"""Public CPU-only component screen. Does not start the camera service."""
import argparse
import ast
import copy
import gc
import hashlib
import importlib.abc
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
SOURCE_MANIFEST_SHA = '2a35303cb6d50b488a6d4dc22f4609050b0f220ac0223b47f31829ac590fec12'
PIXELS = 640 * 480 * 3
MODES = ('no_get', 'low_get', 'legacy_get')
VERSIONS = {'A': 'before', 'B': 'after'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_sources():
    manifest = HERE / 'PUBLIC_SOURCES.json'
    if digest(manifest) != SOURCE_MANIFEST_SHA:
        raise ValueError('Public source manifest changed')
    rows = json.loads(manifest.read_text('utf-8'))
    root = (HERE / 'public_sources').resolve()
    for name, row in rows.items():
        path = root / name
        if path.is_symlink() or root not in path.resolve().parents or digest(path) != row['sha256']:
            raise ValueError('Public source differs: ' + name)
    return rows


def wants_get(frame_id, mode, logical_fps):
    if mode == 'no_get':
        return False
    interval = 2.0 if mode == 'low_get' else .6
    stride = max(1, math.ceil(logical_fps * interval))
    return (frame_id - 1) % stride == 0


def public_directory():
    root = Path('/dev/shm')
    if not root.is_dir() or root.resolve() != root:
        raise RuntimeError('A real /dev/shm directory is required; no storage fallback')
    path = Path(tempfile.mkdtemp(prefix='aura-jpeg-public-', dir=str(root)))
    if path.is_symlink() or path.parent.resolve() != root:
        raise RuntimeError('Unexpected public RAM directory')
    os.chmod(path, 0o700)
    return path


class CpuOnlyImports(importlib.abc.MetaPathFinder):
    PREFIXES = ('gi', 'xir', 'vart', 'torch', 'onnxruntime',
                'board.vision.native_startup', 'board.vision.native_binding',
                'board.vision.native_runtime', 'board.vision.dpu_', 'board.identity.camera_faces')

    def find_spec(self, fullname, path, target=None):
        if any(fullname == name or fullname.startswith(name + '.') or
               (name.endswith('_') and fullname.startswith(name)) for name in self.PREFIXES):
            raise RuntimeError('Hardware/model import forbidden in public screen: ' + fullname)
        return None


def cpu_only_io(event, args):
    if event in ('socket.connect', 'socket.bind'):
        raise RuntimeError('Public component screen does not open a network connection')
    if event == 'sqlite3.connect':
        raise RuntimeError('Public component screen does not open a database')
    if event != 'open' or not args or not isinstance(args[0], (str, bytes)):
        return
    path = os.fsdecode(args[0])
    forbidden = ('/dev/video', '/dev/uio', '/dev/dri', '/run/aura-camera-ui-',
                 '/home/root/.local/share/aura', '/home/root/.local/share/aura-board-business')
    if path.startswith(forbidden) or path.lower().endswith(('.xmodel', '.onnx', '.gguf', '.pt')):
        raise RuntimeError('Private/device/model file forbidden in public screen')


def load_camera(version):
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(HERE / 'public_sources/support'))
    import board.vision  # Bind the package before the source inserts its own root.
    path = HERE / 'public_sources' / version / 'board/vision/ui_camera_service.py'
    name = 'public_camera_' + version
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def producer(module):
    """Use the original producer body, excluding capture wait and error wrapper."""
    tree = ast.parse(Path(module.__file__).read_text('utf-8'))
    run = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'run')
    preview = next(node for node in ast.walk(run) if isinstance(node, ast.FunctionDef) and node.name == 'preview')
    body = next(node.body for node in ast.walk(preview) if isinstance(node, ast.Try))
    arguments = ast.arguments(posonlyargs=[], args=[ast.arg(arg=name) for name in
        ('state', 'raw', 'cv2', 'source', 'fid', 'stamp')], vararg=None, kwonlyargs=[],
        kw_defaults=[], kwarg=None, defaults=[])
    function = ast.FunctionDef(name='render_once', args=arguments, body=copy.deepcopy(body), decorator_list=[])
    block = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    namespace = dict(vars(module))
    exec(compile(block, module.__file__, 'exec'), namespace)
    return namespace['render_once']


