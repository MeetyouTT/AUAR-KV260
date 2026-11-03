"""Root-only board public WAV 3/4/4/3 probe. Default inspect, never controls GUI.

Production ASR stays resident; exactly one additional short-lived model session
exists at a time. stdout is metadata only. No microphone/player/identity/DB IO.
"""
import argparse
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
import wave

HERE = Path(__file__).resolve().parent
BASE_SHA = '4edb865881c887d6a290a02e078e14386bd95d017b79820b143b5a1e329997c3'
MODEL_SHA = 'f36a0433bcf096bd6d6f11b80a3ac8bed110bdca632fe0d731df8d1a84475945'
TOKEN_SHA = '59aba8873a2ed1e122c25fee421e25f283b63290efbde85c1f01a853d83cb6e6'
WAV = Path('/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/models/paraformer/test_wavs/0.wav')
WAV_SHA = '1a6bf94091d9c35e11aea5d494d05e3287b8f5c767f6de3bfd796d91b637500c'
ASR_DEPS = '/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps'
ERROR_CODES = frozenset(('memavailable_unavailable', 'metadata_http_failed', 'metadata_not_object',
    'startup_changed', 'boot_changed', 'production_asr_source_changed', 'gui_configuration_changed',
    'production_fps_or_threads_changed', 'production_ui_owner_changed', 'production_owner_birth_changed',
    'pause_and_idle_required', 'model_health_unavailable', 'model_or_background_summary_active',
    'memory_worker_active', 'four_core_scope_required', 'normal_priority_required', 'insufficient_memavailable',
    'candidate_changed', 'public_wav_changed', 'public_wav_format_changed', 'post_load_memavailable_below_limit',
    'production_process_identity_changed', 'owned_probe_slot_failed', 'public_transcript_changed', 'probe_refused',
    'asr_dependency_or_resource_unavailable', 'probe_memory_error', 'owned_probe_deadline', 'probe_os_error',
    'probe_invalid_metadata', 'unexpected_probe_error'))


class ProbeRefused(RuntimeError):
    def __init__(self, code): self.code = code if code in ERROR_CODES else 'probe_refused'


def error_code(error):
    if isinstance(error, ProbeRefused): return error.code
    return {'BoardAsrUnavailable': 'asr_dependency_or_resource_unavailable',
            'MemoryError': 'probe_memory_error', 'TimeoutExpired': 'owned_probe_deadline',
            'OSError': 'probe_os_error', 'ValueError': 'probe_invalid_metadata'}.get(type(error).__name__, 'unexpected_probe_error')


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def proc(pid):
    path = Path('/proc') / str(pid)
    raw = (path / 'stat').read_text()
    data = raw[raw.rfind(')')+2:].split()
    return dict(pid=pid, birth=int(data[19]), nice=int(data[16]),
                command_sha256=hashlib.sha256((path / 'cmdline').read_bytes()).hexdigest())


def available_mib():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'): return int(line.split()[1]) / 1024
    raise ProbeRefused('memavailable_unavailable')


def get(host, port, path):
    connection = http.client.HTTPConnection(host, port, timeout=2.)
    try:
        connection.request('GET', path)
        response = connection.getresponse()
        raw = response.read(1048577)
        if response.status != 200 or len(raw) > 1048576: raise ProbeRefused('metadata_http_failed')
        value = json.loads(raw)
        if not isinstance(value, dict): raise ProbeRefused('metadata_not_object')
        return value
    finally: connection.close()


