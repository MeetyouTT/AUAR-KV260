BOOT='1236ccf4-7df1-420e-83e7-8df17e2c53a4'
ROOT='/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4-r2'
CONTROLLER='/home/root/aura-post-power-20261022/helpers/ded9704ecc463a50/source.py'
CONTROLLER_SHA='ded9704ecc463a5040ff59056efa71321eb104b6aa0d9f047e9e80fb14662c45'
HELPER='/home/root/aura-post-power-20261022/helpers/96420fc26d811e16/source.py'
HELPER_SHA='96420fc26d811e16bd47b8b3d16a0b1a6b3ea9759ba5490564205fc9c0065bb4'
MANIFEST_SHA='ed175a70735b4c445d6f86cbcd2909cdd1add349ba52f852f367a7602d30f9ab'
EXPECTED={'boot_id': '1236ccf4-7df1-420e-83e7-8df17e2c53a4', 'registers': {'flags': 0, 'width_us': 1425, 'lease_left_ms': 0, 'session': 525919161, 'epoch': 1, 'reference_us': 1420, 'target_us': 1425, 'ack_seq': 44, 'active': False, 'armed': False, 'referenced': False, 'bound': False, 'reason': 0}}
import fcntl,hashlib,importlib.util,json,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
controller=Path(CONTROLLER);assert hashlib.sha256(controller.read_bytes()).hexdigest()==CONTROLLER_SHA
helper=Path(HELPER);assert hashlib.sha256(helper.read_bytes()).hexdigest()==HELPER_SHA
spec=importlib.util.spec_from_file_location('observed_pan_controller',str(controller));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
t=m.Trial(ROOT);t.verify();assert t.state()['phase']=='CANDIDATE_STOPPED_RETAINED_PHYSICAL_FEEDBACK_PENDING'
assert t.active()==[m.APP] and t.firmware()==m.APP+'.bit.bin'
h=t.brief(t.get(8790,'/health'));g=t.get(8783,'/api/state')
assert not h['owner_fenced'] and h['worker_alive'] and h['identity_ready']
assert g['phase']=='IDLE' and not g['playing'] and g['audio_output_state']=='IDLE_READY'
assert g.get('local_recording',{}).get('state')!='RECORDING' and not g.get('local_transcription',{}).get('service',{}).get('pending')
root=Path(ROOT);expected=root/'expected-observed-20us-02.json';report=root/'observed-20us-return-02.json'
assert not report.exists()
with expected.open('x') as f:json.dump(EXPECTED,f)
with (root/'operation.lock').open('a+') as own,(Path(t.base['ops_root'])/'operation.lock').open('a+') as other:
 fcntl.flock(own,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(other,fcntl.LOCK_EX|fcntl.LOCK_NB)
 args=['/usr/bin/python3','-B',str(helper),'--execute','--confirmation','OBSERVED_20US_RETURN_2S','--manifest',str(root/'candidate-manifest.json'),'--manifest-sha256',MANIFEST_SHA,'--context',str(root/'context.json'),'--expected-state',str(expected),'--output',str(report)]
 p=subprocess.run(args,capture_output=True,text=True)
 result=json.loads(report.read_text()) if report.exists() else None
 after=t.brief(t.get(8790,'/health'))
print(json.dumps({'exit_code':p.returncode,'result':result,'before_health':h,'after_health':after,'stderr':p.stderr[-1200:]}))