def http_get(handler_type, state, frame_id):
    """Exact handler and headers, with an in-memory response stream and no TCP."""
    handler = handler_type.__new__(handler_type)
    handler.path = '/v1/ui/preview.jpg?camera_epoch=' + state.camera_epoch + '&frame_id=' + str(frame_id)
    handler.wfile = io.BytesIO()
    response = {'headers': {}}
    handler.send_response = lambda code: response.update(status=code)
    handler.send_header = lambda name, value: response['headers'].update({name: value})
    handler.end_headers = lambda: None
    handler.do_GET()
    response['body'] = handler.wfile.getvalue()
    return response


def timed(function, *args):
    wall, cpu = time.perf_counter_ns(), time.process_time_ns()
    value = function(*args)
    return value, (time.perf_counter_ns() - wall) / 1e6, (time.process_time_ns() - cpu) / 1e6


def rss_bytes():
    resident = int(Path('/proc/self/statm').read_text().split()[1])
    return resident * os.sysconf('SC_PAGE_SIZE')


def describe_samples(values):
    if not values:
        return {'count': 0, 'total_ms': 0.0}
    ordered = sorted(values)
    return {'count': len(values), 'total_ms': sum(values), 'mean_ms': statistics.mean(values),
            'p50_ms': statistics.median(values), 'p95_ms': ordered[math.ceil(.95 * len(ordered)) - 1],
            'max_ms': max(values)}


def pattern(base, frame_id):
    value = base.copy()
    left = (frame_id * 13) % 560
    value[160:240, left:left + 80] = ((frame_id * 7) % 256, 220, 45)
    return value


def check_response(response, state, frame_id, stamp, validate_jpeg):
    headers, jpeg = response['headers'], response['body']
    if response['status'] != 200 or headers != {
        'Content-Type': 'image/jpeg', 'Content-Length': str(len(jpeg)), 'Cache-Control': 'no-store',
        'X-Aura-Boot-Id': state.boot, 'X-Aura-Camera-Epoch': state.camera_epoch, 'X-Aura-Frame-Id': str(frame_id)}:
        raise AssertionError('Same-frame JPEG HTTP contract failed')
    if len(jpeg) > 256 * 1024:
        raise AssertionError('JPEG exceeded producer limit')
    frame = dict(board_boot_id=state.boot, camera_epoch=state.camera_epoch, frame_id=frame_id,
                 captured_mono_ms=stamp, observed_mono_ms=int(time.monotonic() * 1000),
                 sha256=hashlib.sha256(jpeg).hexdigest())
    validate_jpeg(frame, jpeg)
    return frame['sha256']


