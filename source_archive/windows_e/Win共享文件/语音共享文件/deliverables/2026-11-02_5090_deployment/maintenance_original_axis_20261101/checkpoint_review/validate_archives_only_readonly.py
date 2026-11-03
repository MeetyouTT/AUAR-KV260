"""Post-stop read-only validation of the real final checkpoint and full archive chain.

Run only in /usr/bin/python3 -B -I -S. No service, device, NativeContext,
consumption-marker or checkpoint write operation exists in this file.
"""
import argparse
import hashlib
import importlib.machinery
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import types

BOOT = '903cfade-b93c-48fa-804e-379be1967313'
ROOT = Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/aura')
CHECKPOINT = ROOT.parent/'state/native-protection-checkpoint.json'
ARCHIVES = Path('/home/root/aura-native-critical-20261024/candidates/native-v2-d7256b06808509c9/state/kernel-history/archive')
OLD_SHA = '5b26714b0be9d52bf99fe14c07a0f810105379171712328b63454beb314bc6bb'
TOP_ARCHIVE_SHA = 'b050b88649f45a4dcdb680513e64caae2560162afecf6536ee9fda6885e08ba5'
SOURCE_MANIFEST = '5e08f7cf587d74334ef24104ea01f79701629b48f2004fb772ce3f8ea82afd0d'
SOURCE_UNIT = '7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32'
LEGACY = Path('/home/root/aura-native-critical-20261024/legacy-prefix/ecda1d52dbc4d3a0/legacy-boot-archive.json')
LEGACY_SHA = 'ecda1d52dbc4d3a0005f55c6a85d489c92293076661403c1d834666adae4e2c7'
PINS = {
    'board/vision/__init__.py': '091e8b3b95a7f46655ba0c5275630eb3aee2079b57a95a0f5ef35d4e44c47284',
    'board/vision/native_binding.py': '5f385c03cf84b1f9ba3afe4d4a6cfd3022ba639aba06b8d923f83783bfd48da6',
    'board/vision/native_protection.py': 'b8637c2aa387915a49ef0fd7a1c7cb9d015fb71802c4eaa11539a64466db1faa',
    'board/vision/native_boot.py': '251e9660633cd6c50d0874e263899155895372d8b8e0db4d6ecdbfca7901d4a7',
}

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def raw(path, limit=262144):
    path = Path(path)
    require(path.is_absolute() and not path.is_symlink() and path.resolve() == path,
            'Redirected or relative metadata path: ' + str(path))
    require(path.suffix not in ('.db', '.sqlite', '.sqlite3'), 'Private database path refused')
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_size <= limit, 'Metadata file shape or bound')
        with os.fdopen(fd, 'rb', closefd=False) as handle:
            value = handle.read(limit + 1)
        require(len(value) <= limit, 'Metadata exceeds bound')
        return value
    finally:
        os.close(fd)

def sha(value):
    return hashlib.sha256(value).hexdigest()

def canonical(value, newline=True):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True) +
            ('\n' if newline else '')).encode()

def unit(name):
    p = subprocess.run(['systemctl', 'show', name,
        '--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus,Restart,SendSIGKILL,TimeoutStopUSec,KillMode'],
        capture_output=True, text=True, timeout=5)
    require(p.returncode == 0, 'Cannot read service state')
    return dict(row.split('=', 1) for row in p.stdout.splitlines() if '=' in row)

def stopped():
    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT, 'Kernel changed')
    for name in ('aura-avatar-ui.service', 'aura-camera-ui.service'):
        value = unit(name)
        require(value['MainPID'] == '0' and value['Job'] == '' and
                value['ActiveState'] == 'inactive' and value['SubState'] == 'dead',
                'A service is not fully stopped: ' + name)
        require(value['Result'] == 'success' and value['ExecMainStatus'] == '0',
                'Normal shutdown has not succeeded: ' + name)
        if name == 'aura-camera-ui.service':
            require(value['Restart'] == 'no' and value['SendSIGKILL'] == 'no' and
                    value['TimeoutStopUSec'] == 'infinity' and value['KillMode'] == 'process',
                    'Original camera shutdown protection changed')
    predecessor = Path('/proc/1333/stat')
    if predecessor.exists():
        require(int(predecessor.read_text().rsplit(')', 1)[1].split()[19]) != 2359,
                'Original camera owner is still alive')

