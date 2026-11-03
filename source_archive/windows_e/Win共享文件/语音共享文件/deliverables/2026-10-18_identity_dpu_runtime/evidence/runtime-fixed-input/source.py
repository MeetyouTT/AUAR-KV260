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
ROOT = Path('/home/root/aura-adaptation-20261006/identity_dpu_runtime_20261018/96f86ddef3a96b93')
core = "\nimport hashlib,json,sys,time,statistics\nfrom pathlib import Path\nimport numpy as np\napp=Path('/home/root/aura-adaptation-20261006/identity_dpu_runtime_20261018/96f86ddef3a96b93/candidate/runtime/aura')\nsys.path.insert(0,str(app))\nfrom board.vision.ui_camera_service import checked_backend,CameraState\nfrom board.vision.dpu_schedule import DpuSchedule\nfrom board.identity.camera_faces import CameraFaceExtractor,config_for\nfrom board.identity.live import IdentityService\nfrom board.identity.store import IdentityStore\nfrom board.interaction.ui_contract import millis,validate_snapshot\nconfig=json.loads((app/'config/board_camera_ui.json').read_text())\ncv2,np,detector,Tracks=checked_backend(config)\ncfg=config_for(app,config['identity']['config'])\ngate=DpuSchedule()\nextractor=CameraFaceExtractor(cfg,gate,detector.verify_runtime())\nreference=Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/bee245f2a94e4d28/hardware-reference.npz')\nvectors=np.load(str(reference),allow_pickle=False)\nresults=[]\nfor name in vectors['names']:\n source=vectors['input_'+str(name)]\n rgb=np.clip(source[0].astype(np.int16)+127,0,255).astype(np.uint8)\n crop=np.ascontiguousarray(rgb[:,:,::-1])\n from board.identity.dpu_sface import quantize_crop\n assert np.array_equal(quantize_crop(crop),source)\n with gate.detection(time.monotonic()+1):pass\n feature=extractor.embedder.feature(crop);assert feature is not None\n output=np.rint(feature*32).astype(np.int8)\n expected=vectors['quantized_'+str(name)].reshape(-1)\n delta=int(np.max(np.abs(output.astype(np.int16)-expected.astype(np.int16))))\n assert delta==0\n results.append({'sample':str(name),'maximum_integer_difference':delta,'feature_sha256':hashlib.sha256(feature.tobytes()).hexdigest()})\nperson=cv2.imread(config['yolo']['reference_image'])\nface=cv2.imread('/home/root/aura-adaptation-20261006/identity/reference/lena.jpg')\nassert person is not None and face is not None\nstart=time.monotonic();yolo_times=[];sface_times=[];overruns=0\nfor i in range(80):\n before=time.monotonic()\n with gate.detection(start+(i+1)*.1):people=detector.detect_bgr(person)\n assert len(people)>=2\n yolo_times.append((time.monotonic()-before)*1000)\n if i%5==0:\n  value=extractor.embedder.feature(crop)\n  assert value is not None\n  sface_times.append(extractor.embedder.last_ms)\n wait=start+(i+1)*.1-time.monotonic()\n if wait<0:overruns+=1\n else:time.sleep(wait)\nstate=CameraState('fixed-input-test-boot',clock=millis)\nstore=IdentityStore(':memory:',cfg['model_id'],128,cfg['threshold'],cfg['ambiguity_margin'])\nservice=IdentityService(store,lambda:extractor,state.identity_target,lock=state.lock,clock=millis,\n backend='DPU_SFACE_INT8',known_frames=3,enrollment_target=state.identity_enrollment_target)\nstate.identity=service;service.ready=True\nfor i in range(6):\n if i:time.sleep(.42)\n image=cv2.convertScaleAbs(face,alpha=.9+i*.04,beta=i)\n stamp=millis();fid=state.captured(stamp)\n obs={'target_id':1,'tracks':[{'track_id':1,'generation':1,'box':(0,0,image.shape[1],image.shape[0]),'visible':True,'confirmed':True}]}\n state.observed(fid,stamp,obs,0.)\n with gate.detection(time.monotonic()+2):detector.detect_bgr(person)\n service.offer(image,fid,stamp,obs,state.camera_epoch)\n packet,service.pending=service.pending,None\n service.process(packet,extractor)\n if i==0:\n  assert service.result is not None,service.reason\n  service.begin_enrollment({'target':state.identity_target(),'display_name':'PUBLIC_FIXTURE_ONLY','confirmed':True},'fixture-enrollment')\nassert service.last_operation['state']=='COMMITTED',service.last_operation\nassert store.revision==1\nvalidate_snapshot(state.snapshot(),state.boot,millis())\nsummary={'all_host_quantized_agreement':True,'fixed_vectors':results,\n 'mixed_fixed_input':{'yolo_calls':80,'sface_calls':len(sface_times),'period_overruns':overruns,\n 'yolo_median_ms':statistics.median(yolo_times),'sface_median_ms':statistics.median(sface_times),\n 'yolo_max_ms':max(yolo_times),'sface_max_ms':max(sface_times)},\n 'public_fixture_five_sample_transaction':'COMMITTED_IN_MEMORY_ONLY',\n 'same_process':True,'schedule':gate.health(),'real_person_enrolled':False,'real_accuracy_verified':False}\nassert not summary['schedule']['identity_disabled']\nextractor.close();detector.close();service.close()\nprint(json.dumps(summary),flush=True)\n"


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
report = {'scope': 'RUNTIME_ADAPTER_FIXED_INPUT_TEST_WITH_CAMERA_TEMPORARILY_STOPPED', 'boot_id': boot,
          'camera_before': before, 'production_configuration_changed': False,
          'real_identity_accuracy_accepted': False, 'unified_dpu_scheduler_tested': True,
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
report['status'] = 'PASS_RUNTIME_ADAPTER_FIXED_INPUT' if report.get('core', {}).get('all_host_quantized_agreement') and report.get('camera_restored') and report['ui_pid_preserved'] and report['protected_configuration_hashes_unchanged'] and report['boot_preserved'] else 'FAILED_RUNTIME_ADAPTER_FIXED_INPUT'
(ROOT/'runtime-fixed-input-result.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)
