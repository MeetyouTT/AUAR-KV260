"""Post-consumption same-boot readback proof for the reviewed COMPLETE trial.

Default is read-only. This is not native checkpoint admission: the checkpoint
must ALREADY have been exclusively consumed by the exact restored live owner.
No service action, native context, model runner, gallery DB or template is used.
The original new-boot pin helper and every old source pin remain unchanged.
"""
import argparse
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import types

ROOT = '/home/root/aura-board-owner-candidate-20261030/camera-budget-b697628ac2588881-08348d996517'
AUTHORITY = {
    'executor_path': ROOT+'/serial_trial-1e8aeee2a94b4fce.py',
    'executor_sha256': '1e8aeee2a94b4fce674f2468ce48c77fbb88ef99bd9cb1ab66dd3bf20a0327f6',
    'journal_path': ROOT+'/journal/state.json',
    'baseline_path': '/home/root/aura-board-owner-candidate-20261030/private-pin-8100a7fd-20261030/face_gallery_readback.local.json',
    'baseline_sha256': '8daeef57e5871abeb21a73d7daca5b0e1a02ae0824ccc481c62e7977fa365167',
    'manifest_sha256': 'b697628ac2588881628e809e207a8bbc5e88f9d0ab40a433749e1d875aa38ccd',
    'checkpoint_sha256': 'a16ccd5b823f385890cc119fe8cd427ee9908906c05bad73271c06b220ad9228',
    'boot': '8100a7fd-0c6a-46c4-82b8-f874988a1521',
    'baseline_pid': 1334, 'candidate_pid': 240801, 'restored_pid': 260102,
    'baseline_pin_count': 19,
}
FIELDS = {'version', 'enabled', 'board_boot_id', 'camera_pid', 'camera_start_ticks',
          'camera_cmdline_sha256', 'camera_config', 'identity_config', 'source_sha256',
          'database', 'model_id', 'dimension', 'model_sha256', 'result_ttl_ms', 'backend'}


class Refused(RuntimeError):
    pass


def need(value, code):
    if not value:raise Refused(code)


def digest(raw):return hashlib.sha256(raw).hexdigest()


def sha(value):return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'duplicate_metadata_key');result[key] = value
    return result


def parse(raw):
    need(len(raw) <= 262144, 'metadata_too_large')
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(Refused('nonfinite_metadata')))


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def private_read(name):
    path = Path(name)
    need(path.is_absolute() and path.resolve() == path and not path.is_symlink() and path.is_file(),
         'private_metadata_path_redirected_or_missing')
    info = path.stat()
    need(info.st_uid == os.geteuid() and not info.st_mode & 0o077, 'private_metadata_permissions_required')
    return path.read_bytes()


class FrozenJournal:
    def __init__(self, value):self.value = copy.deepcopy(value)
    def read(self):return copy.deepcopy(self.value)
    def save(self, value):raise Refused('readonly_helper_cannot_change_trial_journal')


def load_executor(path, expected, *, reader=private_read, authority=AUTHORITY):
    need(path == authority['executor_path'] and expected == authority['executor_sha256'],
         'exact_reviewed_v3_executor_path_and_sha_required')
    raw = reader(path)
    need(digest(raw) == expected, 'reviewed_executor_source_changed')
    module = types.ModuleType('_verified_complete_trial_readonly')
    module.__file__ = path
    # __name__ is never __main__; the reviewed source defines classes only.
    exec(compile(raw, path, 'exec'), module.__dict__)
    return module


def readonly_system(executor):
    class ReadOnly(executor.System):
        def command(self, *args):
            need(args and args[0] == 'show' and executor.UNIT in args, 'service_mutation_forbidden')
            return super().command(*args)
        def write_dropin(self, *args, **options):raise Refused('dropin_mutation_forbidden')
        def remove_dropin(self, *args, **options):raise Refused('dropin_mutation_forbidden')
        def checkpoint_validate(self, *args, **options):raise Refused('checkpoint_admission_forbidden')
        def validate_seed_abi(self, seed):
            # Original pure structure/range validation, NOT restore_seed and
            # NOT load_business_checkpoint (which correctly refuses consumed).
            sys.path.insert(0, executor.SOURCE_ROOT)
            protection = importlib.import_module('board.vision.native_protection')
            binding = importlib.import_module('board.vision.native_binding')
            for module, relative in [(protection, '/board/vision/native_protection.py'),
                                     (binding, '/board/vision/native_binding.py')]:
                need(str(Path(module.__file__).resolve()) == executor.SOURCE_ROOT+relative,
                     'original_native_structure_validator_path_changed')
            protection.make_native_seed(seed, binding.Seed, binding.Recovery)
    return ReadOnly()


