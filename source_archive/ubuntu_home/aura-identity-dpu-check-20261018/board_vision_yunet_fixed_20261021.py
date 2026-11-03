import sys
sys.argv=['board_fixed_benchmark.py', '/home/root/aura-dpu-vision-20261021/staging/3f10273827d88501/bundle.tar.gz', '--sha256', '3f10273827d88501364225b212108fd2353c547105914bf5301bfa608dbc6dfc', '--boot', '215c4292-ce84-4828-9827-83c32ba66564']
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
import ctypes,fcntl,hashlib,json,sys,time
from pathlib import Path
from types import SimpleNamespace
import cv2,numpy as np
root=Path(sys.argv[1]);camera_config=json.loads(Path(sys.argv[2]).read_text())
runtime=Path(sys.argv[3]);sys.path[:0]=[str(root),str(runtime)]
from dpu_vision_runtime import PinnedRunner,make_yunet
cv2.setNumThreads(2)
lock=Path('/run/aura-person-dpu.lock').open('a+')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
owner=SimpleNamespace(fingerprint='0x101000056010407',ownership=lock)
runner=PinnedRunner(root/'yunet_public_int8.xmodel',root/'manifest.json',owner)
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
    root = args.bundle.parent / 'kit'
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
              'production_config_changed': False, 'restore_timer': timer}
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
