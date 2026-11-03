"""Offline-prepared candidate: original current-final reader and full history.

For later root review/use in a fresh /usr/bin/python3 -B -I -S process only.
No service control, network, model, DSO, NativeContext, checkpoint/marker write,
or recovery operation is present. systemctl show and /proc inspection are reads.
Every current boot/owner/stop pin/bound and history edge comes from pinned fresh
inputs. Unknown current values must not be filled from historical examples.
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
import uuid

ROOT = Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/aura')
CHECKPOINT = ROOT.parent / 'state/native-protection-checkpoint.json'
MANIFEST = ROOT.parent / 'camera-python-manifest.json'
ARCHIVES = Path('/home/root/aura-native-critical-20261024/candidates/native-v2-d7256b06808509c9/state/kernel-history/archive')
LEGACY = Path('/home/root/aura-native-critical-20261024/legacy-prefix/ecda1d52dbc4d3a0/legacy-boot-archive.json')
LEGACY_SHA = 'ecda1d52dbc4d3a0005f55c6a85d489c92293076661403c1d834666adae4e2c7'
SOURCE_UNIT = '7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32'
PINS = {
    'board/vision/__init__.py': '091e8b3b95a7f46655ba0c5275630eb3aee2079b57a95a0f5ef35d4e44c47284',
    'board/vision/native_binding.py': '5f385c03cf84b1f9ba3afe4d4a6cfd3022ba639aba06b8d923f83783bfd48da6',
    'board/vision/native_protection.py': 'b8637c2aa387915a49ef0fd7a1c7cb9d015fb71802c4eaa11539a64466db1faa',
    'board/vision/native_boot.py': '251e9660633cd6c50d0874e263899155895372d8b8e0db4d6ecdbfca7901d4a7',
}
FEATURES = ('requests', 'execution_attempts', 'completed', 'features_returned',
            'deferred', 'slot_denials', 'expired_after_admission')
OPTIONAL_COUNTERS = ('calls', 'native_completed', 'native_failures', 'not_submitted', 'overruns')
RECOVERY_TOTALS = ('faults', 'attempts', 'recoveries')
ROW_KEYS = {'path', 'sha256', 'current_boot', 'source_boot',
            'source_checkpoint_sha256', 'history_is_lower_bound'}


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode()


def positive(value, name, maximum=2**63 - 1):
    require(type(value) is int and 0 < value <= maximum, 'Required positive integer: ' + name)
    return value


def digest(value):
    require(type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value), 'Required SHA256')
    return value


def boot(value):
    require(type(value) is str and str(uuid.UUID(value)) == value, 'Required canonical boot UUID')
    return value


def owner(value):
    require(type(value) is dict and set(value) == {'pid', 'birth_ticks', 'command_sha256'}, 'Complete original owner required')
    positive(value['pid'], 'owner.pid', 2**32 - 1)
    require(type(value['birth_ticks']) is str and value['birth_ticks'].isdigit() and int(value['birth_ticks']) > 0, 'Original owner birth required')
    digest(value['command_sha256'])
    return value


def pin(value, fixed_path=None):
    require(type(value) is dict and set(value) == {'path', 'sha256'}, 'Exact metadata pin required')
    path = Path(value['path'])
    require(path.is_absolute() and str(path) == value['path'] and path.suffix == '.json', 'Canonical absolute JSON metadata pin required')
    require(fixed_path is None or path == fixed_path, 'Metadata pin path changed')
    digest(value['sha256'])
    return path


class Snapshot:
    """Bounded regular-file reads and end-to-end original-byte stability."""
    def __init__(self):
        self.files = {}

    def read(self, path, limit=262144):
        path = Path(path)
        require(path.is_absolute() and path.resolve() == path and not path.is_symlink(), 'Redirected metadata/source path')
        require(path.suffix in ('.json', '.py'), 'Only explicit public JSON/Python inputs allowed')
        fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(fd, 'rb') as handle:
            a = os.fstat(handle.fileno())
            require(stat.S_ISREG(a.st_mode) and a.st_size <= limit, 'Nonregular or oversized public input')
            data = handle.read(limit + 1)
            b = os.fstat(handle.fileno())
        identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_mode, info.st_uid, info.st_gid)
        require(len(data) <= limit and identity(a) == identity(b) == identity(path.stat()), 'Public input changed during read')
        record = (data, identity(b))
        if str(path) in self.files:
            require(record == self.files[str(path)], 'Public input changed since first read')
        self.files[str(path)] = record
        return data

    def pinned(self, value, fixed_path=None):
        path = pin(value, fixed_path)
        data = self.read(path)
        require(sha(data) == value['sha256'], 'Pinned input hash differs: ' + str(path))
        return json.loads(data)

    def unchanged(self):
        for path in list(self.files):
            self.read(path)


def original_modules(snapshot):
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, 'Fresh -B -I -S required')
    require(os.uname().machine == 'aarch64', 'Original board ABI required')
    require(not any(name == 'board' or name.startswith('board.') for name in sys.modules), 'Project namespace already loaded')
    require(not os.path.lexists(str(ROOT / 'board/__init__.py')), 'Original namespace root changed')
    for path in (ROOT, ROOT / 'board', ROOT / 'board/vision'):
        require(path.is_dir() and path.resolve() == path and not path.is_symlink(), 'Original source parent redirects')
    sources = {name: snapshot.read(ROOT / name) for name in PINS}
    require(all(sha(sources[name]) == PINS[name] for name in PINS), 'Original reader/ABI Python source changed')
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
        value.__file__ = str(ROOT / relative)
        value.__spec__ = importlib.machinery.ModuleSpec(name, loader=None, origin=value.__file__)
        sys.modules[name] = value
        setattr(sys.modules['board.vision'], stem, value)
        exec(compile(sources[relative], value.__file__, 'exec', dont_inherit=True), value.__dict__)
    return sys.modules['board.vision.native_protection'], sys.modules['board.vision.native_boot']


def show(name):
    result = subprocess.run(['systemctl', 'show', name,
        '--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus,Restart,SendSIGKILL,TimeoutStopUSec,KillMode'],
        capture_output=True, text=True, timeout=5)
    require(result.returncode == 0, 'Cannot inspect original unit')
    return dict(row.split('=', 1) for row in result.stdout.splitlines() if '=' in row)


def guard(expected):
    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == expected['boot_id'], 'Current kernel changed')
    for name in ('aura-avatar-ui.service', 'aura-camera-ui.service'):
        state = show(name)
        require(all(state[key] == value for key, value in {'MainPID': '0', 'ActiveState': 'inactive',
            'SubState': 'dead', 'Job': '', 'Result': 'success', 'ExecMainStatus': '0'}.items()), 'Original service not normally stopped')
        if name == 'aura-camera-ui.service':
            require(all(state[key] == value for key, value in {'Restart': 'no', 'SendSIGKILL': 'no',
                'TimeoutStopUSec': 'infinity', 'KillMode': 'process'}.items()), 'Infinite normal-stop protection changed')
    for prior in [expected['camera_owner']] + expected['stopped_gui_owners']:
        path = Path('/proc') / str(prior['pid']) / 'stat'
        try:
            stamp = path.read_text().rsplit(')', 1)[1].split()[19]
            require(stamp != prior['birth_ticks'], 'Original source owner remains alive, including after exec')
        except (FileNotFoundError, ProcessLookupError):
            pass
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():
            continue
        try:
            maps = (process / 'maps').read_text()
            handles = []
            for descriptor in (process / 'fd').iterdir():
                try:
                    handles.append(os.readlink(descriptor))
                except (FileNotFoundError, ProcessLookupError):
                    pass
            require(not any(name in maps for name in ('libvart', 'libaura_native_operator', 'libvsrv.so')) and
                    not any(name.startswith(('/dev/dri/renderD', '/dev/dpu')) or name == '/dev/mem' for name in handles),
                    'Live Native/VART/DPU/MMIO owner remains')
        except (FileNotFoundError, ProcessLookupError):
            continue
        except OSError:
            require(not process.exists(), 'Unreadable live process prevents owner proof')


def reject_current_checkpoint_source(value, current_boot, current_owner):
    # Inspect checkpoint objects before dereferencing the source pointer. This
    # covers direct documents and JSON envelopes without authenticating root or
    # rejecting independently accepted different-boot/different-owner history.
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is dict:
            seed = item.get('seed')
            if item.get('schema') == 'aura-native-protection-checkpoint-2' and type(seed) is dict:
                require(not (seed.get('boot_id') == current_boot and seed.get('source_pid') == current_owner['pid'] and
                    seed.get('source_birth_ticks') in (int(current_owner['birth_ticks']), current_owner['birth_ticks'])),
                    'History source contains current stopped-owner checkpoint')
            pending.extend(child for child in item.values() if type(child) in (dict, list))
        elif type(item) is list:
            pending.extend(child for child in item if type(child) in (dict, list))


def referenced_value(reference, snapshot, forbidden, forbidden_shas, current_boot, current_owner):
    require(type(reference) is dict and set(reference) == {'pin', 'pointer'}, 'Exact history source reference required')
    require(reference['pin']['path'] not in forbidden, 'History must not self-attest from this final/result')
    require(reference['pin']['sha256'] not in forbidden_shas, 'History source SHA aliases final/result/provenance')
    value = snapshot.pinned(reference['pin'])
    reject_current_checkpoint_source(value, current_boot, current_owner)
    pointer = reference['pointer']
    require(type(pointer) is str and (pointer == '' or pointer.startswith('/')), 'Explicit JSON pointer required')
    if pointer:
        for part in pointer[1:].split('/'):
            require('~' not in part.replace('~0', '').replace('~1', ''), 'Invalid JSON pointer escape')
            key = part.replace('~1', '/').replace('~0', '~')
            if type(value) is list:
                require(key.isdigit() and str(int(key)) == key and int(key) < len(value), 'Invalid JSON pointer index')
                value = value[int(key)]
            else:
                require(type(value) is dict and key in value, 'History source pointer missing')
                value = value[key]
    return value


def validate_original_operator_migration(expected, snapshot, native, intent):
    """Accept only the pinned original RAM migration, never a rewritten config."""
    if native.get('source_unit_sha256') == SOURCE_UNIT:
        return
    operator = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/native-operator-v1')
    old_unit = '29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
    old_library_sha = 'c675ba698d45acd8742e52403e6186f43dc56d7d313d0e740896b19412bde656'
    new_library_sha = '704f561a50b5f0fb8f9b4cf72c024acce0cdafd888cad0784507f484518fc224'
    require(native.get('source_unit_sha256') == old_unit and native.get('library_sha256') == old_library_sha,
            'Unknown config unit/library is not the approved original migration')
    observation = snapshot.pinned(expected['original_operator_migration_pin'])
    require(observation['schema'] == 'aura-original-operator-config-migration-observation-1'
            and observation['boot_id'] == expected['boot_id']
            and observation['source_owner'] == expected['camera_owner']
            and observation['owner_run_config_pin'] == expected['owner_run_config_pin']
            and type(observation['observed_mono_ns']) is int
            and 0 < observation['observed_mono_ns'] < intent['stop_intent_mono_ns']
            and observation['metadata_observation_only'] is True
            and observation['original_migration_or_Native_code_executed_by_this_observer'] is False,
            'Original migration observation is not from this owner before normal stop')
    def read_bytes(entry):
        pin(entry)
        raw = snapshot.read(entry['path'])
        require(sha(raw) == entry['sha256'], 'Original migration source bytes differ')
        return raw
    runtime_pin = observation['native_operator_manifest_pin']
    require(runtime_pin == {'path': str(operator / 'runtime-manifest.json'),
                            'sha256': '74e011db30a9d943a9512f7648190ac0c01060af06df1280d1e8ea006dc882ad'},
            'Original operator runtime manifest differs')
    runtime = snapshot.pinned(runtime_pin)
    require(runtime['schema'] == 'aura-native-operator-runtime-1' and len(runtime['files']) == 7,
            'Original seven-member migration closure required')
    for path, checksum in runtime['files'].items():
        read_bytes({'path': path, 'sha256': checksum})
    fixed_sources = {
        str(operator / 'native_entry_operator.py'): '0576a388e2c17174b4102665602aa42fbf078a3f016bdfb641c269571ce13943',
        str(operator / 'identity_recovery.py'): '64831498d8497c2087b3bb1543367e8cc1917ca131694000884f2d58e60990f7',
    }
    require(observation['original_migration_sources'] == fixed_sources
            and all(runtime['files'].get(path) == checksum for path, checksum in fixed_sources.items()),
            'Original entry/RAM-migration source differs')
    settings_pin = observation['settings_pin']
    require(settings_pin['path'] == str(operator / 'settings.json')
            and runtime['files'].get(settings_pin['path']) == settings_pin['sha256'],
            'Original migration settings are not in the pinned runtime')
    settings = snapshot.pinned(settings_pin)
    require(native['library'] == settings['old_library'] and native['library_sha256'] == settings['old_library_sha256'] == old_library_sha
            and native['source_unit_sha256'] == settings['predecessor_unit_sha256'] == old_unit
            and settings['unit_sha256'] == SOURCE_UNIT
            and settings['library'] == str(operator / 'libaura_native_operator.so')
            and settings['library_sha256'] == new_library_sha,
            'Original approved migration input/output tuple differs')
    read_bytes({'path': settings['old_library'], 'sha256': old_library_sha})
    unit_pin = observation['native_c_unit_manifest_pin']
    require(unit_pin == {'path': str(operator / 'source-manifest.json'), 'sha256': SOURCE_UNIT}, 'Original six-member C unit differs')
    unit = snapshot.pinned(unit_pin)
    require(unit['schema'] == 'aura-native-operator-source-unit-1' and unit['existing_abi'] == 2 and len(unit['files']) == 6,
            'Original C ABI/source member set differs')
    for path, checksum in unit['files'].items():
        relative = Path(path)
        require(not relative.is_absolute() and '..' not in relative.parts, 'Original C source path escapes')
        read_bytes({'path': str(operator / relative), 'sha256': checksum})
    library_pin = observation['native_library_pin']
    require(library_pin == {'path': settings['library'], 'sha256': new_library_sha}, 'Actual original migrated library differs')
    read_bytes(library_pin)
    audit_pin = observation['original_audit_pin']
    require(audit_pin['path'] == str(operator / ('recovery-audit-' + str(expected['camera_owner']['pid']) + '.json')),
            'Original migration audit is not this owner')
    audit = snapshot.pinned(audit_pin)
    handoff = observation['original_live_handoff_migration']
    require(audit['audit_path'] == audit_pin['path'] and audit['request'] == settings
            and audit['artificial_counter_reset'] is False and type(audit['mechanical_actions']) is int and audit['mechanical_actions'] == 0
            and audit['checkpoint_sha256'] == native['seed']['sha256']
            and audit['checkpoint_unit_sha256'] in (old_unit, SOURCE_UNIT)
            and audit['exact_seed_before_operator_request']['boot_id'] == expected['boot_id']
            and handoff['operator_recovery_audit'] == audit_pin['path']
            and handoff['native_abi_compatible_migration'] is True
            and handoff['predecessor_unit_sha256'] == audit['checkpoint_unit_sha256']
            and handoff['native_unit_sha256'] == SOURCE_UNIT
            and observation['mapped_original_operator_library'] == settings['library'],
            'Original audit and observed live migration linkage differs')


def validate_inputs(expected, snapshot):
    require(expected['schema'] == 'aura-fresh-final-history-expected-1' and expected['all_other_writers_frozen'] is True,
            'Explicit fresh validation contract and writer freeze required')
    boot(expected['boot_id'])
    current = owner(expected['camera_owner'])
    require(type(expected['stopped_gui_owners']) is list and expected['stopped_gui_owners'], 'Prior GUI owners required')
    for prior in expected['stopped_gui_owners']:
        owner(prior)
    pin(expected['startup'])
    snapshot.pinned(expected['startup'])
    pin(expected['checkpoint_pin'], CHECKPOINT)
    pin(expected['source_manifest_pin'], MANIFEST)
    snapshot.pinned(expected['source_manifest_pin'])
    require(expected['source_unit_sha256'] == SOURCE_UNIT, 'Original Native C unit changed')
    config = snapshot.pinned(expected['owner_run_config_pin'])
    run_path = Path(expected['owner_run_config_pin']['path'])
    require(run_path.name == 'config.json' and run_path.parent.name == 'native-run-' + expected['boot_id'] + '-' + str(current['pid']),
            'Actual stopped-owner run-config provenance required')
    native = config['native_execution']
    require(native['source_manifest'] == expected['source_manifest_pin']['path'] and
            native['source_manifest_sha256'] == expected['source_manifest_pin']['sha256'], 'Stopped owner run-config/Python manifest differs')
    intent = snapshot.pinned(expected['stop_intent_pin'])
    result = snapshot.pinned(expected['stop_result_pin'])
    require(intent['schema'] == 'aura-original-camera-stop-intent-2' and intent['boot_id'] == expected['boot_id'] and
            intent['source_owner'] == current and intent['source_pid'] == current['pid'] and
            intent['source_birth_ticks'] == int(current['birth_ticks']) and intent['startup'] == expected['startup'] and
            intent['all_other_writers_frozen'] is True and intent['action'] == 'systemctl stop --no-block aura-camera-ui.service',
            'Pinned normal-stop intent does not bind this current run')
    positive(intent['stop_intent_mono_ns'], 'stop intent mono')
    validate_original_operator_migration(expected, snapshot, native, intent)
    require(result['schema'] == 'aura-original-camera-normal-stop-2' and result['status'] == 'CAMERA_STOPPED_NEW_FINAL_PRESENT' and
            result['intent'] == intent and result['normal_stop_submitted_once'] is True and result['forced_action'] is False and
            result['checkpoint_or_marker_written_by_this_script'] is False and result['fresh_checkpoint'] == expected['checkpoint_pin'],
            'Pinned result does not prove this one normal-stop/fresh-final attempt')
    history = expected['history']
    proof = snapshot.pinned(history['provenance_pin'])
    require(proof['schema'] == 'aura-prestop-native-history-manifest-1' and proof['boot_id'] == expected['boot_id'] and
            proof['source_owner'] == current and proof['history'] == {key: value for key, value in history.items() if key != 'provenance_pin'},
            'Fresh independent history provenance differs')
    require(0 < positive(history['observed_mono_ns'], 'history observation mono') < intent['stop_intent_mono_ns'],
            'History proof must predate the normal-stop intent')
    count = positive(history['archive_count'], 'exact archive count', 64)
    require(type(history['archives']) is list and len(history['archives']) == count, 'Exact complete ordered archive manifest required')
    require(history['legacy_pin'] == {'path': str(LEGACY), 'sha256': LEGACY_SHA}, 'Original legacy anchor changed')
    sources = proof['source_bindings']
    require(type(sources) is dict and set(sources) == {'boot_id', 'source_owner', 'observed_mono_ns', 'head', 'archive_segments'},
            'Traceable fresh history source bindings required')
    forbidden = {str(CHECKPOINT), expected['stop_result_pin']['path'], history['provenance_pin']['path']}
    forbidden_shas = {expected['checkpoint_pin']['sha256'], expected['stop_result_pin']['sha256'], history['provenance_pin']['sha256']}
    values = {'boot_id': expected['boot_id'], 'source_owner': current,
              'observed_mono_ns': history['observed_mono_ns'], 'head': history['head']}
    for name, value in values.items():
        require(referenced_value(sources[name], snapshot, forbidden, forbidden_shas, expected['boot_id'], current) == value, 'History source field differs: ' + name)
    require(type(sources['archive_segments']) is list and sources['archive_segments'], 'Accepted ordered history source segments required')
    sourced_archives = []
    for reference in sources['archive_segments']:
        segment = referenced_value(reference, snapshot, forbidden, forbidden_shas, expected['boot_id'], current)
        require(type(segment) is list and segment, 'Empty/invalid history source segment')
        sourced_archives.extend(segment)
    require(sourced_archives == history['archives'], 'History manifest differs from ordered accepted source segments')
    seen = set()
    for row in history['archives']:
        require(type(row) is dict and set(row) == ROW_KEYS, 'Exact archive manifest row required')
        path = Path(row['path'])
        require(path.parent == ARCHIVES and str(path) not in seen and type(row['history_is_lower_bound']) is bool, 'Archive manifest root/duplicate/scope invalid')
        seen.add(str(path))
        digest(row['sha256']); digest(row['source_checkpoint_sha256'])
        boot(row['current_boot']); boot(row['source_boot'])
    return intent, result


def optional_shape(auxiliary, protection):
    require(set(auxiliary['inherited_optional']) == {'yunet', 'sface'}, 'Both inherited optional histories required')
    for task in ('yunet', 'sface'):
        state = auxiliary['inherited_optional'][task]
        for field in OPTIONAL_COUNTERS + ('pending_result_token',):
            protection.integer(state[field], task + '.' + field)
        require(state['pending_result_token'] == 0 and type(state['disabled']) is bool and
                type(state['last_native_report']) is dict and type(state['recovery']) is dict, 'Optional completion/state incomplete')
        policy = state['recovery']
        for field in RECOVERY_TOTALS + ('probe_successes', 'attempts_in_window'):
            protection.integer(policy[field], task + '.recovery.' + field)
        require(type(policy['history_opaque']) is bool, 'Optional opaque-history flag required')


def current_bounds(seed, auxiliary, intent, protection):
    bounds = intent['prestop_bounds']
    for field, source in (('primary_calls', 'primary_calls_lower_bound'), ('primary_period_overruns', 'primary_period_overruns_lower_bound')):
        require(seed[field] >= protection.integer(intent[source], source), 'Current-boot primary counter regressed')
    require(set(bounds['sface']) == set(FEATURES), 'All seven current SFace lower bounds required')
    for field in FEATURES:
        require(auxiliary['sface_counters'][field] >= protection.integer(bounds['sface'][field], 'prestop sface.' + field), 'Current-boot SFace counter regressed: ' + field)
    require(set(bounds['optional']) == {'yunet', 'sface'}, 'Both current optional lower bounds required')
    for index, task in enumerate(('yunet', 'sface'), 1):
        prior = bounds['optional'][task]
        final = auxiliary['inherited_optional'][task]
        for field in OPTIONAL_COUNTERS:
            require(final[field] >= protection.integer(prior[field], 'prestop ' + task + '.' + field), 'Current-boot optional counter regressed: ' + task + '.' + field)
        for field in ('native_failures', 'not_submitted', 'overruns'):
            require(seed[field][index] >= prior[field], 'Current-boot Native task counter regressed: ' + task + '.' + field)
        require(seed['completed'][index] >= prior['native_completed'], 'Current-boot Native completion regressed')
        old_policy = prior['recovery']
        policies = (final['recovery'], seed['recovery'][index - 1])
        require(type(old_policy['history_opaque']) is bool, 'Prestop opaque-history flag missing')
        for policy in policies:
            for field in RECOVERY_TOTALS:
                require(policy[field] >= protection.integer(old_policy[field], 'prestop recovery.' + field), 'Current-boot recovery total regressed')
            require(policy['history_opaque'] == old_policy['history_opaque'], 'Opaque history was discarded')
            progress = protection.integer(old_policy['probe_successes'], 'prestop recovery.probe_successes')
            # Probe progress resets after a new fault/attempt; it is not a
            # cumulative total. Preserve the old check within one generation.
            if policy['faults'] == old_policy['faults'] and policy['attempts'] == old_policy['attempts']:
                require(policy['probe_successes'] >= progress, 'Same-generation recovery progress regressed')


def validate_current(expected, intent, result, snapshot, protection, boot_module):
    before = snapshot.read(CHECKPOINT)
    require(sha(before) == expected['checkpoint_pin']['sha256'], 'Fresh final bytes differ')
    marker = str(CHECKPOINT) + '.native-consumed-' + expected['checkpoint_pin']['sha256']
    require(not os.path.lexists(marker), 'Final already consumed or marker path object exists')
    # Exact original Python reader; no now_ns override and no consume call.
    loaded = protection.load_business_checkpoint(expected['checkpoint_pin'], boot_id=expected['boot_id'])
    require(loaded['sha256'] == expected['checkpoint_pin']['sha256'] and loaded['document'] == json.loads(before), 'Original reader returned different final')
    document = loaded['document']
    # Stronger original archived-policy semantic validator, also for current.
    seed, auxiliary = boot_module._sealed_source(document)
    require(seed == loaded['seed'] and auxiliary == loaded['auxiliary'], 'Original validators disagree')
    optional_shape(auxiliary, protection)
    source = expected['camera_owner']
    require(seed['boot_id'] == expected['boot_id'] and seed['source_pid'] == source['pid'] and
            seed['source_birth_ticks'] == int(source['birth_ticks']), 'Final source boot/owner differs')
    require(document['source_unit_sha256'] == SOURCE_UNIT and
            seed['source_manifest_sha256'] == expected['source_manifest_pin']['sha256'], 'Final source provenance differs')
    require(0 < intent['stop_intent_mono_ns'] <= seed['captured_mono_ns'] <= time.monotonic_ns() and
            result['captured_mono_ns'] == seed['captured_mono_ns'], 'Final not captured in this stop intent/current monotonic domain')
    current_bounds(seed, auxiliary, intent, protection)
    require(not os.path.lexists(marker), 'Final consumed during validation')
    return document, marker


def validate_chain(document, history_expected, snapshot, protection, boot_module):
    history = document['previous_kernel_history']
    require(history == history_expected['head'], 'Final lost its independently pinned history head')
    count = history_expected['archive_count']
    require(type(count) is int and 1 <= count <= 64 and len(history_expected['archives']) == count, 'Exact bounded archive count required')
    expected_boot = document['seed']['boot_id']
    seen_paths, seen_boots, records = set(), {expected_boot}, []
    for depth in range(count):
        path = Path(history['archive_path'])
        require(path.parent == ARCHIVES and str(path) not in seen_paths, 'Archive root/path cycle')
        seen_paths.add(str(path))
        data = snapshot.read(path)
        require(sha(data) == protection.digest(history['archive_sha256'], 'archive SHA'), 'Archive bytes differ')
        archive = json.loads(data)
        require(archive['schema'] == 'aura-native-previous-kernel-archive-1', 'Unknown archive schema')
        source_boot = protection._boot(archive['source_boot'])
        require(source_boot not in seen_boots and source_boot != expected_boot, 'Boot cycle in archive chain')
        seen_boots.add(source_boot)
        source_sha = protection.digest(archive['source_checkpoint_sha256'], 'archived source checkpoint')
        require(archive['current_boot'] == expected_boot and source_boot == history['source_boot'] and
                source_sha == history['source_checkpoint_sha256'] and path.name == expected_boot + '-' + source_sha + '.json', 'Archive edge identity differs')
        require(type(history['history_is_lower_bound']) is bool and archive['history_is_lower_bound'] is history['history_is_lower_bound'] and
                archive['unknown_tail'] is history['history_is_lower_bound'], 'Legacy scope/unknown tail changed')
        row = {'path': str(path), 'sha256': sha(data), 'current_boot': expected_boot, 'source_boot': source_boot,
               'source_checkpoint_sha256': source_sha, 'history_is_lower_bound': archive['history_is_lower_bound']}
        require(row == history_expected['archives'][depth], 'Ordered archive manifest/provenance differs')
        records.append(row)
        checkpoint = archive['checkpoint']
        if checkpoint.get('schema') == 'aura-native-protection-checkpoint-2':
            require(archive['history_is_lower_bound'] is False and archive['source_checkpoint_path'] == str(CHECKPOINT), 'V2 archive source scope/path differs')
            require(sha(canonical(checkpoint)) == source_sha, 'Embedded v2 checkpoint is not its exact original canonical SHA')
            # Archive-only validator: NO current-boot reader, now override,
            # restored seed, or comparison to the current counter domain.
            seed, auxiliary = boot_module._sealed_source(checkpoint)
            optional_shape(auxiliary, protection)
            require(seed['boot_id'] == source_boot and seed['source_manifest_sha256'] == archive['source_manifest_sha256'], 'Archived source provenance differs')
            require('previous_kernel_history' in checkpoint, 'Archive chain truncated before legacy anchor')
            history, expected_boot = checkpoint['previous_kernel_history'], source_boot
            continue
        require(checkpoint.get('schema') == 'aura-native-legacy-boot-archive-1' and archive['history_is_lower_bound'] is True and
                archive['source_checkpoint_path'] == history_expected['legacy_pin']['path'] and
                source_sha == history_expected['legacy_pin']['sha256'], 'Unknown terminal archive/legacy source')
        legacy = snapshot.pinned(history_expected['legacy_pin'])
        require(legacy == checkpoint, 'Original legacy bytes differ from embedded anchor')
        legacy_seed, legacy_auxiliary = boot_module._legacy_source(checkpoint)
        require(legacy_seed['boot_id'] == source_boot and legacy_seed['source_manifest_sha256'] == archive['source_manifest_sha256'] and
                'previous_kernel_history' not in checkpoint and legacy_seed['history_is_lower_bound'] is True and legacy_seed['unknown_tail'] is True,
                'Legacy anchor identity/scope differs')
        require(depth + 1 == count, 'Early terminal omitted expected archive history')
        return records
    raise ValueError('Archive chain truncated or bounded traversal ended before original legacy anchor')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    args = parser.parse_args()
    snapshot = Snapshot()
    raw = snapshot.read(args.expected)
    require(sha(raw) == digest(args.expected_sha256), 'Expected contract pin differs')
    expected = json.loads(raw)
    intent, result = validate_inputs(expected, snapshot)
    guard(expected)
    protection, boot_module = original_modules(snapshot)
    document, marker = validate_current(expected, intent, result, snapshot, protection, boot_module)
    records = validate_chain(document, expected['history'], snapshot, protection, boot_module)
    snapshot.unchanged()
    require(not os.path.lexists(marker), 'Final consumed during validation')
    guard(expected)
    require(set(name for name in sys.modules if name == 'board' or name.startswith('board.')) ==
            {'board', 'board.vision', 'board.vision.native_binding', 'board.vision.native_protection', 'board.vision.native_boot'},
            'Unexpected project import')
    print(json.dumps({'schema': 'aura-fresh-final-history-validation-1', 'status': 'ORIGINAL_CURRENT_FINAL_AND_COMPLETE_HISTORY_VERIFIED',
        'expected_sha256': args.expected_sha256, 'boot_id': expected['boot_id'], 'source_owner': expected['camera_owner'],
        'checkpoint_pin': expected['checkpoint_pin'], 'owner_run_config_pin': expected['owner_run_config_pin'],
        'source_manifest_pin': expected['source_manifest_pin'], 'source_unit_sha256': SOURCE_UNIT,
        'original_load_business_checkpoint_called': True, 'original_sealed_source_current_and_each_v2_called': True,
        'original_legacy_source_called': True, 'complete_ordered_history_verified': True, 'archive_count': len(records), 'archives': records,
        'legacy_pin': expected['history']['legacy_pin'], 'legacy_lower_bound_unknown_tail_preserved': True,
        'all_required_current_boot_cumulative_lower_bounds_checked': True, 'old_boot_counters_remain_archive_only': True,
        'checked_lower_bounds': {'primary': ['primary_calls', 'primary_period_overruns'], 'sface': list(FEATURES),
            'optional_each': list(OPTIONAL_COUNTERS), 'native_optional_each': ['completed', 'native_failures', 'not_submitted', 'overruns'],
            'recovery_totals_each': list(RECOVERY_TOTALS), 'recovery_progress': 'probe_successes within unchanged fault/attempt generation'},
        'checkpoint_consumed': False, 'checkpoint_or_marker_written': False, 'native_context_created': False,
        'aura_native_library_loaded': False, 'service_action_requested': False, 'device_or_database_or_model_opened': False}, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'HOLD_FRESH_FINAL_HISTORY_NOT_VERIFIED', 'reason_type': type(exc).__name__,
                          'reason': str(exc), 'no_retry_or_recovery_requested': True}))
        raise SystemExit(2)
