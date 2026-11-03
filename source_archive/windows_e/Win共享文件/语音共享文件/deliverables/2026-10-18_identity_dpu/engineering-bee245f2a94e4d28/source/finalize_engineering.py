"""Seal fixed-input board results and restoration evidence without raw UART."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).parent
OUT = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-18_identity_dpu/engineering-bee245f2a94e4d28')
summary = json.loads((OUT/'verification.json').read_text())
entries = {r['path']: r for r in summary['files']}


def copy(source, relative):
    target = OUT/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    data = source.read_bytes()
    if target.exists():
        assert target.read_bytes() == data, 'Changed evidence: '+relative
    else:
        shutil.copyfile(source, target)
    entries[relative] = {'path': relative, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


for name in ['board_standalone_sface.py', 'board_mixed_benchmark.py', 'run_staged_helper.py',
             'board_dpu_diagnose.py', 'board_postcheck.py', 'create_reference.py',
             'board_transfer_state.py', 'finalize_engineering.py']:
    copy(ROOT/name, 'source/'+name)
copy(OUT/'reference-generator-verification.json', 'reference-generator-verification.json')
phases = {}
for phase in ['startup-diagnose', 'standalone-board', 'standalone-board-retry', 'mixed-fixed-input', 'recovery-postcheck']:
    status = json.loads((ROOT/('latest-'+phase+'.json')).read_text())
    assert status['complete'] and status['console_echo_restored']
    folder = Path(status['evidence'])
    data = (folder/'response.json').read_bytes()
    phases[phase] = json.loads(data)
    copy(folder/'status.json', 'evidence/'+phase+'/status.json')
    copy(folder/'response.json', 'evidence/'+phase+'/response.json')
    copy(folder/'source.py', 'evidence/'+phase+'/source.py')
copy(Path('/home/ghmd/kv260-adaptation-check-20261006/evidence/20261019T020746.561401Z-transfer/status.json'), 'evidence/first-transfer-failed.json')
board = phases['standalone-board-retry']
mixed = phases['mixed-fixed-input']
post = phases['recovery-postcheck']
assert board['status'] == 'PASS_STANDALONE_DPU_ENGINEERING'
assert len(board['core']['results']) == 4 and all(r['maximum_integer_difference'] == 0 for r in board['core']['results'])
assert mixed['status'] == 'PASS_FIXED_INPUT_TWO_MODEL_BENCHMARK'
assert mixed['core']['mixed_identity_outputs_bit_exact']
assert all(r['period_overruns'] == 0 for r in mixed['core']['results'])
assert post['status'] == 'PASS_20_SECOND_RESTORED_CAMERA' and not post['production_identity_enabled']
assert post['streaming_enabled'] and not post['active_test_restore_timers']
assert all(p['ui_pid_preserved'] and p['protected_configuration_hashes_unchanged'] and p['boot_preserved'] and p['camera_restored'] for p in (board, mixed))
transfer = json.loads((ROOT/'latest-resume-transfer.json').read_text())
assert transfer['complete'] and transfer['console_echo_restored'] and transfer['retries'] == 0
summary.pop('production_code_or_services_changed', None)
summary.update(status='PASS_DPU_ENGINEERING_AND_FIXED_INPUT_MIXED_TEST_NOT_PRODUCTION_IDENTITY',
    checked_utc=datetime.now(timezone.utc).isoformat(), files=list(entries.values()),
    board_engineering_smoke=board, fixed_input_same_process_mixed_test=mixed,
    restored_camera_postcheck=post, model_executed_on_physical_dpu=True,
    dpu_exclusive_process_lock_confirmed=True,
    unified_dpu_scheduling_tested=False, live_camera_identity_mixed_workload_tested=False,
    representative_identity_calibration=False, independent_identity_accuracy_accepted=False,
    production_source_or_configuration_changed=False, production_model_replaced=False,
    production_services_temporarily_restarted=['aura-camera-ui.service'],
    gui_process_preserved=True, fpga_bitstream_changed=False,
    identity_enrollment_or_identity_database_changed=False)
for row in summary['files']:
    data = (OUT/row['path']).read_bytes()
    assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
(OUT/'verification.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'status': summary['status'], 'files_hash_verified': len(entries),
                  'board_cases_bit_exact': 4, 'mixed_identity_calls_bit_exact': 20,
                  'restored_camera_observed_hz': post['observed_detection_hz'],
                  'production_identity_accepted': False}, ensure_ascii=False))
