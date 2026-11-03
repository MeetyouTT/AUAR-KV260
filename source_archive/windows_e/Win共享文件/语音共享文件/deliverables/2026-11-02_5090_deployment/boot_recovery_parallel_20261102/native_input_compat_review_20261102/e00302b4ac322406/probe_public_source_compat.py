"""Three RAM-only checks of exact e003 provenance helper, no Native execution."""
import ast
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT.parent
EXPECTED_SHA = 'e00302b4ac322406482bcef822dbb0db2596c7d94069f0f2f52fd78b95149d66'
candidate = HERE / 'validate_fresh_final_history_original_migration.py'
raw = candidate.read_bytes()
assert hashlib.sha256(raw).hexdigest() == EXPECTED_SHA
tree = ast.parse(raw)
names = {'require', 'sha', 'digest', 'pin', 'validate_original_operator_migration'}
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
assert len(functions) == len(names)
namespace = dict(Path=PurePosixPath, hashlib=hashlib,
                 SOURCE_UNIT='7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32')
exec(compile(ast.Module(body=functions, type_ignores=[]), str(candidate) + '::<RAM-only-helper>', 'exec'), namespace)
proof_receipt = json.loads((HERE.parent / 'ORIGINAL_MIGRATION_EVIDENCE_RESULT.json').read_bytes())['board_result']
observation = proof_receipt['observation']
runtime_path = BASE.parent / '2026-10-24_pan_follow_shadow/source/native_operator_v1/runtime-manifest.json'
runtime_raw = runtime_path.read_bytes()
assert hashlib.sha256(runtime_raw).hexdigest() == observation['native_operator_manifest_pin']['sha256']
runtime = json.loads(runtime_raw)


class CapturedMetadata:
    def __init__(self):
        self.reads = []
        self.pinned_queries = []

    def pinned(self, entry):
        self.pinned_queries.append(copy.deepcopy(entry))
        if entry == proof_receipt['observation_pin']:
            return copy.deepcopy(observation)
        if entry == observation['native_operator_manifest_pin']:
            return copy.deepcopy(runtime)
        raise AssertionError('Unexpected input after first blocked source: ' + str(entry))

    def read(self, path):
        self.reads.append(path)
        raise AssertionError('Metadata-only pin should reject Python before any source read')


expected = dict(boot_id=observation['boot_id'], camera_owner=observation['source_owner'],
                owner_run_config_pin=observation['owner_run_config_pin'],
                original_operator_migration_pin=proof_receipt['observation_pin'])
settings = proof_receipt['actual_settings']
native = dict(source_unit_sha256=settings['predecessor_unit_sha256'],
              library=settings['old_library'], library_sha256=settings['old_library_sha256'])
# Synthetic stop time only for the narrow helper's time ordering; no real stop
# intent/result or checkpoint is created or claimed by this local probe.
intent = dict(stop_intent_mono_ns=observation['observed_mono_ns'] + 1)
checks = []
assert namespace['pin'](observation['native_operator_manifest_pin']) == PurePosixPath(observation['native_operator_manifest_pin']['path'])
checks.append(dict(name='original_json_pin_positive_control', outcome='PASS'))
direct = CapturedMetadata()
namespace['validate_original_operator_migration'](expected, direct,
    dict(native, source_unit_sha256=namespace['SOURCE_UNIT']), intent)
assert not direct.pinned_queries and not direct.reads
checks.append(dict(name='unchanged_direct_current_unit_positive_control', outcome='PASS'))
snapshot = CapturedMetadata()
try:
    namespace['validate_original_operator_migration'](expected, snapshot, native, intent)
except ValueError as exc:
    assert str(exc) == 'Canonical absolute JSON metadata pin required'
    assert len(snapshot.pinned_queries) == 2 and not snapshot.reads
    first = next(iter(runtime['files']))
    assert PurePosixPath(first).suffix == '.py'
    checks.append(dict(name='accepted_original_RAM_migration_input', outcome='BLOCKING_COUNTEREXAMPLE_REPRODUCED',
                       actual='ValueError: ' + str(exc), blocked_original_member=first,
                       expected='Pinned original migration closure must be readable without changing Native or live config',
                       no_source_or_library_opened=True))
else:
    raise AssertionError('Exact e003 counterexample unexpectedly disappeared')
result = dict(candidate_sha256=EXPECTED_SHA, checks=checks, tests_run=3,
              successful_positive_controls=2, blocking_counterexamples=1,
              old65_50_8_suites_rerun=False, full_original_reader_executed=False,
              real_stop_or_final_constructed=False, board_calls=0, Native_context_or_library_loaded=False)
(HERE / 'PUBLIC_SOURCE_READER_COUNTEREXAMPLE.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