def metadata(args, *, allow_background=False):
    root = Path(args.runtime_root)
    if sha(root / 'startup/config.json') != args.startup_sha256: raise ProbeRefused('startup_changed')
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    if boot != args.boot_id: raise ProbeRefused('boot_changed')
    startup = json.loads((root / 'startup/config.json').read_bytes())
    source = root / 'runtime/aura/board/runtime/audio/board_asr.py'
    if startup['component_sha256']['board/runtime/audio/board_asr.py'] != BASE_SHA or sha(source) != BASE_SHA:
        raise ProbeRefused('production_asr_source_changed')
    config_path = root / 'runtime/aura/config/board_avatar_gtk.json'
    if sha(config_path) != startup['component_sha256']['config/board_avatar_gtk.json']:
        raise ProbeRefused('gui_configuration_changed')
    config = json.loads(config_path.read_bytes())
    if config.get('stable_avatar_fps') != 16 or config['board_business'].get('asr_threads') != 3:
        raise ProbeRefused('production_fps_or_threads_changed')
    unit = subprocess.check_output(['/bin/systemctl', 'show', 'aura-avatar-ui.service',
        '-p', 'MainPID', '-p', 'ActiveState'], text=True, timeout=3.)
    properties = dict(row.split('=', 1) for row in unit.splitlines() if '=' in row)
    if properties.get('ActiveState') != 'active' or int(properties['MainPID']) != args.ui_pid:
        raise ProbeRefused('production_ui_owner_changed')
    ui, camera = proc(args.ui_pid), proc(args.camera_pid)
    if ui['birth'] != args.ui_birth or camera['birth'] != args.camera_birth:
        raise ProbeRefused('production_owner_birth_changed')
    state = get('127.0.0.1', 8783, '/api/state')
    hf = state.get('handsfree_dialogue', {})
    business = state.get('board_business', {})
    task = state.get('board_processing', {}).get('task_state')
    if (hf.get('enabled') is not False or hf.get('microphone_open') is not False
            or state.get('playing') is not False
            or task not in ('IDLE', 'CANCELLED', 'ANSWERED', 'ERROR', 'READY', 'EMPTY')
            or business.get('started') is not True or business.get('closed') is not False
            or business.get('dialogue', {}).get('pending') not in (None, False, 0)):
        raise ProbeRefused('pause_and_idle_required')
    model = get('192.168.50.1', 8797, '/health')
    if model.get('ok') is not True or model.get('role') != 'model_inference_only':
        raise ProbeRefused('model_health_unavailable')
    model_idle = model.get('active') is False and model.get('pending') == 0
    if not model_idle and not allow_background:
        raise ProbeRefused('model_or_background_summary_active')
    memory = business.get('memory', {})
    memory = {key: value for key, value in memory.items()
              if key in ('running', 'completed', 'discarded', 'active', 'busy') and type(value) in (bool, int)}
    if (memory.get('active') or memory.get('busy')) and not allow_background:
        raise ProbeRefused('memory_worker_active')
    if os.cpu_count() != 4 or len(os.sched_getaffinity(0)) != 4: raise ProbeRefused('four_core_scope_required')
    if os.getpriority(os.PRIO_PROCESS, 0) != 0: raise ProbeRefused('normal_priority_required')
    available = available_mib()
    if available < args.min_available_mib: raise ProbeRefused('insufficient_memavailable')
    return dict(boot_id=boot, startup_sha256=args.startup_sha256, ui=ui, camera=camera,
        available_mib=round(available, 2), cpu_count=4, allowed_cpus=sorted(os.sched_getaffinity(0)),
        listening_paused=True, microphone_open=False, playing=False, task_state=task,
        memory=memory, model_idle=model_idle, configured_fps=16,
        actual_fps_measured=False, production_asr_threads=3, production_asr_resident=True)


def slot(args):
    # One fresh interpreter/session; it exits before the next slot is started.
    before = metadata(args)
    sys.path.insert(0, ASR_DEPS)
    candidate = Path(args.candidate)
    if sha(candidate) != args.candidate_sha256: raise ProbeRefused('candidate_changed')
    if sha(WAV) != WAV_SHA: raise ProbeRefused('public_wav_changed')
    with wave.open(str(WAV), 'rb') as stream:
        if (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) != (1, 2, 16000):
            raise ProbeRefused('public_wav_format_changed')
        pcm = stream.readframes(stream.getnframes())
    spec = importlib.util.spec_from_file_location('_root_asr_thread_trial', candidate)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = json.loads((Path(args.runtime_root) / 'runtime/aura/config/board_avatar_gtk.json').read_bytes())
    started = time.monotonic()
    model = module.BoardParaformer(config['board_business']['asr_directory'],
        model_sha256=MODEL_SHA, tokens_sha256=TOKEN_SHA, num_threads=args.slot_threads)
    load_ms = (time.monotonic()-started)*1000
    if available_mib() < args.min_available_mib: raise ProbeRefused('post_load_memavailable_below_limit')
    warm = model.transcribe(pcm, deadline=time.monotonic()+30.)
    wall, cpu = time.monotonic(), time.process_time()
    result = model.transcribe(pcm, deadline=wall+30.)
    wall_ms, cpu_ms = (time.monotonic()-wall)*1000, (time.process_time()-cpu)*1000
    after = metadata(args, allow_background=True)
    if before['ui'] != after['ui'] or before['camera'] != after['camera']:
        raise ProbeRefused('production_process_identity_changed')
    import resource
    return dict(threads=args.slot_threads, load_ms=round(load_ms, 2), asr_ms=round(wall_ms, 2),
        process_cpu_ms=round(cpu_ms, 2), audio_seconds=len(pcm)/32000,
        characters=len(result), transcript_sha256=hashlib.sha256(result.encode()).hexdigest(),
        warmup_same_transcript=warm == result, peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        before=before, after=after, actual_fps_acceptance=False,
        background_changed=before['memory'] != after['memory'] or not after['model_idle'])