def current_owner(executor, system, data, authority):
    owner = data['restored']
    need(owner['pid'] == authority['restored_pid'] and owner['argv'] == data['baseline_argv']
         and owner['argv'] == ['/usr/bin/python3', '-B', executor.BASE], 'restored_original_entry_required')
    observed = system.owner(owner['pid'])
    need(observed == owner, 'restored_owner_pid_birth_cmdline_changed')
    return observed


def completed_invariants(executor, system, instance, data):
    props = instance.invariants(guarded=False, argv=data['baseline_argv'])
    need(props['ActiveState'] == 'active' and int(props['MainPID']) == data['restored']['pid']
         and executor.no_unit_job(props['Job']), 'restored_unit_not_stable')
    for key in ('Restart', 'SendSIGKILL', 'TimeoutStopUSec', 'KillSignal'):
        need(props[key] == data['unit'][key], 'original_unit_properties_not_restored')
    need(not system.exists(data['dropin']) and data['dropin'] not in props['DropInPaths'].split()
         and not any(executor.trial_dropin(name) for name in props['DropInPaths'].split()),
         'trial_guard_still_present')
    instance.exact_owner(props, data['restored'], data['baseline_argv'])
    return props


def consumed_checkpoint(executor, system, data, authority):
    handoff = data['handoff'];source = handoff['source']
    need(source == data['candidate'] and source['pid'] == authority['candidate_pid']
         and system.owner(source['pid']) is None, 'candidate_predecessor_not_confirmed_dead')
    need(handoff['sha256'] == authority['checkpoint_sha256'], 'explicit_reviewed_latest_checkpoint_required')
    raw = system.read(executor.CHECKPOINT, private=True)
    need(digest(raw) == handoff['sha256'], 'latest_checkpoint_bytes_changed')
    document = parse(raw);seed = document.get('seed', {});aux = document.get('auxiliary', {})
    need(document.get('schema') == 'aura-native-protection-checkpoint-2'
         and document.get('scope') == 'final_quiescent_before_native_owner_close'
         and document.get('source_unit_sha256') == executor.NATIVE_UNIT
         and seed == handoff['seed'] and seed.get('source_manifest_sha256') == executor.NATIVE_MANIFEST
         and seed.get('purpose') == 'final_quiescent_business_checkpoint'
         and seed.get('checkpoint_kind') == 1 and seed.get('fenced') == 0
         and seed.get('boot_id') == data['boot'] and seed.get('source_pid') == source['pid']
         and str(seed.get('source_birth_ticks')) == source['birth'],
         'exact_sealed_same_boot_checkpoint_provenance_required')
    need(all(type(aux.get(k)) is int and aux[k] == 0 for k in ('active', 'primary_waiting', 'fenced'))
         and aux.get('pending_result_tokens') == [0, 0, 0]
         and all(type(x) is int for x in aux['pending_result_tokens'])
         and aux.get('sface_counters') == handoff['sface_counters']
         and document.get('previous_kernel_history') == handoff.get('previous_kernel_history'),
         'checkpoint_counters_quiescence_or_history_changed')
    need(type(seed.get('captured_mono_ns')) is int
         and handoff['captured_after_stop_ns'] <= seed['captured_mono_ns'] <= system.now(),
         'checkpoint_not_fresh_after_candidate_normal_stop')
    marker = executor.CHECKPOINT+'.native-consumed-'+handoff['sha256']
    need(handoff['consumption_marker'] == marker
         and system.read(marker, private=True) == (handoff['sha256']+'\n').encode(),
         'exact_existing_same_boot_consumption_marker_required')
    system.validate_seed_abi(seed)
    return {'checkpoint_sha256': handoff['sha256'], 'consumption_marker_sha256': digest((handoff['sha256']+'\n').encode())}


