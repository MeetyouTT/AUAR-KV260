"""Bounded, gracefully stoppable candidate owner using the reviewed host classes.

It serves only model requests, keeps audio in RAM and opens no business DB.
The explicit stop marker closes this candidate's server and its own TTS worker.
The fixed project daemon and unrelated models are never stopped or unloaded.
"""
import argparse
import datetime
import json
from pathlib import Path
import re
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
sys.path[:0] = [str(PROJECT / 'aura'), str(PROJECT / 'deliverables/2026-10-18_board_dialogue')]
from resume_baseline import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--lifetime-seconds', type=int, default=3600)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{32}', args.session_id) or not 60 <= args.lifetime_seconds <= 7200:
        parser.error('Use a fresh candidate run identifier and a bounded lifetime')
    window = json.loads((HERE.parent / 'coordination/runtime_windows.json').read_text(encoding='utf-8-sig'))
    if window['performance_window'].get('state') != 'BUSINESS_ACCEPTANCE_EXCLUSIVE':
        raise RuntimeError('Character resources have not been returned')
    output = HERE / 'resume_live' / args.session_id
    output.mkdir(parents=True, exist_ok=False)
    state = dict(schema_version=1, session_id=args.session_id, status='STARTING',
                 started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 business_database_opened=False, raw_audio_archived=False)
    write_json(output / 'status.json', state)
    server = models = backend = None
    server_thread = None
    try:
        from project_ollama import ensure
        daemon = ensure()
        if not daemon.get('ready') or daemon.get('needs_controlled_restart'):
            raise RuntimeError('Fixed project daemon bindings require inspection')
        from tools.service_instance_lock import ServiceInstanceLock
        from tools.voice_startup_guard import cold_capacity_preflight
        from tools.model_inference_startup import startup_models
        from tools.model_inference_host import LocalModelBackend, InferenceHost, make_server
        deadline = time.monotonic() + 300
        runtime_root = PROJECT / 'deliverables/2026-10-18_board_dialogue/model_host'
        voice_python = Path(sys.executable)
        with ServiceInstanceLock(runtime_root / 'voice8792.instance.lock') as lock:
            cold_capacity_preflight(PROJECT / 'aura', runtime_root, lock=lock,
                                    listen='192.168.50.1', port=8792, deadline=deadline)
            backend = LocalModelBackend.from_config(voice_python=str(voice_python))
            try:
                startup = startup_models(backend, lock=lock, deadline=deadline)
                models = InferenceHost(backend)
                server = make_server(('192.168.50.1', 8797), models, local_health=True)
                server_thread = threading.Thread(target=server.serve_forever,
                    kwargs=dict(poll_interval=.1), name='candidate-model-server')
                server_thread.start()
                state.update(status='READY', startup=startup,
                    ready_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    stop_marker=str(output / 'STOP'), same_unique_tts_pid=backend.voice.process.pid,
                    fixed_daemon_pid=daemon['ownership']['pid'])
                write_json(output / 'status.json', state)
                print(json.dumps(dict(status='READY', session_id=args.session_id, port=8797)), flush=True)
                expiry = time.monotonic() + args.lifetime_seconds
                while time.monotonic() < expiry and not (output / 'STOP').exists():
                    if not server_thread.is_alive():
                        raise RuntimeError('Candidate server stopped unexpectedly')
                    time.sleep(.2)
                state['stop_reason'] = 'explicit_owner_marker' if (output / 'STOP').exists() else 'bounded_lifetime'
            finally:
                if server_thread is not None and server_thread.is_alive():
                    server.shutdown()
                    server_thread.join(timeout=5)
                if server is not None:
                    server.server_close()
                if models is not None:
                    models.close()
                elif backend is not None:
                    backend.close()
            state.update(status='CLOSED', owned_tts_closed=True, server_closed=True,
                         fixed_daemon_stopped=False, unrelated_models_stopped=False)
    except BaseException as error:
        state.update(status='FAILED', error_type=type(error).__name__,
                     error_code=getattr(error, 'code', str(error))[:300])
        raise
    finally:
        state['updated_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        write_json(output / 'status.json', state)


if __name__ == '__main__':
    main()