def run_slot(args, threads):
    command = [sys.executable, '-B', str(Path(__file__).resolve())] + sys.argv[1:]
    command = [value for value in command if value != '--run']
    read_fd, write_fd = os.pipe()
    command += ['--slot-threads', str(threads), '--result-fd', str(write_fd)]
    try:
        process = subprocess.Popen(command, pass_fds=(write_fd,), stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, env=dict(os.environ, OMP_NUM_THREADS='1',
                OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1'))
        os.close(write_fd); write_fd = None
        try: code = process.wait(timeout=80.)
        except BaseException:
            process.terminate()
            try: process.wait(timeout=3.)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=3.)
            raise
        raw = os.read(read_fd, 65537)
        if not raw or len(raw) > 65536: raise ProbeRefused('owned_probe_slot_failed')
        value = json.loads(raw)
        if code != 0 or value.get('status') != 'PASS':
            raise ProbeRefused(value.get('error_code', 'owned_probe_slot_failed'))
        return value['result']
    finally:
        os.close(read_fd)
        if write_fd is not None: os.close(write_fd)


def summarize(rows):
    if [row['threads'] for row in rows] != [3, 4, 4, 3]: raise ValueError('abba_sequence_required')
    if len({row['transcript_sha256'] for row in rows}) != 1 or not all(row['warmup_same_transcript'] for row in rows):
        raise ProbeRefused('public_transcript_changed')
    old = statistics.median(row['asr_ms'] for row in rows if row['threads'] == 3)
    new = statistics.median(row['asr_ms'] for row in rows if row['threads'] == 4)
    return dict(threads3_median_ms=round(old, 2), threads4_median_ms=round(new, 2),
        improvement_ms=round(old-new, 2), improvement_percent=round((old-new)/old*100, 2),
        same_public_transcript=True, sample_pairs=2, statistical_significance_claimed=False,
        formal_gui_asr_acceptance=False, actual_fps_acceptance=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', default='/home/root/aura-board-business-20261030/production-5259eab11e42af13')
    parser.add_argument('--startup-sha256', default='39b102a4a505db491cf06b90e3a5232bfb656c79cb0a3c221551d76d414a9a0a')
    parser.add_argument('--boot-id', required=True)
    for name in ('ui-pid', 'ui-birth', 'camera-pid', 'camera-birth'):
        parser.add_argument('--'+name, type=int, required=True)
    parser.add_argument('--candidate', default=str(HERE/'after/board/runtime/audio/board_asr.py'))
    parser.add_argument('--candidate-sha256', required=True)
    parser.add_argument('--min-available-mib', type=int, default=512)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--slot-threads', type=int, choices=(3, 4), help=argparse.SUPPRESS)
    parser.add_argument('--result-fd', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.min_available_mib < 256: parser.error('memory margin must be at least256MiB')
    if args.slot_threads is not None:
        try: value = dict(status='PASS', result=slot(args)); code = 0
        except Exception as error:
            value = dict(status='REFUSED', error_code=error_code(error)); code = 1
        os.write(args.result_fd, json.dumps(value, allow_nan=False).encode())
        os.close(args.result_fd)
        return code
    before = metadata(args)
    if sha(Path(args.candidate)) != args.candidate_sha256: raise ProbeRefused('candidate_changed')
    if not args.run:
        print(json.dumps(dict(status='INSPECT_ONLY_NO_MODEL_CONSTRUCTED', before=before,
            sequence=[3, 4, 4, 3], additional_probe_models_at_once=1,
            production_model_also_resident=True, minimum_available_mib=args.min_available_mib)))
        return 0
    rows, failure = [], None
    for threads in (3, 4, 4, 3):
        try: rows.append(run_slot(args, threads))
        except Exception as error:
            failure = error_code(error)
            break
    after = metadata(args, allow_background=True)
    if before['ui'] != after['ui'] or before['camera'] != after['camera']:
        raise ProbeRefused('production_process_identity_changed')
    contaminated = (before['memory'] != after['memory'] or not after['model_idle']
                    or any(row['background_changed'] for row in rows))
    comparison = dict(gain_claim_allowed=False)
    status = 'CONTAMINATED_NO_GAIN_CLAIM' if contaminated else 'INCOMPLETE_NO_GAIN_CLAIM'
    if len(rows) == 4 and not contaminated:
        try:
            comparison = summarize(rows)
            status = 'PUBLIC_ASR_ABBA_COMPLETE_NOT_PRODUCTION_ACCEPTANCE'
        except Exception as error: failure = error_code(error)
    print(json.dumps(dict(status=status, background_changed=contaminated, failure_code=failure,
        sequence=[3, 4, 4, 3], results=rows, comparison=comparison, before=before, after=after,
        production_changed=False, production_model_also_resident=True, additional_probe_models_at_once=1,
        no_private_audio=True, microphone_or_player_opened=False, affinity_or_priority_changed=False,
        limitation='No visibility into a background operation that starts and ends between metadata samples; ASR is in a separate process, not the GUI owner.')))
    return 0 if len(rows) == 4 and failure is None else 1


if __name__ == '__main__':
    try: raise SystemExit(main())
    except Exception as error:
        print(json.dumps(dict(status='REFUSED', error_code=error_code(error), production_changed=False)))
        raise SystemExit(1)
