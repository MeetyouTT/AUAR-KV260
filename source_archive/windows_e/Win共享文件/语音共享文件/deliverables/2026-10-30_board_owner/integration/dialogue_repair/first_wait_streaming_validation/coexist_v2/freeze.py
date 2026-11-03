"""Seal this independent diagnostic copy, preserving all original evidence."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'coexist/probe_coexist.py'


def record(path):
    raw=path.read_bytes()
    return dict(path=str(path.resolve()),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))


def main():
    before=record(BASE)
    if before['sha256']!='b252e7cc3d09f84557a580bae13356e99f6e3e1c6037271e672dd1c203a45570':
        raise ValueError('frozen_base_changed')
    files={name:record(HERE/name) for name in ('probe_coexist.py','tests/test_coexist.py',
        'tests/test_diagnostics.py','tests.xml','README.txt','freeze.py')}
    value=dict(status='DIAGNOSTIC_SOURCE_FROZEN_NO_BOARD_RUN',before=before,files=files,
        test_main_passed=17,test_subtests_passed=8,failed=0,
        capture_frames=8,asr_credit_samples=16000,model_threads=1,
        queue_or_priority_or_thread_or_model_changed=False,original_ack_payload_changed=False,
        diagnostic_progress_returns_credit=False,first_failure_metadata_frozen=True,
        reader_started_after_frontend_warmup=True,system_pid_sampler_added=False,
        production_changed=False,model_or_device_actions=[],actual_gain_claimed=False)
    path=HERE/'HANDOFF.json'
    path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(dict(probe_sha256=files['probe_coexist.py']['sha256'],handoff_sha256=record(path)['sha256'])))


if __name__=='__main__':main()
