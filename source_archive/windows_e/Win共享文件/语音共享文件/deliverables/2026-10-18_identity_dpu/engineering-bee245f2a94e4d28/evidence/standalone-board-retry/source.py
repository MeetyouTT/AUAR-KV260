"""Temporarily release the camera's DPU with finally+timer restoration guards."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

assert os.uname().machine == 'aarch64'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip() == '0353445345333247805558c00401a100'
boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot == '94bbc908-4eb8-4111-9435-db2eb1e5a511'
ROOT = Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/bee245f2a94e4d28')
core = r'''
import hashlib,json,time
from pathlib import Path
import numpy as np
import xir,vart
root=Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/bee245f2a94e4d28')
manifest=json.loads((root/'manifest.json').read_text())
for name,meta in manifest['files'].items():
 data=(root/name).read_bytes();assert len(data)==meta['bytes'] and hashlib.sha256(data).hexdigest()==meta['sha256']
g=xir.Graph.deserialize(str(root/'sface_engineering.xmodel'))
subs=[s for s in g.get_root_subgraph().toposort_child_subgraph() if s.has_attr('device') and s.get_attr('device')=='DPU']
assert len(subs)==1 and subs[0].get_attr('dpu_fingerprint')==int('0x101000056010407',16)
runner=vart.Runner.create_runner(subs[0],'run')
it,ot=runner.get_input_tensors(),runner.get_output_tensors()
assert len(it)==len(ot)==1 and list(it[0].dims)==[1,112,112,3] and list(ot[0].dims)==[1,128]
assert it[0].get_attr('fix_point')==7 and ot[0].get_attr('fix_point')==5
def cosine(a,b):
 a=a.reshape(-1).astype(np.float64);b=b.reshape(-1).astype(np.float64)
 return float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)))
data=np.load(str(root/'hardware-reference.npz'),allow_pickle=False);results=[]
for name in data['names']:
 source=np.ascontiguousarray(data['input_'+str(name)],dtype=np.int8)
 output=np.zeros(tuple(ot[0].dims),dtype=np.int8)
 start=time.monotonic();job=runner.execute_async([source],[output]);status=runner.wait(job)
 elapsed=(time.monotonic()-start)*1000;assert status==0,'VART failed: '+str(status)
 expected=data['quantized_'+str(name)];diff=np.abs(output.reshape(-1).astype(np.int16)-expected.astype(np.int16))
 score=cosine(output,expected)
 results.append({'sample':str(name),'submit_wait_ms':round(elapsed,3),'cosine_to_host_quantized':score,
  'maximum_integer_difference':int(diff.max()),'cosine_to_original_cpu':cosine(output.astype(np.float32)/32.,data['fp32_'+str(name)]),
  'output_sha256':hashlib.sha256(output.tobytes()).hexdigest(),'host_quantized_agreement':bool(diff.max()<=1 or score>=.995)})
print(json.dumps({'results':results,'all_host_quantized_agreement':all(r['host_quantized_agreement'] for r in results)}),flush=True)
'''


def service(*args):
    return subprocess.run(['systemctl', *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20, check=True)


def get(port, route):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:%d%s' % (port, route), timeout=3) as response:
        return json.load(response)


def camera():
    s = get(8790, '/health')
    return {k: s.get(k) for k in ('pid', 'service_epoch', 'detected_frames', 'observation_age_ms', 'camera_error', 'detector_error', 'identity_recognition')}


ui = get(8783, '/api/state')
assert ui['phase'] == 'IDLE' and not ui['playing'] and not ui['paused']
assert ui.get('local_recording', {}).get('state') != 'RECORDING'
assert not ui.get('local_transcription', {}).get('service', {}).get('pending')
before = camera()
assert not before['camera_error'] and not before['detector_error']
files = ['/etc/systemd/system/aura-camera-ui.service', '/etc/systemd/system/aura-avatar-ui.service',
         '/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura/config/board_camera_ui.json']
protected = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files}
ui_pid = service('show', 'aura-avatar-ui.service', '-p', 'MainPID', '--value').stdout.decode().strip()
timer = 'aura-sface-engineering-restore-'+str(os.getpid())
subprocess.run(['systemd-run', '--unit='+timer, '--on-active=70s', '/bin/systemctl', 'start', 'aura-camera-ui.service'],
               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True, timeout=10)
report = {'scope': 'STANDALONE_ENGINEERING_TEST_WITH_CAMERA_TEMPORARILY_STOPPED', 'boot_id': boot,
          'camera_before': before, 'production_configuration_changed': False,
          'real_identity_accuracy_accepted': False, 'unified_dpu_scheduler_tested': False,
          'restore_timer': timer}
started = time.monotonic()
try:
    service('stop', 'aura-camera-ui.service')
    p = subprocess.run(['python3', '-u', '-B', '-c', core], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=25)
    report['core_exit_code'] = p.returncode
    lines = p.stdout.decode(errors='replace').splitlines()
    for line in reversed(lines):
        if line.startswith('{'):
            report['core'] = json.loads(line)
            break
    if p.returncode or 'core' not in report:
        report['core_error'] = '\n'.join(lines[-12:])[-2500:]
except Exception as exc:
    report['test_error'] = type(exc).__name__+': '+str(exc)
finally:
    service('start', '--no-block', 'aura-camera-ui.service')
    deadline = time.monotonic()+22
    while time.monotonic() < deadline:
        try:
            current = camera()
            if current['detected_frames'] > 1 and not current['camera_error'] and not current['detector_error'] and current['observation_age_ms'] is not None and current['observation_age_ms'] < 750:
                report['camera_after'] = current
                report['camera_restored'] = True
                break
        except Exception:
            pass
        time.sleep(.4)
    if report.get('camera_restored'):
        service('stop', timer+'.timer')
report['test_and_recovery_seconds'] = round(time.monotonic()-started, 3)
report['ui_pid_preserved'] = ui_pid == service('show', 'aura-avatar-ui.service', '-p', 'MainPID', '--value').stdout.decode().strip()
report['protected_configuration_hashes_unchanged'] = all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == sha for p, sha in protected.items())
report['boot_preserved'] = Path('/proc/sys/kernel/random/boot_id').read_text().strip() == boot
report['status'] = 'PASS_STANDALONE_DPU_ENGINEERING' if report.get('core', {}).get('all_host_quantized_agreement') and report.get('camera_restored') and report['ui_pid_preserved'] and report['protected_configuration_hashes_unchanged'] and report['boot_preserved'] else 'FAILED_STANDALONE_DPU_ENGINEERING'
(ROOT/'standalone-result.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)
