"""Seal frozen local source and fake evidence; no application/device imports."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def fp(path):
    raw=path.read_bytes()
    return dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))

def main():
    manifest=json.loads((ROOT/'overlay_manifest.json').read_text(encoding='utf-8'))
    handoff=dict(schema='aura.complete-automatic-capture-process.rev3',
        status='FROZEN_SOURCE_ONLY_ROOT_ARM_ADMISSION_REQUIRED',hardware_executed=False,
        files=manifest['files'],artifacts={name:fp(ROOT/name) for name in
            ('frontend_capture_process.overlay.zip','overlay_manifest.json','extra_source_map.json',
             'build_overlay.py','tests.xml','tests/test_capture_contract_external.py',
             'tests/test_worker_ipc.py','ARM_ADMISSION.txt')},
        configuration=dict(frontend_process=True,frontend_capture_process=True,
            frontend_optimization='baseline',frontend_threads=1,capture_priority_nice=-10),
        default_frontend_capture_process=False,
        admission=dict(pool="create_frontend_pool(directory, optimization='baseline', num_threads=1, frontend_process=True)",
            capture="RemoteAutomaticCapture(lambda:False, frontend_pool=pool, max_seconds=2, speech_start_ready=lambda cid:True)",
            run='start; owner-thread snapshot loop for at most 1.5s; finally cancel; close; pool.close; require gate.shutdown',
            document='ARM_ADMISSION.txt'),
        model_ownership=dict(instances=1,gate='Original BoardFftSpeechGate in existing sole child',
            pool='Single original BoardFrontendPool in child arbitrates auto and gate-RPC barge',
            normal_capture='Original BoardAutomaticCapture / SpeechEndpoint / BoundedPcmCaptureMixin / 8-frame queue in child',
            parent='RemoteAutomaticCapture metadata poll plus once-only completed original PCM TAKE',
            barge='Original parent capture/echo/verification/ACK; same child gate via existing fixed-frame RPC',
            manual='Unchanged original parent manual capture',no_fallback=True,no_extra_model=True),
        protocol=dict(control_kinds=['GATE_RELEASE','AUTO_START','AUTO_POLL','AUTO_TAKE','AUTO_CANCEL','AUTO_CLOSE'],
            transport='Existing anonymous socketpair, no network listener/audio file',
            input_frame_limit=1280,control_metadata_limit=4096,completed_pcm_limit=640000,
            take_limit='Only AUTO_TAKE response permits 640000B PCM +4096B metadata+4B length',
            metadata='Strict fixed status/clip schema, fixed error codes, scalar metric white list',
            poll_interval_seconds=.05,callback='Owner start-thread snapshot/take only; current CID/recording/monitor guard',
            ready='Original Mcp READY plus reader/source/owner released; parent onset callback before READY',
            invalidation='Start/cancel/close/take local revision barriers reject late polls and completed results',
            pcm='Original CapturedAudio/AudioRef metadata + exact bytes + SHA, no parent waveform transform'),
        cleanup=dict(normal='Remote cancel/close waits original child capture cleanup, keeps worker for reuse',
            shutdown='Original pool close then owned worker STOP; 6s grace for original bounded capture cleanup, no worker SIGKILL',
            start_failure='Explicit original source/endpoint/mic lock retirement after partial original start failure',
            ipc_failure='Lost start ACK or cancel/close IPC failure retires exact owned worker, no guessing a new capture',
            abrupt_worker_exit='Original arecord argv execs under guarded Python shim: parent PID before/after Linux prctl PDEATHSIG SIGTERM',
            preexec_fn=False,retired_owner='Two bounded metadata-only tombstones allow old automatic close without affecting active barge'),
        public_metadata=dict(path='snapshot.audio_frontend (existing recording/API projection)',
            fields=['worker_pid','worker_process_alive','worker_capture_process','worker_generation','microphone_pid']),
        tests=dict(passed=19,subtests_passed=3,failed=0,seconds=2.37,evidence='tests.xml',
            groups=['12 independent real-proxy/manager/controller cases (3 corrupt metadata subcases)',
                    '4 real socketpair + original BoardAutomaticCapture/endpoint/8queue cases with fake arecord/model',
                    '3 parent-death guard/argv/payload-bound/Python3.9 source checks']),
        preserved=['Original models/thresholds/FFT/PCM/queue capacity','Parent playback and full ACK',
            'Latest independent b11 cancel-rearm and diagnostics overlays','Current appearance/persona/private data/source pins'],
        limitations=['No ARM subprocess/pass_fds/prctl/actual device test by this agent',
            'No claim that model compute or total GUI capacity passes; root admission and formal runtime observation remain',
            'Normal parent ASR/business/player still use existing process and ownership'])
    (ROOT/'HANDOFF.json').write_text(json.dumps(handoff,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(fp(ROOT/'HANDOFF.json')))

if __name__=='__main__':main()
