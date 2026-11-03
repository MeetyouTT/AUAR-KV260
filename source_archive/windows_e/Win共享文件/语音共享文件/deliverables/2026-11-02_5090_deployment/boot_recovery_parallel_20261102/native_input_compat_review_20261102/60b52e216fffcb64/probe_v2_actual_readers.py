"""Exact V2 reader classes on local synthetic files; no board or Native load.

Windows lacks Linux O_NOFOLLOW/O_CLOEXEC. The adapter below supplies zero for
those constants and binary Windows opens. This checks real class behavior,
hashes and file identity, not Linux kernel flag enforcement. The separate CPU
target receipt supplies the actual original-file/Linux byte-reader evidence.
"""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SHA = '60b52e216fffcb64cd7860447d2a62d4bf1b39556532a6af819e85d7760f0d7f'
raw = (HERE / 'validate_fresh_final_history_original_migration_v2.py').read_bytes()
assert hashlib.sha256(raw).hexdigest() == SHA
tree = ast.parse(raw)
names = {'require', 'sha', 'digest', 'pin', 'OriginalPublicSourcePins', 'Snapshot'}
nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]


class WindowsByteIO:
    O_NOFOLLOW = getattr(os, 'O_NOFOLLOW', 0)
    O_CLOEXEC = getattr(os, 'O_CLOEXEC', 0)

    def __getattr__(self, name):
        return getattr(os, name)

    @staticmethod
    def open(path, flags):
        return os.open(path, flags | getattr(os, 'O_BINARY', 0))


scope = dict(Path=Path, os=WindowsByteIO(), stat=stat, json=json, hashlib=hashlib)
exec(compile(ast.Module(body=nodes, type_ignores=[]), '<exact-v2-real-reader-classes>', 'exec'), scope)
Snapshot, Public = scope['Snapshot'], scope['OriginalPublicSourcePins']
sha = scope['sha']
work = HERE / 'local_io_cases'
work.mkdir(exist_ok=False)
assert work.resolve().parent == HERE.resolve()
checks = []


def pinned_file(name, raw):
    path = work / name
    path.write_bytes(raw)
    return dict(path=str(path.resolve()), sha256=sha(raw))


def rejects(name, call, errors=(ValueError,)):
    try:
        call()
    except errors as exc:
        checks.append(dict(case=name, outcome='EXPECTED_HOLD', reason=type(exc).__name__ + ': ' + str(exc)))
    else:
        raise AssertionError('Expected rejection: ' + name)


metadata = pinned_file('metadata.json', b'{"public":"synthetic"}\n')
source = pinned_file('synthetic-source.so', b'public synthetic library bytes; never loaded\x00\xff')
snap = Snapshot()
assert snap.pinned(metadata) == {'public': 'synthetic'}
public = Public({source['path']: source['sha256']})
snap._original_operator_public_sources = public
assert public.read(source) == Path(source['path']).read_bytes()
snap.unchanged()
checks.append(dict(case='real_Snapshot_public_reader_and_final_hook_positive', outcome='PASS'))
python = pinned_file('synthetic.py', b'pass\n')
rejects('original_JSON_pin_refuses_Python', lambda: scope['pin'](python))
rejects('original_Snapshot_read_refuses_DSO', lambda: Snapshot().read(source['path']))
rejects('dedicated_reader_refuses_unknown_path', lambda: public.read(dict(path=str(work / 'unknown.so'), sha256='1' * 64)))
rejects('dedicated_reader_refuses_conflicting_SHA', lambda: public.read(dict(source, sha256='0' * 64)))
Path(source['path']).write_bytes(b'changed bytes')
rejects('final_Snapshot_unchanged_detects_changed_source_bytes', snap.unchanged)

same = pinned_file('same-bytes.o', b'public synthetic object bytes')
stable = Snapshot()
stable._original_operator_public_sources = Public({same['path']: same['sha256']})
stable._original_operator_public_sources.read(same)
replacement = work / 'replacement.o'
replacement.write_bytes(Path(same['path']).read_bytes())
os.replace(replacement, same['path'])
rejects('final_Snapshot_unchanged_detects_same_bytes_file_replacement', stable.unchanged)
missing = dict(path=str((work / 'missing.so').resolve()), sha256='2' * 64)
rejects('dedicated_reader_refuses_missing_source', lambda: Public({missing['path']: missing['sha256']}).read(missing), (OSError, ValueError))

# Execute the exact outer migration helper using actual Snapshot JSON reads.
# POSIX path construction applies only to that helper. Its JSON Snapshot and
# reader classes retain their real local filesystem implementations.
helper_scope = dict(scope, Path=PurePosixPath,
    SOURCE_UNIT='7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32')
helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'validate_original_operator_migration')
exec(compile(ast.Module(body=[helper], type_ignores=[]), '<exact-v2-outer-helper>', 'exec'), helper_scope)
receipt = json.loads((HERE.parent / 'ORIGINAL_MIGRATION_EVIDENCE_RESULT.json').read_bytes())['board_result']
observation, settings = receipt['observation'], receipt['actual_settings']
native = dict(source_unit_sha256=settings['predecessor_unit_sha256'], library=settings['old_library'],
              library_sha256=settings['old_library_sha256'], seed={'sha256': receipt['original_audit_metadata']['checkpoint_sha256']})
expected = dict(boot_id=observation['boot_id'], camera_owner=observation['source_owner'], owner_run_config_pin=observation['owner_run_config_pin'])
intent = dict(stop_intent_mono_ns=observation['observed_mono_ns'] + 1)  # RAM-only ordering value, not a real stop intent.
validate = helper_scope['validate_original_operator_migration']
rejects('outer_helper_missing_migration_pin_real_Snapshot', lambda: validate(expected, Snapshot(), native, intent), (KeyError, ValueError))
for name, change in [('wrong_owner', lambda d: d.update(source_owner=dict(d['source_owner'], birth_ticks='999999'))),
                     ('wrong_config_pin', lambda d: d.update(owner_run_config_pin=dict(d['owner_run_config_pin'], sha256='3' * 64))),
                     ('post_intent_observation', lambda d: d.update(observed_mono_ns=intent['stop_intent_mono_ns']))]:
    document = copy.deepcopy(observation)
    change(document)
    pin = pinned_file(name + '.json', json.dumps(document, sort_keys=True).encode())
    rejects('outer_helper_' + name + '_real_Snapshot',
            lambda pin=pin: validate(dict(expected, original_operator_migration_pin=pin), Snapshot(), native, intent))
validate(expected, Snapshot(), dict(native, source_unit_sha256=helper_scope['SOURCE_UNIT']), intent)
checks.append(dict(case='original_direct_current_unit_path_retained', outcome='PASS'))

result = dict(candidate_sha256=SHA, checks=checks, local_checks=len(checks),
              actual_Snapshot_and_public_reader_classes_executed=True, actual_outer_helper_with_real_JSON_reads=True,
              all_expectations_met=True, permissive_fake_Snapshot_used=False,
              Linux_NOFOLLOW_CLOEXEC_kernel_semantics_tested=False,
              legitimate_full_original_source_positive='CPU V2_PUBLIC_SOURCE_IO_RESULT.json,14 original public files; separately attributed, not rerun by this reviewer',
              actual_full_current_final_or_Native_executed=False, old65_50_8_suites_rerun=False, board_calls=0)
(HERE / 'V2_LOCAL_ACTUAL_READER_PROBES.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