def build(executor, system, *, journal_path, expected_journal_sha256,
          baseline_path, expected_baseline_sha256, executor_path, expected_executor_sha256,
          reader=private_read, authority=AUTHORITY):
    need(journal_path == authority['journal_path'] and baseline_path == authority['baseline_path']
         and expected_baseline_sha256 == authority['baseline_sha256']
         and executor_path == authority['executor_path']
         and expected_executor_sha256 == authority['executor_sha256']
         and sha(expected_journal_sha256), 'explicit_reviewed_complete_trial_inputs_required')
    need(digest(reader(executor_path)) == expected_executor_sha256, 'reviewed_executor_source_changed')
    journal_raw = reader(journal_path)
    need(digest(journal_raw) == expected_journal_sha256, 'complete_journal_sha_mismatch')
    data = parse(journal_raw)
    need(data.get('schema') == 'aura-face-cadence-trial-1' and data.get('phase') == 'COMPLETE'
         and data.get('boot') == authority['boot'] and system.boot() == authority['boot']
         and data.get('manifest_sha256') == authority['manifest_sha256']
         and data.get('baseline', {}).get('pid') == authority['baseline_pid']
         and data.get('candidate', {}).get('pid') == authority['candidate_pid']
         and data.get('restored', {}).get('pid') == authority['restored_pid'],
         'exact_reviewed_complete_same_boot_owner_chain_required')
    baseline_raw = reader(baseline_path)
    need(digest(baseline_raw) == expected_baseline_sha256
         and data.get('readback_path') == baseline_path
         and data.get('readback_sha256') == expected_baseline_sha256, 'original_private_readback_changed')
    baseline = parse(baseline_raw)
    need(set(baseline) == FIELDS and baseline == data.get('baseline_config')
         and baseline.get('version') == 1 and baseline.get('enabled') is True
         and baseline.get('board_boot_id') == data['boot']
         and baseline.get('camera_pid') == data['baseline']['pid']
         and baseline.get('camera_start_ticks') == data['baseline']['birth']
         and baseline.get('camera_cmdline_sha256') == data['baseline']['cmd_sha256']
         and baseline.get('dimension') == 128 and baseline.get('backend') == 'DPU_SFACE_INT8'
         and len(baseline.get('source_sha256', {})) == authority['baseline_pin_count'],
         'original_readback_schema_or_complete_journal_binding_changed')
    for name, expected in baseline['source_sha256'].items():
        need(data['pins'].get(name) == expected, 'journal_would_replace_original_source_pin')
    instance = executor.Trial(system, FrozenJournal(data))
    first = current_owner(executor, system, data, authority)
    completed_invariants(executor, system, instance, data)
    checkpoint_proof = consumed_checkpoint(executor, system, data, authority)
    health = instance.running_health(first, data['handoff'])
    need(health.get('same_boot_verified') is True
         and health['runtime_path'] == data['restored_health']['runtime_path']
         and health['runtime_sha256'] == data['restored_health']['runtime_sha256']
         and health['service_epoch'] == data['restored_health']['service_epoch']
         and health['camera_epoch'] == data['restored_health']['camera_epoch'], 'restored_runtime_or_epoch_changed')
    candidate = copy.deepcopy(baseline)
    candidate.update(board_boot_id=data['boot'], camera_pid=first['pid'],
                     camera_start_ticks=first['birth'], camera_cmdline_sha256=first['cmd_sha256'],
                     camera_config=health['runtime_path'])
    need(candidate['camera_config'] not in baseline['source_sha256'], 'new_runtime_pin_already_present')
    candidate['source_sha256'][candidate['camera_config']] = health['runtime_sha256']
    need(len(candidate['source_sha256']) == authority['baseline_pin_count']+1,
         'source_pin_extension_not_exactly_one_runtime')
    completed_invariants(executor, system, instance, data)
    health2 = instance.running_health(first, data['handoff'])
    need(all(health2.get(key) == health.get(key) for key in
             ('runtime_path', 'runtime_sha256', 'service_epoch', 'camera_epoch', 'same_boot_verified')),
         'restored_health_provenance_changed_during_proof')
    need(current_owner(executor, system, data, authority) == first, 'owner_changed_during_readback_proof')
    need(digest(reader(journal_path)) == expected_journal_sha256
         and digest(reader(baseline_path)) == expected_baseline_sha256
         and digest(reader(executor_path)) == expected_executor_sha256,
         'reviewed_inputs_changed_during_proof')
    need(consumed_checkpoint(executor, system, data, authority) == checkpoint_proof,
         'checkpoint_proof_changed_during_readback_proof')
    need(digest(system.read(candidate['camera_config'], private=True)) == health['runtime_sha256'],
         'new_runtime_changed_during_proof')
    observation = {'executor_sha256': expected_executor_sha256, 'journal_sha256': expected_journal_sha256,
                   'baseline_sha256': expected_baseline_sha256, 'owner': first,
                   'runtime_sha256': health['runtime_sha256'],
                   'original_source_pins_sha256': digest(encoded(baseline['source_sha256'])),
                   'extended_source_pins_sha256': digest(encoded(candidate['source_sha256'])),
                   'service_epoch': health['service_epoch'], 'camera_epoch': health['camera_epoch'],
                   **checkpoint_proof}
    report = {'ready': True, 'status': 'SAME_BOOT_RESTORED_READBACK_CANDIDATE_READY_NOT_INSTALLED',
              'owner': {'board_boot_id': data['boot'], 'camera_pid': first['pid'],
                        'camera_start_ticks': first['birth'], 'camera_cmdline_sha256': first['cmd_sha256']},
              'original_pin_count': authority['baseline_pin_count'],
              'candidate_pin_count': len(candidate['source_sha256']),
              'candidate_sha256': digest(encoded(candidate)), 'observation_sha256': digest(encoded(observation)),
              'journal_sha256': expected_journal_sha256, 'executor_sha256': expected_executor_sha256,
              'latest_consumed_checkpoint_sha256': checkpoint_proof['checkpoint_sha256'],
              'new_runtime_sha256': health['runtime_sha256'],
              'private_original_config_changed': False, 'database_opened': False,
              'native_runner_loaded': False, 'service_action_sent': False,
              'checkpoint_or_marker_modified': False, 'new_boot_admission_used': False,
              'written': False}
    return candidate, report


