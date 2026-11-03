"""Four existing 2s <=5us steps, anchored to each actual stopped readback."""
import fcntl,hashlib,importlib.util,json,os,signal,subprocess,sys,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
O=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735');P=O/'pan-face-edge-v5/attended-reference-1420';C=O/'pan-face-edge-v5/continuous-v10r14'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as f:return json.load(f)
def command(kind):
 base='http://127.0.0.1:8783';q=urllib.request.Request(base+'/api/command',data=json.dumps({'type':kind}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(q,timeout=3) as f:return json.load(f)
s=json.loads((R/'state.json').read_text());prep=json.loads((P/'prepared.json').read_text())
assert prep['boot_id']==s['boot']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert sha(G/'startup/config.json')==prep['startup_config_sha256']
cfg=json.loads((G/'startup/config.json').read_text());assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
assert all(sha(x['destination'])==x['sha256'] for x in json.loads((C/'deployment-manifest.json').read_text())['files'])
m=get(8783,'/api/state')['manual_pan'];assert m['state']=='READY' and not m['automatic_following'] and m['readback']==prep['before']
assert get(8790,'/health')['pid']==prep['camera_pid']
root=Path(s['old_root']);sys.path.insert(0,str(root))
from bench_identity_stop import validated_context
from types import SimpleNamespace
driver_root,manifest,boot=validated_context(SimpleNamespace(manifest=root/'candidate-manifest.json',manifest_sha256='ed175a70735b4c445d6f86cbcd2909cdd1add349ba52f852f367a7602d30f9ab',context=R/'context.json'))
bench=root/'bench_finite_step.py'
assert sha(bench)==json.loads((root/'payload.json').read_text())['files']['bench_finite_step.py']
spec=importlib.util.spec_from_file_location('existing_finite_bench',bench);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
sys.path.insert(0,str(C))
from batch_transport import BatchRegisters
from batch_driver import BatchDriver
pid=m['backend_pid'];proc=Path('/proc')/str(pid);birth=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]
assert 'aura-avatar-ui.service' in proc.joinpath('cgroup').read_text() and b'spawn_main' in proc.joinpath('cmdline').read_bytes()
lock=(O/'operation.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
report_path=P/'reference-trial.json';assert not report_path.exists()
report=dict(status='STARTING',boot_id=boot,target_kind='manual_reference_check',sequence_us=[1402,1407,1412,1417,1420],physical_motion_verified=False,segments=[])
with report_path.open('x') as f:json.dump(report,f)
fd=os.pidfd_open(pid)
try:
 assert proc.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==birth
 signal.pidfd_send_signal(fd,signal.SIGTERM)
finally:os.close(fd)
until=time.monotonic()+6
while proc.exists() and time.monotonic()<until:time.sleep(.05)
assert not proc.exists(),'Manual owner did not exit; trial not started'
failure=None
try:
 lib=C/'libvsrv_batch.so';pin=next(x['sha256'] for x in json.loads((C/'deployment-manifest.json').read_text())['files'] if x['destination']==str(lib))
 with BatchRegisters(lib,pin,boot,manifest['runtime_files']) as io:
  device=BatchDriver(io,0x778d2512,boot)
  assert device.status()==prep['before']
  for initial,target in zip(report['sequence_us'],report['sequence_us'][1:]):
   current=device.status();assert current['flags']==0 and current['lease_left_ms']==0 and current['width_us']==initial
   events=[];result=mod.run_finite(io,device,initial,target,events)
   report['segments'].append(dict(initial_us=initial,target_us=target,events=events,result=result))
   assert result['stopped']['width_us']==target
  report['stopped']=device.status();report['status']='ATTENDED_REFERENCE_STOPPED_OBSERVATION_PENDING'
except BaseException as exc:
 failure=type(exc).__name__+': '+str(exc)[:400];report.update(status='FAILED_NO_AUTOMATIC_RETRY',error=failure)
finally:
 report_path.write_text(json.dumps(report,indent=2)+'\n')
 assert command('pan_reconnect').get('ok')
 until=time.monotonic()+7
 while time.monotonic()<until:
  after=get(8783,'/api/state')['manual_pan']
  if after['state'] in ('READY','FAULT'):
   if after['backend_pid']!=pid:break
  time.sleep(.1)
 report['gui_after']=after;report_path.write_text(json.dumps(report,indent=2)+'\n')
assert after['state']=='READY' and not after['automatic_following'] and after['readback']['flags']==0 and after['readback']['lease_left_ms']==0
s.update(phase=report['status'],current_last_command_us=after['readback']['width_us'],startup_config_sha256=sha(G/'startup/config.json'),attended_reference_report=str(report_path),automatic_following=False)
(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'status':report['status'],'error':failure,'sequence_us':report['sequence_us'],'completed_segments':len(report['segments']),
 'readback':after['readback'],'manual_bounds_us':[after['minimum_us'],after['maximum_us']],'left_sign':after['left_sign'],'report':str(report_path),'physical_observation_pending':True,'camera_restarted':False,'gui_restarted':False}))
assert failure is None,failure
