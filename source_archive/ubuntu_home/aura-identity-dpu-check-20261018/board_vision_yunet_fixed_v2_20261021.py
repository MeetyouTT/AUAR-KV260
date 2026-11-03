import sys
sys.argv=['board_fixed_benchmark.py', '/home/root/aura-dpu-vision-20261021/staging/3f10273827d88501/bundle.tar.gz', '--sha256', '3f10273827d88501364225b212108fd2353c547105914bf5301bfa608dbc6dfc', '--boot', '215c4292-ce84-4828-9827-83c32ba66564']
RUNTIME_OVERRIDE='"""Pinned candidate runners; caller supplies the single DPU owner and scheduler.\n\nNo camera, network, service control, identity database or FPGA loading here.\nThe four YuNet heads are matched by geometry, never VART\'s output ordering.\n"""\nimport hashlib\nimport json\nfrom pathlib import Path\nimport time\nimport numpy as np\n\nFINGERPRINT = \'0x101000056010407\'\n\n\ndef encode(values, fix_point):\n    values = np.asarray(values, dtype=np.float32)\n    if not np.isfinite(values).all():\n        raise ValueError(\'Non-finite DPU input\')\n    return np.ascontiguousarray(np.clip(np.floor(values * (2. ** fix_point) + .5), -128, 127).astype(np.int8))\n\n\ndef tensor_meta(t):\n    return {\'name\': t.name, \'dims\': list(t.dims), \'dtype\': str(t.dtype),\n            \'fix_point\': t.get_attr(\'fix_point\') if t.has_attr(\'fix_point\') else None}\n\n\nclass PinnedRunner:\n    def __init__(self, model_path, manifest_path, owner):\n        # Production should pass its DpuYoloX instance; a fixed-input bench can\n        # supply an equivalent owner holding the SAME project lock in this PID.\n        if owner.fingerprint != FINGERPRINT or owner.ownership is None:\n            raise RuntimeError(\'An active matching DPU owner is required\')\n        owner.ownership.fileno()\n        self.owner = owner\n        path = Path(model_path)\n        manifest = json.loads(Path(manifest_path).read_text())\n        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest[\'sha256\']:\n            raise ValueError(\'Candidate xmodel SHA256 mismatch\')\n        expected = [s for s in manifest[\'partitions\'] if s[\'device\'] == \'DPU\']\n        if len(expected) != 1 or expected[0][\'fingerprint\'] != FINGERPRINT:\n            raise ValueError(\'Candidate manifest DPU mismatch\')\n        import xir\n        import vart\n        self.graph = xir.Graph.deserialize(str(path))\n        subs = [s for s in self.graph.get_root_subgraph().toposort_child_subgraph()\n                if s.has_attr(\'device\') and s.get_attr(\'device\') == \'DPU\']\n        if len(subs) != 1 or hex(int(subs[0].get_attr(\'dpu_fingerprint\'))) != FINGERPRINT:\n            raise ValueError(\'Compiled DPU fingerprint mismatch\')\n        # XIR exposes an unordered tensor set. VART\'s port order is the ABI for\n        # execute_async; using XIR order can overrun a smaller output buffer.\n        self.runner = vart.Runner.create_runner(subs[0], \'run\')\n        self.inputs = list(self.runner.get_input_tensors())\n        self.outputs = list(self.runner.get_output_tensors())\n        if ({t.name: tensor_meta(t) for t in self.inputs} != {t[\'name\']: t for t in expected[0][\'inputs\']} or\n                {t.name: tensor_meta(t) for t in self.outputs} != {t[\'name\']: t for t in expected[0][\'outputs\']}):\n            raise ValueError(\'Compiled tensor interface differs from manifest\')\n        if len(self.inputs) != 1 or any(str(t.dtype) != \'xint8\' for t in self.inputs + self.outputs):\n            raise ValueError(\'Expected INT8 tensors and exactly one input\')\n        self.input_fix = self.inputs[0].get_attr(\'fix_point\')\n        self.last_ms = None\n\n    def execute(self, normalized_nhwc):\n        if self.runner is None:\n            raise RuntimeError(\'DPU runner is closed\')\n        self.owner.ownership.fileno()\n        source = encode(normalized_nhwc, self.input_fix)\n        if list(source.shape) != list(self.inputs[0].dims):\n            raise ValueError(\'DPU input shape mismatch\')\n        outputs = [np.empty(tuple(t.dims), dtype=np.int8) for t in self.outputs]\n        started = time.monotonic()\n        job = self.runner.execute_async([source], outputs)\n        status = self.runner.wait(job)\n        self.last_ms = (time.monotonic() - started) * 1000\n        if status != 0:\n            raise RuntimeError(\'VART execution failed: \' + str(status))\n        return {t.name: a.astype(np.float32) / (2. ** t.get_attr(\'fix_point\'))\n                for t, a in zip(self.outputs, outputs)}\n\n    def close(self):\n        self.runner = self.graph = None\n\n\ndef yunet_outputs(values):\n    shapes = {(40, 40, 51), (20, 20, 34), (10, 10, 34), (5, 5, 51)}\n    by_shape = {tuple(x.shape[1:]): x for x in values.values()}\n    if len(values) != 4 or set(by_shape) != shapes:\n        raise ValueError(\'YuNet must have four unique 320px output heads\')\n    raw = np.concatenate([by_shape[s].reshape(1, -1) for s in sorted(shapes, reverse=True)], axis=1).reshape(-1, 17)\n    logits = raw[:, 14:16]\n    e = np.exp(logits - logits.max(axis=1, keepdims=True))\n    return raw[:, :14].copy(), e / e.sum(axis=1, keepdims=True), raw[:, 16:17].copy()\n\n\nclass YuNetNetwork:\n    def __init__(self, runner, execute=None):\n        self.runner = runner\n        # The camera integration supplies a scheduling callback. The isolated\n        # benchmark calls sequentially under its exclusive process owner.\n        self.execute = execute or runner.execute\n\n    def setInput(self, nchw_bgr):\n        self.source = np.ascontiguousarray(nchw_bgr.transpose(0, 2, 3, 1) / 256.)\n\n    def forward(self, names):\n        if names != [\'loc\', \'conf\', \'iou\']:\n            raise ValueError(\'Unsupported YuNet CPU outputs\')\n        result = self.execute(self.source)\n        if result is None:\n            # A skipped scheduling slot must not look like "no face" and break\n            # a live identity binding. Integration must discard this packet.\n            raise SlotUnavailable(\'Face detection skipped for a primary DPU deadline\')\n        return yunet_outputs(result)\n\n\nclass SlotUnavailable(RuntimeError):\n    pass\n\n\ndef make_yunet(reference_model, runner, *, threshold=.9, execute=None):\n    from board.vision.reference_faces import YuNetCompat\n    result = YuNetCompat(reference_model, score_threshold=threshold, input_size=320)\n    result.net = YuNetNetwork(runner, execute)\n    return result\n\n\ndef sface_feature(crop, runner, execute=None):\n    if not isinstance(crop, np.ndarray) or crop.dtype != np.uint8 or crop.shape != (112, 112, 3):\n        raise ValueError(\'SFace needs an aligned uint8 112x112 BGR crop\')\n    source = (crop[:, :, ::-1].astype(np.float32)[None] - 127.5) / 128.\n    result = (execute or runner.execute)(source)\n    if result is None:\n        return None\n    if len(result) != 1:\n        raise ValueError(\'SFace must have one output\')\n    feature = next(iter(result.values())).reshape(-1)\n    if feature.shape != (128,) or not np.isfinite(feature).all() or np.linalg.norm(feature) <= 1e-8:\n        raise ValueError(\'Invalid SFace INT8 feature\')\n    return feature\n'
"""Bounded fixed-input board test, with independent timed camera restoration."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import time
import urllib.request

CORE = r'''
import ctypes,faulthandler,fcntl,hashlib,json,sys,time
from pathlib import Path
from types import SimpleNamespace
import cv2,numpy as np
faulthandler.enable()
print('milestone: imports ready',flush=True)
root=Path(sys.argv[1]);camera_config=json.loads(Path(sys.argv[2]).read_text())
runtime=Path(sys.argv[3]);sys.path[:0]=[str(root),str(runtime)]
from dpu_vision_runtime import PinnedRunner,make_yunet
cv2.setNumThreads(2)
lock=Path('/run/aura-person-dpu.lock').open('a+')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
owner=SimpleNamespace(fingerprint='0x101000056010407',ownership=lock)
runner=PinnedRunner(root/'yunet_public_int8.xmodel',root/'manifest.json',owner)
print('milestone: VART runner ready; ports='+str([(t.name,list(t.dims)) for t in runner.outputs]),flush=True)
vectors=np.load(str(root/'vectors.npz'),allow_pickle=False)
agreement=[]
for i,image in enumerate(vectors['images_bgr']):
 values=runner.execute(image.astype(np.float32)[None]/256.)
 heads=[]
 for tensor in runner.outputs:
  actual=np.rint(values[tensor.name]*2.**tensor.get_attr('fix_point')).astype(np.int16)
  expected=vectors['sample_%d_%s'%(i,tensor.name)].astype(np.int16)
  diff=np.abs(actual-expected)
  heads.append({'shape':list(actual.shape),'max_integer_difference':int(diff.max()),
                'different_elements':int(np.count_nonzero(diff)),'elements':int(diff.size)})
 agreement.append({'sample':i,'submit_wait_ms':runner.last_ms,'heads':heads,
                   'host_agreement_within_one_lsb':all(x['max_integer_difference']<=1 for x in heads)})
 print('milestone: hardware sample '+str(i)+' complete',flush=True)
from board.vision.reference_faces import YuNetCompat
identity_config=json.loads(Path(camera_config['identity']['config']).read_text())
face_model=Path(identity_config['face_model'])
if not face_model.is_absolute():face_model=runtime/face_model
reference=YuNetCompat(str(face_model),score_threshold=.9,input_size=320)
candidate=make_yunet(str(face_model),runner,threshold=.9)
def summary(values):
 a=np.asarray(values);return {'samples':len(a),'median_ms':float(np.median(a)),
  'p95_ms':float(np.percentile(a,95)),'max_ms':float(a.max())}
latencies={};cpu_counts=[];dpu_counts=[]
for label,detector,counts in [('cpu_fp32',reference,cpu_counts),('dpu_int8_with_cpu_postprocess',candidate,dpu_counts)]:
 detector.detect(vectors['images_bgr'][0]);elapsed=[]
 for i in range(40):
  before=time.monotonic();faces=detector.detect(vectors['images_bgr'][i%3]);elapsed.append((time.monotonic()-before)*1000);counts.append(len(faces))
 latencies[label]=summary(elapsed)
config=camera_config['yolo']
for key,sha_key in [('model','model_sha256'),('native_library','native_sha256'),('reference_image','reference_sha256')]:
 assert hashlib.sha256(Path(config[key]).read_bytes()).hexdigest()==config[sha_key]
lib=ctypes.CDLL(config['native_library'])
lib.aura_yolox_create.argtypes=[ctypes.c_char_p];lib.aura_yolox_create.restype=ctypes.c_void_p
lib.aura_yolox_error.restype=ctypes.c_char_p
lib.aura_yolox_detect.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.POINTER(ctypes.c_int)]
lib.aura_yolox_detect.restype=ctypes.c_int;lib.aura_yolox_destroy.argtypes=[ctypes.c_void_p]
handle=lib.aura_yolox_create(config['model'].encode());assert handle,lib.aura_yolox_error()
image=np.ascontiguousarray(cv2.imread(config['reference_image']));h,w=image.shape[:2];boxes=np.zeros((32,6),np.float32)
def yolo():
 count=ctypes.c_int();before=time.monotonic()
 status=lib.aura_yolox_detect(handle,image.ctypes.data,w,h,image.strides[0],boxes.ctypes.data,32,0,ctypes.byref(count))
 assert status==0 and count.value>0,lib.aura_yolox_error()
 return (time.monotonic()-before)*1000
mixed=[]
try:
 yolo()
 for label,slots,faces_enabled in [('yolo_only',20,False),('yolo_yunet',40,True)]:
  start=time.monotonic();primary=[];secondary=[];overruns=0
  for i in range(slots):
   deadline=start+i*.1;time.sleep(max(0,deadline-time.monotonic()))
   primary.append(yolo())
   if faces_enabled and i%2==0:
    before=time.monotonic();candidate.detect(vectors['images_bgr'][0]);secondary.append((time.monotonic()-before)*1000)
   overruns+=int(time.monotonic()>deadline+.1)
  mixed.append({'mode':label,'scheduled_yolo_hz':10,'scheduled_yunet_hz':5 if faces_enabled else 0,
    'yolo_calls':len(primary),'yunet_calls':len(secondary),'yolo':summary(primary),
    'yunet':summary(secondary) if secondary else None,'period_overruns':overruns})
finally:
 lib.aura_yolox_destroy(handle);runner.close();lock.close()
print(json.dumps({'scope':'FIXED_PUBLIC_SYNTHETIC_INPUT_NOT_LIVE_CAMERA_OR_FIELD_ACCURACY',
 'agreement':agreement,'all_host_quantized_agreement':all(x['host_agreement_within_one_lsb'] for x in agreement),
 'latencies':latencies,'same_face_count_calls':sum(a==b for a,b in zip(cpu_counts,dpu_counts)),
 'compared_detection_calls':len(cpu_counts),'mixed':mixed}),flush=True)
'''


def get(port, path):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:%d%s' % (port, path), timeout=2) as response:
        return json.load(response)


def service(*args):
    return subprocess.run(['systemctl', *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          check=True, timeout=20).stdout.decode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--boot', required=True)
    args = parser.parse_args()
    assert os.uname().machine == 'aarch64'
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == args.boot
    assert str(args.bundle).startswith('/home/root/aura-dpu-vision-20261021/staging/')
    assert hashlib.sha256(args.bundle.read_bytes()).hexdigest() == args.sha256
    override = globals().get('RUNTIME_OVERRIDE')
    override_sha = hashlib.sha256(override.encode()).hexdigest() if override else None
    root = args.bundle.parent / ('kit-' + override_sha[:16] if override else 'kit')
    root.mkdir(exist_ok=True)
    with tarfile.open(args.bundle, 'r:gz') as archive:
        meta = json.load(archive.extractfile('bundle-manifest.json'))
        assert set(archive.getnames()) == set(meta) | {'bundle-manifest.json'}
        for member in archive:
            if member.name == 'bundle-manifest.json':
                continue
            assert member.isfile() and Path(member.name).name == member.name
            data = archive.extractfile(member).read()
            assert len(data) == meta[member.name]['bytes']
            assert hashlib.sha256(data).hexdigest() == meta[member.name]['sha256']
            if member.name == 'dpu_vision_runtime.py' and override:
                data = override.encode()
                compile(data, member.name, 'exec')
            target = root / member.name
            assert not target.is_symlink()
            if target.exists():
                assert target.read_bytes() == data
            else:
                with target.open('xb') as out:
                    out.write(data)
    ui = get(8783, '/api/state')
    assert ui['phase'] == 'IDLE' and not ui['playing'] and not ui['paused'], 'Wait for an idle conversation'
    assert ui.get('local_recording', {}).get('state') != 'RECORDING'
    assert not ui.get('local_transcription', {}).get('service', {}).get('pending')
    before = get(8790, '/health')
    assert not before['camera_error'] and not before['detector_error']
    pid = before['pid']
    arguments = (Path('/proc') / str(pid) / 'cmdline').read_bytes().split(b'\0')
    runtime = next(Path(x.decode()).parent.parent for x in arguments if x.endswith(b'/board_camera_motion.py'))
    config = Path(arguments[arguments.index(b'--config') + 1].decode())
    camera_config = json.loads(config.read_text())
    identity_config = json.loads(Path(camera_config['identity']['config']).read_text())
    face_model = Path(identity_config['face_model'])
    if not face_model.is_absolute():
        face_model = runtime / face_model
    assert hashlib.sha256(face_model.read_bytes()).hexdigest() == '50ef07f702a31741ca46a4c0d947773b64143b9362780237bf0d427d6c79bab7'
    for path_key, sha_key in [('model', 'model_sha256'), ('native_library', 'native_sha256'), ('reference_image', 'reference_sha256')]:
        assert hashlib.sha256(Path(camera_config['yolo'][path_key]).read_bytes()).hexdigest() == camera_config['yolo'][sha_key]
    files = [Path('/etc/systemd/system/aura-camera-ui.service'),
             Path('/etc/systemd/system/aura-avatar-ui.service'), config]
    protected = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    ui_pid = service('show', 'aura-avatar-ui.service', '-p', 'MainPID', '--value').strip()
    timer = 'aura-dpu-vision-restore-' + str(os.getpid())
    subprocess.run(['systemd-run', '--unit=' + timer, '--on-active=80s',
                    '/bin/systemctl', 'start', 'aura-camera-ui.service'],
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True, timeout=10)
    keys = ('pid', 'service_epoch', 'detected_frames', 'observation_age_ms', 'camera_error', 'detector_error')
    report = {'scope': 'CONTROLLED_FIXED_INPUT_BENCHMARK_WITH_CAMERA_RESTORATION',
              'boot_id': args.boot, 'camera_before': {k: before.get(k) for k in keys},
              'production_config_changed': False, 'restore_timer': timer,
              'runtime_override_sha256': override_sha}
    started = time.monotonic()
    try:
        service('stop', 'aura-camera-ui.service')
        p = subprocess.run(['python3', '-u', '-B', '-c', CORE, str(root), str(config), str(runtime)],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=40)
        report['core_exit_code'] = p.returncode
        lines = p.stdout.decode(errors='replace').splitlines()
        for line in reversed(lines):
            if line.startswith('{'):
                report['core'] = json.loads(line)
                break
        if p.returncode or 'core' not in report:
            report['core_error'] = '\n'.join(lines[-12:])[-2000:]
    except Exception as exc:
        report['test_error'] = str(exc)
    finally:
        service('start', '--no-block', 'aura-camera-ui.service')
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            try:
                state = get(8790, '/health')
                if state['detected_frames'] > 2 and not state['camera_error'] and not state['detector_error'] and state['observation_age_ms'] is not None and state['observation_age_ms'] < 750:
                    report['camera_after'] = {k: state.get(k) for k in keys}
                    report['camera_restored'] = True
                    break
            except Exception:
                pass
            time.sleep(.4)
        if report.get('camera_restored'):
            service('stop', timer + '.timer')
    report['elapsed_s'] = time.monotonic() - started
    report['ui_pid_preserved'] = ui_pid == service('show', 'aura-avatar-ui.service', '-p', 'MainPID', '--value').strip()
    report['protected_configuration_unchanged'] = all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == sha for p, sha in protected.items())
    report['boot_preserved'] = Path('/proc/sys/kernel/random/boot_id').read_text().strip() == args.boot
    report['passed'] = bool(report.get('core', {}).get('all_host_quantized_agreement') and report.get('camera_restored')
                            and report['ui_pid_preserved'] and report['protected_configuration_unchanged'] and report['boot_preserved'])
    (root / 'board-result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
