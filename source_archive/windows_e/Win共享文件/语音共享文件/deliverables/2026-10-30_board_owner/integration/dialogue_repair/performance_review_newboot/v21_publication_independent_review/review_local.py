"""Read-only frozen v21 source audit. Test artifacts stay in this review folder."""
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parents[1]
CANDIDATE = REPAIR / 'release_v21_asr2_display_candidate'
HANDOFF_SHA = '345d4d7157eac9ef58f91e10698ca2acdcd4ab2c2504df167fddf31d09c647e8'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert sha(CANDIDATE / 'HANDOFF.json') == HANDOFF_SHA
handoff = json.loads((CANDIDATE / 'HANDOFF.json').read_bytes())
for relative, row in handoff['files'].items():
    assert sha(CANDIDATE / relative) == row['sha256'], relative
    assert (CANDIDATE / relative).stat().st_size == row['bytes'], relative
sys.path.insert(0, str(CANDIDATE))
import stability_common as common
import apply_stability_closed as apply
import seal_stability as seal
import test_configuration_closure
import test_saved_pause
import test_seal_stability

baseline, proposal = common.baseline(), common.proposed()
assert common.encoded(baseline) == (CANDIDATE / 'baseline_spec.json').read_bytes()
assert common.encoded(proposal) == (CANDIDATE / 'proposed_spec.json').read_bytes()
assert proposal['startup_sha256'] == '94f665cf69e861d4f3d625dd627116218120cdbbef2244aa4cf2b63c39b9f1c7'
generated = {
    'FROZEN_PUBLISH_BASELINE_REMOTE.py': common.publisher_remote(baseline),
    'FROZEN_PUBLISH_CONFIGURATION_REMOTE.py': common.publisher_remote(proposal),
    'FROZEN_APPLY_REMOTE.py': apply.build_remote(proposal),
    'FROZEN_SEAL_REMOTE.py': seal.REMOTE,
}
for name, source in generated.items():
    assert source.encode() == (CANDIDATE / name).read_bytes(), name
    ast.parse(source, feature_version=(3, 9))
assert common.PAYLOAD_FINALIZED is True
assert proposal['expected_final_listening_enabled'] is False
assert len(proposal['component_sha256']) == 380
assert {name for name in baseline['component_sha256']
        if baseline['component_sha256'][name] != proposal['component_sha256'][name]} == {
            'tools/board_avatar_gtk.py', 'config/board_avatar_gtk.json'}

preflight_path = REPAIR / 'progress_followup_20261031/v21_preflight_paths_1793504768885442500.json'
preflight = json.loads(preflight_path.read_bytes())
assert preflight['startup_sha256'] == common.BASE_STARTUP_SHA
assert preflight['configuration_sha256'] == common.BASE_CONFIG_SHA
assert preflight['configuration_path'] != common.PREPARED_CONFIG_PATH
assert preflight['configuration_is_runtime_path'] is False
assert preflight['external_configuration_bytes'] == 4074

port_tests = REPAIR / 'release_v18_minor_ui_candidate/port_release_wait_candidate/test_ownerless_port_wait.py'
common.pinned(port_tests, 'bac051365f6c77a79b646f74b98f9c3d057755a5415807f859e3d5f32b8a5762')
spec = importlib.util.spec_from_file_location('independent_port_wait_tests', port_tests)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(item) for item in
    (test_configuration_closure, test_saved_pause, test_seal_stability, module))
log = io.StringIO()
# Original seal tests create temporary public JSON. Relocate those fixtures here.
with patch.object(seal, 'HERE', HERE), patch.object(common, 'execute_remote', side_effect=AssertionError('device access forbidden')):
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
for relative, row in handoff['files'].items():
    assert sha(CANDIDATE / relative) == row['sha256'], relative
assert sha(CANDIDATE / 'HANDOFF.json') == HANDOFF_SHA
report = {
    'status': 'PASS_READ_ONLY_FROZEN_PUBLICATION_REVIEW' if result.wasSuccessful() else 'FAIL',
    'handoff_sha256': HANDOFF_SHA,
    'tests_run': result.testsRun,
    'passed': result.testsRun - len(result.skipped) - len(result.errors) - len(result.failures),
    'skipped': len(result.skipped),
    'errors': len(result.errors),
    'failures': len(result.failures),
    'review_script_sha256': sha(Path(__file__)),
    'all_frozen_file_pins_verified_before_and_after': True,
    'four_generated_remotes_match_frozen_bytes': True,
    'startup_sha256': proposal['startup_sha256'],
    'configuration_sha256': proposal['configuration_sha256'],
    'component_pins': 380,
    'external_preflight_sha256': sha(preflight_path),
    'candidate_modified': False,
    'device_accessed': False,
    'observations': [
        'Only GTK source and GUI asr_threads 3 to 2 change in the 380-component closure.',
        'Startup config binds the new GUI through component_sha256. Runtime config and new prepared-gui external reference share 228abe8f.',
        'Old external 5518 configuration is read from the pinned prior manifest, backed up and verified unchanged after installation.',
        'Apply requires natural NORMAL_CLOSED state, UI/writer/speaker locks and verified private bootstrap before staging or mutation.',
        'Backup and prepared files are written before the install intent. Installation errors leave the owner closed with the guard retained.',
        'The apply action has no automatic rollback or restart. A partial write requires guarded recovery from its backup and intent record.',
        'Normal WM_DELETE, existing lifecycle guards and legacy CONFIG_SHA anchor remain intact.',
        'Ready and seal require the saved false preference, PAUSED, microphone closed and no playback.',
        'Public seal interruption fixtures preserve recoverable old/new pointer combinations and reject a foreign canonical update.',
        'Actual Linux lock/port behavior and five-second display keepalive remain root acceptance.'
    ],
    'failed_tests': [{'id': test.id(), 'traceback': error} for test, error in result.failures + result.errors],
}
(HERE / 'REVIEW.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
(HERE / 'PUBLIC_TESTS.log').write_text(log.getvalue(), encoding='utf-8')
print(json.dumps({key: report[key] for key in ('status', 'tests_run', 'passed', 'skipped', 'errors', 'failures')}))
if not result.wasSuccessful():
    print(log.getvalue()[-10000:])
raise SystemExit(0 if result.wasSuccessful() else 1)
