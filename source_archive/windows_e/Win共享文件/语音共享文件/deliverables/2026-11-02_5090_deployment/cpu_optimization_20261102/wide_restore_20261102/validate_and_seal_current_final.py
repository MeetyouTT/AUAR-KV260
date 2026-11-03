"""Bind genuine stop artifacts, run the exact reviewed reader, then seal bytes."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

require = lambda value, text: None if value else (_ for _ in ()).throw(ValueError(text))
require(hashlib.sha256(CANDIDATE_SOURCE.encode()).hexdigest() == '60b52e216fffcb64cd7860447d2a62d4bf1b39556532a6af819e85d7760f0d7f', 'Reviewed migration validator revision differs')
stop_ns = {'__name__': 'original_stop_artifact_reader'}
exec(compile(STOP_SOURCE, '<unchanged-stop-artifact-reader>', 'exec'), stop_ns)
regular, digest = stop_ns['regular'], stop_ns['digest']
session = Path(SESSION); camera_tx = Path(FRESH['normal_stop_expected']['transaction_directory'])
result_path = camera_tx / 'camera-stop-result.json'; result_raw = regular(result_path)
result = json.loads(result_raw)
require(result['status'] == 'CAMERA_STOPPED_NEW_FINAL_PRESENT' and result['normal_stop_submitted_once'] is True
        and result['forced_action'] is False, 'Normal camera stop is not complete; observe, do not retry')
intent_path = camera_tx / 'camera-stop-intent.json'; intent_raw = regular(intent_path)
require(json.loads(intent_raw) == result['intent'], 'Actual stop intent/result differ')
history_raw = regular(HISTORY_PIN['path']); require(digest(history_raw) == HISTORY_PIN['sha256'], 'Independent prestop history changed')
history = json.loads(history_raw)
e = FRESH['normal_stop_expected']; closure = e['source_closure']
expected = dict(schema='aura-fresh-final-history-expected-1', all_other_writers_frozen=True,
                boot_id=GRANT['boot_id'], camera_owner=GRANT['camera_owner'], stopped_gui_owners=e['stopped_gui_owners'],
                startup=e['startup'], checkpoint_pin=result['fresh_checkpoint'],
                owner_run_config_pin=closure['owner_run_config'], source_manifest_pin=closure['native_python_manifest'],
                source_unit_sha256='7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32',
                stop_intent_pin=dict(path=str(intent_path),sha256=digest(intent_raw)),
                stop_result_pin=dict(path=str(result_path),sha256=digest(result_raw)),
                history=history, original_operator_migration_pin=MIGRATION_OBSERVATION_PIN)
def put(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(directory)
    finally: os.close(directory)
    return dict(path=str(path),sha256=digest(raw))
expected_raw = (json.dumps(expected,sort_keys=True,indent=2)+'\n').encode()
expected_pin = put(session/'fresh-final-history.expected.json',expected_raw)
reader = {'__name__': 'reviewed_fresh_final_original_reader', '__file__': '<pinned-migration-adapter-v2>'}
exec(compile(CANDIDATE_SOURCE,'<pinned-migration-adapter-v2>','exec'),reader)
output = io.StringIO(); previous = sys.argv
failure = None
try:
    sys.argv = ['original_full_history','--expected',expected_pin['path'],'--expected-sha256',expected_pin['sha256']]
    with contextlib.redirect_stdout(output): reader['main']()
except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError,SystemExit) as error:
    failure=dict(type=type(error).__name__,reason=str(error))
finally:
    sys.argv = previous
if failure is not None:
    print(json.dumps(dict(status='HOLD_ORIGINAL_FULL_READER_DID_NOT_PASS',failure=failure,
                         expected_pin=expected_pin,genuine_stop_checkpoint_pin=result['fresh_checkpoint'],
                         camera_stop_resubmitted=False,DFX_or_start_requested=False),sort_keys=True))
    raise SystemExit(0)
validation = json.loads(output.getvalue())
require(validation['status']=='ORIGINAL_CURRENT_FINAL_AND_COMPLETE_HISTORY_VERIFIED'
        and validation['checkpoint_pin']==result['fresh_checkpoint']
        and validation['source_owner']==GRANT['camera_owner']
        and validation['archive_count']==history['archive_count']
        and validation['original_load_business_checkpoint_called'] is True
        and validation['complete_ordered_history_verified'] is True
        and validation['all_required_current_boot_cumulative_lower_bounds_checked'] is True
        and validation['checkpoint_consumed'] is False, 'Original full validation result is incomplete')
validation_raw=(json.dumps(validation,sort_keys=True,indent=2)+'\n').encode()
validation_pin=put(session/'original-full-history-result.json',validation_raw)
checkpoint_raw=regular(result['fresh_checkpoint']['path'],262144)
require(digest(checkpoint_raw)==result['fresh_checkpoint']['sha256'], 'Current final changed after original validation')
sealed=put(session/('sealed-current-final-'+digest(checkpoint_raw)+'.json'),checkpoint_raw)
jobs=subprocess.run(['systemctl','list-jobs','--no-legend','--no-pager','--plain'],capture_output=True,text=True,timeout=5)
require(jobs.returncode==0,'Cannot inspect pending jobs after normal stop')
pending=[line for line in jobs.stdout.splitlines() if line.strip() and line.strip() not in ('No jobs running.','0 jobs listed.')]
require(not pending,'Pending systemd jobs remain after full reader; do not continue to DFX')
print(json.dumps(dict(status='CPU_NORMAL_STOP_CURRENT_FINAL_AND_COMPLETE_HISTORY_SEALED',
                     boot_id=GRANT['boot_id'],startup_sha256=GRANT['startup_sha256'],
                     camera_owner_stopped=GRANT['camera_owner'],genuine_checkpoint_pin=result['fresh_checkpoint'],
                     sealed_identical_final_pin=sealed,expected_pin=expected_pin,original_validation_pin=validation_pin,
                     original_validation=validation,original_guard_passed_at_validation_begin_and_end=True,
                     no_live_Native_VART_DPU_MMIO_or_render_owners_verified_by_original_guard=True,
                     no_pending_systemd_jobs=True,normal_stop_submissions=1,forced_shutdown=False,
                     original_checkpoint_or_seed_or_counter_or_marker_written_by_this_wrapper=False,
                     source_code_config_identity_memory_or_models_changed=False,
                     DFX_axis_or_camera_GUI_start_requested=False),sort_keys=True))