def phase(module, cv2, np, directory, frames, mode, logical_fps, *, warmup=False):
    from board.interaction.ui_contract import validate_snapshot
    from board.vision.local_preview import RawFrameStore, RawFrameReader
    from common.visual_question import validate_jpeg
    info = {'role': 'DPU_YOLOX_PERSON_PREVIEW', 'count_kind': 'people',
            'detail': 'PUBLIC SYNTHETIC BOX FIXTURE', 'target_label': 'person'}
    state = module.CameraState('public-synthetic-boot', 'public-synthetic-service', detector_info=info)
    state.raw_preview = True
    owner = dict(board_boot_id=state.boot, service_epoch=state.epoch, camera_epoch=state.camera_epoch)
    raw = RawFrameStore(owner, str(directory))
    reader = RawFrameReader(owner, str(directory))
    render = producer(module)
    handler_type = module.handler_for(state)
    x, y = np.indices((480, 640), dtype=np.uint16)
    base = np.stack(((x + y) % 256, (x * 3) % 256, (y * 2) % 256), axis=2).astype(np.uint8)
    times = {name: [] for name in ('producer_wall', 'producer_cpu', 'first_get_wall', 'first_get_cpu',
                                   'cache_get_wall', 'cache_get_cpu', 'encode_wall', 'encode_cpu')}
    original_encode = cv2.imencode
    encode_calls = 0

    def encode(*args, **kwargs):
        nonlocal encode_calls
        encode_calls += 1
        wall, cpu = time.perf_counter_ns(), time.process_time_ns()
        try:
            return original_encode(*args, **kwargs)
        finally:
            times['encode_wall'].append((time.perf_counter_ns() - wall) / 1e6)
            times['encode_cpu'].append((time.process_time_ns() - cpu) / 1e6)

    cv2.imencode = encode
    digests, max_entries, max_payload, requests = [], 0, 0, 0
    rss_before, rss_peak = rss_bytes(), 0
    try:
        for frame_id in range(1, frames + 1):
            source = pattern(base, frame_id)
            stamp = int(time.monotonic() * 1000)
            state.captured(stamp)
            state.observed(frame_id, stamp, {'target_id': 1, 'tracks': [
                {'track_id': 1, 'generation': 1, 'visible': True, 'confirmed': True,
                 'box': (40, 60, 120, 180), 'score': .85}]}, 1.)
            _, wall, cpu = timed(render, state, raw, cv2, source, frame_id, stamp)
            times['producer_wall'].append(wall)
            times['producer_cpu'].append(cpu)
            jpeg_hash = None
            if warmup or wants_get(frame_id, mode, logical_fps):
                response, wall, cpu = timed(http_get, handler_type, state, frame_id)
                times['first_get_wall'].append(wall)
                times['first_get_cpu'].append(cpu)
                jpeg_hash = check_response(response, state, frame_id, stamp, validate_jpeg)
                repeated, wall, cpu = timed(http_get, handler_type, state, frame_id)
                times['cache_get_wall'].append(wall)
                times['cache_get_cpu'].append(cpu)
                if check_response(repeated, state, frame_id, stamp, validate_jpeg) != jpeg_hash:
                    raise AssertionError('Cached JPEG changed')
                requests += 1
            # Validation happens outside measured producer/request durations.
            value = validate_snapshot(state.snapshot(), state.boot, int(time.monotonic() * 1000))
            if value.get('preview') != dict(camera_epoch=state.camera_epoch, frame_id=frame_id, captured_mono_ms=stamp):
                raise AssertionError('Raw display preview reference missing or changed')
            header, pixels = reader.read(int(time.monotonic() * 1000))
            if header['frame_id'] != frame_id or header['captured_mono_ms'] != stamp:
                raise AssertionError('Raw preview source changed')
            entry = state.frames[frame_id]
            if isinstance(entry, tuple):
                jpeg_hash = hashlib.sha256(entry[1]).hexdigest()
                payload_bytes = sum(len(item[1]) for item in state.frames.values())
            else:
                if entry.pixels is not None and entry.pixels != pixels:
                    raise AssertionError('Deferred image differs from published raw pixels')
                payload_bytes = sum(len(item.pixels or b'') + len(item.jpeg or b'') for item in state.frames.values())
            max_entries = max(max_entries, len(state.frames))
            max_payload = max(max_payload, payload_bytes)
            if len(state.frames) > 8 or payload_bytes > 8 * PIXELS:
                raise AssertionError('Frame cache exceeded fixed bound')
            digests.append({'frame_id': frame_id, 'raw_sha256': hashlib.sha256(pixels).hexdigest(),
                            'jpeg_sha256': jpeg_hash})
            rss_peak = max(rss_peak, rss_bytes())
    finally:
        cv2.imencode = original_encode
        raw.close()
    expected = frames if module.__name__.endswith('before') else requests
    if encode_calls != expected:
        raise AssertionError('Unexpected number of JPEG encodes')
    primary_cpu = sum(times['producer_cpu']) + sum(times['first_get_cpu'])
    return {'frames': frames, 'first_get_requests': requests, 'cache_probe_requests': requests,
            'encode_calls': encode_calls, 'expected_encode_calls': expected,
            'timings': {name: describe_samples(values) for name, values in times.items()},
            'primary_component_cpu_ms': primary_cpu, 'primary_cpu_ms_per_frame': primary_cpu / frames,
            'cache_max_entries': max_entries, 'cache_max_payload_bytes': max_payload,
            'rss_before_bytes': rss_before, 'rss_observed_peak_bytes': rss_peak,
            'rss_observed_delta_bytes': rss_peak - rss_before, 'frame_digests': digests}


