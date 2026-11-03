"""Local source evidence only; no device/model imports or execution."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parents[1]
INTEGRATION = HERE.parents[2]


def record(path):
    raw = path.read_bytes()
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def main():
    files = {name:record(HERE/name) for name in
             ('probe_coexist.py','tests/test_coexist.py','tests.xml','README.txt','freeze.py')}
    dependencies = dict(
        public_pipeline=record(INTEGRATION/'resume_frontend_optimization/board_audio_runtime_probe.py'),
        root_guard=record(REPAIR/'first_wait_asr_candidate/probe_asr_abba.py'),
        original_ctc_probe=record(REPAIR/'first_wait_streaming_candidate/public_streaming_probe.py'),
        actual_ctc_receipt=record(REPAIR/'first_wait_streaming_candidate/ROOT_RESULT.json'),
        download_manifest=record(REPAIR/'first_wait_streaming_candidate/download_manifest.json'))
    value = dict(status='PUBLIC_RAW_COEXIST_PROBE_READY_NOT_EXECUTED', files=files, dependencies=dependencies,
        baseline_startup_sha256='39b102a4a505db491cf06b90e3a5232bfb656c79cb0a3c221551d76d414a9a0a',
        raw_capture_frames=8, asr_transport_samples=16000, asr_transport_bytes=32000,
        asr_transport_policy='fixed credits include queued+sent+unACKed; overflow fails entire probe',
        asr_threads=1, asr_input='original PCM16 RAW', gtcrn_vad_unchanged=True,
        raw_input_frame_ms=20, gtcrn_fft_hop_ms=16, gtcrn_output_samples_per_call=[0,256,512],
        extra_frontend_resident=True, production_frontend_also_resident=True,
        production_clip_ticket_bridge_implemented=False, production_source_changed=False,
        production_cache_or_DB_touched=False, model_or_device_actions_by_agent=[],
        tests=dict(main_passed=10, subtests_passed=4, failed=0, actual_models_executed=False),
        actual_accuracy_acceptance=False, actual_fps_acceptance=False, actual_coexist_acceptance=False,
        root_execution_only=True)
    path = HERE/'HANDOFF.json'
    path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(dict(handoff_sha256=record(path)['sha256'], probe_sha256=files['probe_coexist.py']['sha256'])))


if __name__=='__main__': main()