def original_modules():
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
            'Fresh -B -I -S interpreter required')
    require(os.uname().machine == 'aarch64', 'Original board ABI required')
    require(not any(n == 'board' or n.startswith('board.') for n in sys.modules),
            'Pre-existing project modules refused')
    require(not os.path.lexists(str(ROOT/'board/__init__.py')), 'Namespace root changed')
    for path in (ROOT, ROOT/'board', ROOT/'board/vision'):
        require(path.is_dir() and path.resolve() == path and not path.is_symlink(), 'Source parent redirects')
    sources = {name: raw(ROOT/name) for name in PINS}
    require(all(sha(sources[n]) == PINS[n] for n in PINS), 'Original source hash changed')
    for name in ('board', 'board.vision'):
        value = types.ModuleType(name)
        value.__package__ = name
        value.__path__ = []
        value.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, is_package=True)
        value.__spec__.submodule_search_locations = []
        sys.modules[name] = value
    sys.modules['board'].vision = sys.modules['board.vision']
    for stem in ('native_binding', 'native_protection', 'native_boot'):
        name = 'board.vision.' + stem
        relative = 'board/vision/' + stem + '.py'
        value = types.ModuleType(name)
        value.__package__ = 'board.vision'
        value.__file__ = str(ROOT/relative)
        value.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, origin=value.__file__)
        sys.modules[name] = value
        setattr(sys.modules['board.vision'], stem, value)
        exec(compile(sources[relative], value.__file__, 'exec', dont_inherit=True), value.__dict__)
    return tuple(sys.modules['board.vision.' + n] for n in
                 ('native_binding', 'native_protection', 'native_boot'))

def checkpoint_shape(document, binding, protection):
    require(document.get('schema') == 'aura-native-protection-checkpoint-2' and
            document.get('scope') == 'final_quiescent_before_native_owner_close', 'Archived v2 scope differs')
    seed, aux = document['seed'], document['auxiliary']
    require(seed['purpose'] == 'final_quiescent_business_checkpoint', 'Archived seed purpose differs')
    protection.make_native_seed(seed, binding.Seed, binding.Recovery)
    protection.digest(document['source_unit_sha256'], 'archive source unit')
    require(aux['active'] == 0 and aux['primary_waiting'] == 0 and aux['fenced'] == 0 and
            aux['pending_result_tokens'] == [0, 0, 0], 'Archived owner not quiescent')
    c = aux['sface_counters']
    require(set(c) == set(protection.FEATURE_COUNTERS), 'Missing archived SFace counters')
    for key, value in c.items(): protection.integer(value, 'sface.' + key)
    require(c['features_returned'] <= c['completed'] <= c['execution_attempts'] <= c['requests'],
            'Archived SFace counter ordering')
    require(set(aux['inherited_optional']) == {'yunet', 'sface'}, 'Missing complete inherited optional history')
    for task in ('yunet', 'sface'):
        optional = aux['inherited_optional'][task]
        for key in ('calls', 'native_completed', 'native_failures', 'not_submitted', 'overruns', 'pending_result_token'):
            protection.integer(optional[key], task + '.' + key)
        require(optional['pending_result_token'] == 0 and type(optional['disabled']) is bool,
                'Inherited optional result is pending or disabled state invalid')
        require(isinstance(optional['last_native_report'], dict) and isinstance(optional['recovery'], dict),
                'Inherited optional report/recovery missing')
        for key in ('faults', 'attempts', 'recoveries', 'probe_successes', 'attempts_in_window'):
            protection.integer(optional['recovery'][key], task + '.recovery.' + key)
    return seed, aux