def child(args):
    checked_sources()
    sys.meta_path.insert(0, CpuOnlyImports())
    sys.addaudithook(cpu_only_io)
    os.environ.update(AURA_PIPELINE_METRICS='0', AURA_DPU_DIAGNOSTICS='0', AURA_THREAD_SCHED_DIAGNOSTICS='')
    import cv2
    import numpy as np
    cv2.setNumThreads(args.opencv_threads)
    module = load_camera(args.version)
    directory = public_directory()
    report = {'version': args.version, 'mode': args.mode, 'public_synthetic': True,
              'opencv_version': cv2.__version__, 'opencv_threads': cv2.getNumThreads(),
              'numpy_version': np.__version__, 'temporary_directory': str(directory)}
    try:
        phase(module, cv2, np, directory, 5, args.mode, args.logical_capture_fps, warmup=True)
        gc.collect()
        report.update(phase(module, cv2, np, directory, args.frames, args.mode, args.logical_capture_fps))
        report['status'] = 'PASS'
    except Exception as exc:
        report.update(status='FAIL', error_type=type(exc).__name__, error=str(exc)[:500])
    finally:
        # Only the private directory created above is removed, and only if empty.
        # RawFrameStore.close removes its own inode. Unknown leftovers are retained.
        if directory.is_symlink() or directory.parent.resolve() != Path('/dev/shm'):
            raise RuntimeError('Refuse cleanup of an unexpected directory')
        try:
            directory.rmdir()
        except OSError:
            report['temporary_directory_removed'] = False
            report['temporary_leftovers'] = [path.name for path in directory.iterdir()]
            report['status'] = 'FAIL'
        else:
            report['temporary_directory_removed'] = True
    print(json.dumps(report, ensure_ascii=True, separators=(',', ':')))
    return 0 if report['status'] == 'PASS' else 1