def write_candidate(candidate, report, *, private_root, output, proof_output, expected_observation):
    need(os.name == 'posix' and os.geteuid() == 0, 'actual_root_posix_write_required')
    need(expected_observation == report['observation_sha256'], 'reviewed_observation_token_mismatch')
    root = Path(private_root);target = Path(output);proof = Path(proof_output)
    need(root.is_absolute() and root.resolve() == root and not root.is_symlink()
         and str(root).startswith('/home/root/aura-board-owner-candidate-20261030/'), 'new_private_board_root_required')
    for directory in {root, target.parent, proof.parent}:
        info = directory.stat()
        need(directory.resolve() == directory and stat.S_ISDIR(info.st_mode)
             and info.st_uid == 0 and not info.st_mode & 0o077, 'private_root_owned_output_directory_required')
    forbidden = set(candidate['source_sha256'])|{candidate['database'], AUTHORITY['baseline_path'],
                                                AUTHORITY['journal_path'], AUTHORITY['executor_path']}
    for name in (target, proof):
        need(name.is_absolute() and name.resolve() == name and root in name.parents
             and name.suffix == '.json' and str(name) not in forbidden
             and not os.path.lexists(str(name)), 'exclusive_new_private_output_required')
    need(target != proof, 'distinct_proof_output_required')
    # Both files are new artifacts. Neither is an active configuration and
    # neither existing file is replaced, removed or truncated on any error.
    descriptors = []
    try:
        for name in (target, proof):
            descriptors.append(os.open(str(name), os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW|os.O_CLOEXEC, 0o600))
        result = dict(report, written=True, status='SAME_BOOT_READBACK_CANDIDATE_WRITTEN_NOT_INSTALLED')
        for fd, raw in zip(descriptors, (encoded(candidate), encoded(result))):
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                stream.write(raw);stream.flush();os.fsync(stream.fileno())
        for directory in {target.parent, proof.parent}:
            fd = os.open(str(directory), os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)
        return result
    finally:
        for fd in descriptors:os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executor-path', required=True)
    parser.add_argument('--expected-executor-sha256', required=True)
    parser.add_argument('--journal', required=True)
    parser.add_argument('--expected-journal-sha256', required=True)
    parser.add_argument('--baseline-config', required=True)
    parser.add_argument('--expected-baseline-sha256', required=True)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--private-root');parser.add_argument('--output');parser.add_argument('--proof-output')
    parser.add_argument('--expected-observation-sha256')
    args = parser.parse_args()
    report = {'ready': False, 'written': False}
    try:
        need(os.name == 'posix' and os.geteuid() == 0, 'actual_root_posix_required')
        executor = load_executor(args.executor_path, args.expected_executor_sha256)
        system = readonly_system(executor)
        options = dict(journal_path=args.journal, expected_journal_sha256=args.expected_journal_sha256,
                       baseline_path=args.baseline_config, expected_baseline_sha256=args.expected_baseline_sha256,
                       executor_path=args.executor_path, expected_executor_sha256=args.expected_executor_sha256)
        candidate, report = build(executor, system, **options)
        if args.write:
            need(args.private_root and args.output and args.proof_output and args.expected_observation_sha256,
                 'write_requires_new_private_paths_and_reviewed_observation')
            need(report['observation_sha256'] == args.expected_observation_sha256,
                 'reviewed_observation_token_mismatch')
            # A second complete current-owner/source/counter proof immediately
            # precedes exclusive output creation. No volatile counters enter
            # the review token, so normal live progress cannot invalidate it.
            again, proof = build(executor, system, **options)
            need(again == candidate and proof['observation_sha256'] == report['observation_sha256'],
                 'proof_changed_before_exclusive_write')
            report = write_candidate(candidate, proof, private_root=args.private_root, output=args.output,
                                     proof_output=args.proof_output, expected_observation=args.expected_observation_sha256)
    except Exception as exc:
        # Only metadata/error class is emitted; never dump private journal,
        # health, checkpoint token arrays, gallery paths or exception payloads.
        report = {'ready': False, 'written': False,
                  'status': str(exc) if isinstance(exc, Refused) or type(exc).__name__ == 'Refused' else type(exc).__name__,
                  'database_opened': False, 'service_action_sent': False,
                  'checkpoint_or_marker_modified': False}
    print(json.dumps(report, sort_keys=True))
    return 0 if report.get('ready') else 2


if __name__ == '__main__':raise SystemExit(main())