def chain(document, binding, protection, boot_module):
    history = document['previous_kernel_history']
    require(history['archive_path'] == str(ARCHIVES/(BOOT + '-' + OLD_SHA + '.json')) and
            history['archive_sha256'] == TOP_ARCHIVE_SHA and history['source_checkpoint_sha256'] == OLD_SHA and
            history['source_boot'] == '3c94e7a0-3f4d-4b66-801c-fa0a1b749bfb',
            'Current final checkpoint lost its proven predecessor link')
    expected_boot = BOOT
    seen_paths, seen_boots, records = set(), {BOOT}, []
    for depth in range(64):
        path = Path(history['archive_path'])
        require(path.parent == ARCHIVES and str(path) not in seen_paths, 'Archive escapes root or cycles')
        seen_paths.add(str(path))
        content = raw(path)
        require(sha(content) == protection.digest(history['archive_sha256'], 'archive SHA'), 'Archive bytes differ')
        archive = json.loads(content)
        require(archive['schema'] == 'aura-native-previous-kernel-archive-1', 'Archive schema differs')
        source_boot = protection._boot(archive['source_boot'])
        require(source_boot not in seen_boots and source_boot != expected_boot, 'Boot cycle in archive chain')
        seen_boots.add(source_boot)
        source_sha = protection.digest(archive['source_checkpoint_sha256'], 'archived source checkpoint')
        require(archive['current_boot'] == expected_boot and source_boot == history['source_boot'] and
                source_sha == history['source_checkpoint_sha256'] and
                path.name == expected_boot + '-' + source_sha + '.json', 'Archive edge identity differs')
        require(type(history['history_is_lower_bound']) is bool and
                archive['history_is_lower_bound'] is history['history_is_lower_bound'] and
                archive['unknown_tail'] is history['history_is_lower_bound'], 'Legacy scope changed')
        cp = archive['checkpoint']
        record = {'path': str(path), 'sha256': sha(content), 'current_boot': expected_boot,
                  'source_boot': source_boot, 'source_checkpoint_sha256': source_sha,
                  'history_is_lower_bound': archive['history_is_lower_bound']}
        records.append(record)
        if cp.get('schema') == 'aura-native-protection-checkpoint-2':
            require(archive['history_is_lower_bound'] is False and
                    archive['source_checkpoint_path'] == str(CHECKPOINT), 'V2 archive source scope/path differs')
            require(sha(canonical(cp)) == source_sha, 'Embedded v2 checkpoint does not match its exact original writer SHA')
            seed, aux = checkpoint_shape(cp, binding, protection)
            require(seed['boot_id'] == source_boot and seed['source_manifest_sha256'] == archive['source_manifest_sha256'],
                    'Archived checkpoint provenance differs')
            require('previous_kernel_history' in cp, 'Silent archive-chain truncation before legacy anchor')
            history, expected_boot = cp['previous_kernel_history'], source_boot
            continue
        require(cp.get('schema') == 'aura-native-legacy-boot-archive-1' and
                archive['history_is_lower_bound'] is True and source_sha == LEGACY_SHA and
                archive['source_checkpoint_path'] == str(LEGACY), 'Unknown historical terminal scope')
        legacy_bytes = raw(LEGACY)
        require(sha(legacy_bytes) == LEGACY_SHA and json.loads(legacy_bytes) == cp,
                'Legacy original bytes differ from pinned embedded history')
        legacy_seed, legacy_aux = boot_module._legacy_source(cp)
        require(legacy_seed['boot_id'] == source_boot and
                legacy_seed['source_manifest_sha256'] == archive['source_manifest_sha256'] and
                'previous_kernel_history' not in cp, 'Legacy anchor identity differs')
        require(len(records) == 18, 'Current proven archive chain length changed')
        return records
    raise RuntimeError('Archive traversal limit reached; no truncation accepted')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint-sha256', required=True)
    p.add_argument('--stop-intent-mono-ns', required=True, type=int)
    p.add_argument('--minimum-primary-calls', required=True, type=int)
    p.add_argument('--minimum-primary-overruns', required=True, type=int)
    p.add_argument('--minimum-sface-completed', required=True, type=int)
    args = p.parse_args()
    stopped()
    binding, protection, boot_module = original_modules()
    before = raw(CHECKPOINT)
    require(sha(before) == args.checkpoint_sha256 and args.checkpoint_sha256 != OLD_SHA, 'New final pin differs')
    marker = CHECKPOINT.with_name(CHECKPOINT.name + '.native-consumed-' + args.checkpoint_sha256)
    require(not os.path.lexists(str(marker)), 'Consumed marker path exists')
    pin = {'path': str(CHECKPOINT), 'sha256': args.checkpoint_sha256}
    loaded = protection.load_business_checkpoint(pin, boot_id=BOOT)
    document = loaded['document']
    seed, aux = checkpoint_shape(document, binding, protection)
    require(document['source_unit_sha256'] == SOURCE_UNIT and seed['source_manifest_sha256'] == SOURCE_MANIFEST,
            'Current Native source differs')
    require(seed['source_pid'] == 1333 and seed['source_birth_ticks'] == 2359 and seed['boot_id'] == BOOT,
            'Final source owner differs')
    require(0 < args.stop_intent_mono_ns < seed['captured_mono_ns'] <= time.monotonic_ns(),
            'Final capture was not after this stop intent')
    require(seed['primary_calls'] >= max(78923, args.minimum_primary_calls) and
            seed['primary_period_overruns'] >= max(1, args.minimum_primary_overruns) and
            aux['sface_counters']['completed'] >= max(427, args.minimum_sface_completed), 'Observed counters regressed')
    records = chain(document, binding, protection, boot_module)
    require(raw(CHECKPOINT) == before and not os.path.lexists(str(marker)), 'Checkpoint changed or consumed during validation')
    for item in records:
        require(sha(raw(item['path'])) == item['sha256'], 'An archive changed during validation')
    require(sha(raw(LEGACY)) == LEGACY_SHA, 'Legacy anchor changed during validation')
    stopped()
    require(set(n for n in sys.modules if n == 'board' or n.startswith('board.')) ==
            {'board', 'board.vision', 'board.vision.native_binding', 'board.vision.native_protection', 'board.vision.native_boot'},
            'Unexpected project import')
    print(json.dumps({'schema': 'aura-original-final-and-history-readonly-validation-1',
        'boot_id': BOOT, 'checkpoint_pin': pin, 'original_python_validator_passed': True,
        'full_previous_kernel_archive_chain_verified': True, 'archive_count': len(records), 'archives': records,
        'legacy_anchor_sha256': LEGACY_SHA, 'legacy_remains_lower_bound_unknown_tail': True,
        'source_sha256': PINS, 'source_unit_sha256': SOURCE_UNIT, 'source_manifest_sha256': SOURCE_MANIFEST,
        'loaded': loaded, 'checkpoint_consumed': False, 'checkpoint_sealed_by_this_script': False,
        'board_mutations': False, 'device_opened': False, 'database_opened': False,
        'native_context_created': False, 'service_action_requested': False}, sort_keys=True))

if __name__ == '__main__':
    # Archive-only review: the active camera/current-final validator is not called.
    binding, protection, boot_module = original_modules()
    first = ARCHIVES/(BOOT + '-' + OLD_SHA + '.json')
    archive = json.loads(raw(first))
    history = {'archive_path':str(first), 'archive_sha256':sha(raw(first)),
        'source_checkpoint_sha256':archive['source_checkpoint_sha256'],
        'source_boot':archive['source_boot'], 'history_is_lower_bound':archive['history_is_lower_bound']}
    records = chain({'previous_kernel_history':history}, binding, protection, boot_module)
    print(json.dumps({'scope':'EXISTING_ARCHIVES_ONLY_NOT_CURRENT_FINAL_CHECKPOINT',
        'archive_count':len(records),'full_existing_archive_chain_verified':True,
        'top_sha256':TOP_ARCHIVE_SHA,'legacy_original_sha256':LEGACY_SHA,
        'current_final_validator_called':False,'checkpoint_consumed':False,
        'board_mutations':False,'devices_or_databases_opened':False,
        'native_context_created':False,'native_boot_loaded_for_pure_legacy_validation':True},sort_keys=True))