def compare(arms, frames):
    reference = next(arm for arm in arms if arm['version'] == 'before')['frame_digests']
    for arm in arms:
        if len(arm['frame_digests']) != frames:
            raise AssertionError('Incomplete public frame sequence')
        for actual, expected in zip(arm['frame_digests'], reference):
            if actual['frame_id'] != expected['frame_id'] or actual['raw_sha256'] != expected['raw_sha256']:
                raise AssertionError('Public overlaid raw frame differs across arms')
            if actual['jpeg_sha256'] is not None and actual['jpeg_sha256'] != expected['jpeg_sha256']:
                raise AssertionError('Public same-frame JPEG differs across arms')
    summary = {}
    for mode in MODES:
        before = [arm['primary_cpu_ms_per_frame'] for arm in arms if arm['mode'] == mode and arm['version'] == 'before']
        after = [arm['primary_cpu_ms_per_frame'] for arm in arms if arm['mode'] == mode and arm['version'] == 'after']
        old, new = statistics.mean(before), statistics.mean(after)
        summary[mode] = {'before_cpu_ms_per_frame': old, 'after_cpu_ms_per_frame': new,
                         'component_cpu_reduction_percent': (old - new) * 100 / old if old else None}
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=int, default=60)
    parser.add_argument('--logical-capture-fps', type=float, default=15)
    parser.add_argument('--opencv-threads', type=int, default=1)
    parser.add_argument('--order', choices=('AB', 'ABBA'), default='AB')
    parser.add_argument('--describe', action='store_true')
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--version', choices=('before', 'after'), help=argparse.SUPPRESS)
    parser.add_argument('--mode', choices=MODES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 50 <= args.frames <= 100 or not 1 <= args.logical_capture_fps <= 60 or not 1 <= args.opencv_threads <= 4:
        parser.error('Use 50..100 frames, 1..60 logical fps and 1..4 OpenCV threads')
    sources = checked_sources()
    plan = {'scope': 'public CPU producer/raw-file/request-handler component screen',
            'frames_per_arm': args.frames, 'order_per_mode': args.order,
            'total_measured_frames': args.frames * len(args.order) * len(MODES),
            'logical_capture_fps': args.logical_capture_fps,
            'get_intervals_seconds': {'no_get': None, 'low_get': 2.0, 'legacy_get': .6},
            'expected_after_encode_calls_per_arm': {mode: sum(wants_get(fid, mode, args.logical_capture_fps)
                for fid in range(1, args.frames + 1)) for mode in MODES},
            'source_manifest_sha256': SOURCE_MANIFEST_SHA, 'source_files': len(sources)}
    if args.describe:
        print(json.dumps(plan, indent=2))
        return 0
    if sys.platform != 'linux' or platform.machine().lower() not in ('aarch64', 'arm64'):
        raise RuntimeError('Execution is restricted to the root-scheduled ARM Linux public screen')
    if args.child:
        if args.version is None or args.mode is None:
            parser.error('Child requires a fixed version and mode')
        return child(args)
    arms = []
    for mode in MODES:
        for letter in args.order:
            command = [sys.executable, '-B', str(Path(__file__).resolve()), '--child', '--mode', mode,
                       '--version', VERSIONS[letter], '--frames', str(args.frames),
                       '--logical-capture-fps', str(args.logical_capture_fps),
                       '--opencv-threads', str(args.opencv_threads)]
            prior_directories = set(Path('/dev/shm').glob('aura-jpeg-public-*'))
            try:
                process = subprocess.run(command, capture_output=True, text=True, timeout=45)
            except subprocess.TimeoutExpired:
                leftovers = sorted(str(path) for path in set(Path('/dev/shm').glob('aura-jpeg-public-*')) - prior_directories)
                print(json.dumps(dict(plan, status='FAIL', completed_arms=arms,
                                      error='Public child exceeded 45 seconds and was terminated',
                                      potential_public_ram_leftovers=leftovers,
                                      cleanup_performed_on_unknown_files=False)))
                return 1
            if process.returncode or process.stderr.strip():
                print(json.dumps(dict(plan, status='FAIL', completed_arms=arms, child_exit=process.returncode,
                                      child_stdout=process.stdout[-2000:], child_stderr=process.stderr[-2000:])))
                return 1
            arm = json.loads(process.stdout)
            if arm.get('status') != 'PASS' or arm.get('temporary_directory_removed') is not True:
                raise RuntimeError('Public child did not finish and clean up')
            arms.append(arm)
    report = dict(plan, status='PASS', arms=arms, comparison=compare(arms, args.frames),
        worker_sha256=digest(Path(__file__)), hardware_camera_opened=False, real_frames_read=False,
        private_database_read=False, model_initialized=False, native_or_dpu_initialized=False,
        limitations=[
            'Fixed public generated patterns and fake observed boxes; no physical capture/detector/identity work.',
            'CPU time covers the extracted original producer body including raw.publish and first request handler.',
            'Pattern generation, hashing, raw-read validation and immediate cache probes are excluded from primary CPU.',
            'In-memory HTTP handlers omit sockets, real request scheduling and network latency.',
            'Logical frame time only determines GET density; frames are processed as fast as possible, without pacing.',
            'Each arm is a fresh CPU-only process with five warmup frames and a private /dev/shm directory.',
            'RSS is observed process residency in isolated arms, not a total board memory measurement.',
            'Component CPU percentages do not establish total camera/board CPU or conversational latency gains.',
            'No production source/config/entry/private pin was changed and the camera service was not restarted.'])
    print(json.dumps(report, ensure_ascii=True, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
