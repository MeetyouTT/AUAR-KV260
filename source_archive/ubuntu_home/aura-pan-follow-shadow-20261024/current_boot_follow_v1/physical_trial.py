"""One 20s controlled face window; no reinitialization or UI/camera restart."""
import hashlib,json,os,signal,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');G=R/'gui-manual-bound-v1';A=G/'runtime/aura'
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v10r3')
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
s=json.loads((R/'state.json').read_text());assert s['phase']=='CURRENT_BOOT_R3_SHADOW_PASS_OUTPUT_STOPPED' and s['shadow_r3_pass']
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
assert sha(s['shadow_r3_report'])==s['shadow_r3_report_sha256']
shadow=json.loads(Path(s['shadow_r3_report']).read_text())
assert shadow['status']=='SHADOW_FINISHED' and not shadow['result']['fatal'] and shadow['control_polarity']==-1
assert shadow['packet_states'].get('READY',0)>=10,'No adequate actual face observations; no physical test'
assert not shadow['MMIO_opened'] and shadow['physical_ARM']==0 and shadow['physical_COMMIT']==0
assert sha(P/'deployment-manifest.json')=='56f4207a4dc033c9762f1476e8b8a4824bab513c02eae1df9dbaa2e706b34385'
assert all(sha(row['destination'])==row['sha256'] for row in json.loads((P/'deployment-manifest.json').read_text())['files'])
assert sha(R/'direction-calibration.json')==s['direction_evidence_sha256']
c=json.loads((G/'startup/config.json').read_text());assert all(sha(A/n)==h for n,h in c['component_sha256'].items())
face=json.loads((A/'config/pan_face.local.json').read_text());assert face['release_root']==str(P) and face['manifest_sha256']==sha(P/'deployment-manifest.json')
assert json.loads((A/'config/pan_manual.local.json').read_text())['automatic_following_enabled'] is False
u=get(8783,'/api/state');m=u['manual_pan'];h=get(8790,'/health')
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
assert h['pid']==13537 and not h['dpu_schedule']['owner_fenced']
assert u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY'
assert u.get('local_recording',{}).get('state')!='RECORDING' and not u.get('local_transcription',{}).get('service',{}).get('pending')
v=get(8790,'/v1/ui/status');assert v.get('modules',{}).get('identity',{}).get('state') not in ('ENROLLING','SAMPLING')
run=P/'runs'/('board-observed-'+str(time.monotonic_ns()));run.mkdir(parents=True,mode=0o700);out=run/'trial.json'
pid=m['backend_pid'];proc=Path('/proc')/str(pid);birth=(proc/'stat').read_text().split()[21]
assert 'aura-avatar-ui.service' in (proc/'cgroup').read_text() and b'spawn_main' in (proc/'cmdline').read_bytes()
fd=os.pidfd_open(pid)
try:
 assert (proc/'stat').read_text().split()[21]==birth;signal.pidfd_send_signal(fd,signal.SIGTERM)
finally:os.close(fd)
end=time.monotonic()+6
while proc.exists() and time.monotonic()<end:time.sleep(.05)
assert not proc.exists(),'Manual owner did not exit normally; no physical test'
s.update(phase='R3_BOUNDED_FACE_TEST_RUNNING',physical_trial=str(out),automatic_following=False)
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
failure=None;report=None;after=None
try:
 args=['/usr/bin/python3','-B',str(P/'run_face_motion.py')]
 for k,v in face['arguments'].items():args.extend(['--'+k,v])
 args.extend(['--output',str(out),'--confirmation','FACE_ZONE_CONTINUOUS','--duration','20'])
 p=subprocess.run(args,capture_output=True,text=True,timeout=34)
 report=json.loads(out.read_text()) if out.exists() else None
 assert p.returncode==0,{'stderr':p.stderr[-700:],'report':report}
 assert report['status']=='CONTINUOUS_FACE_ZONE_STOPPED' and not report['result']['fatal']
 assert report['result']['stopped']['flags']==0 and report['result']['stopped']['lease_left_ms']==0
except Exception as error:failure=type(error).__name__+': '+str(error)[:1600]
finally:
 q=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_reconnect"}',headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(q,timeout=4) as stream:assert json.load(stream).get('ok')
 end=time.monotonic()+5
 while time.monotonic()<end:
  after=get(8783,'/api/state')['manual_pan']
  if after['state']=='READY':break
  time.sleep(.1)
s.update(phase='R3_BOUNDED_FACE_STOPPED_FEEDBACK_PENDING' if not failure and after['state']=='READY' else 'R3_BOUNDED_FACE_FAILED_NO_RETRY',
 physical_trial_sha256=sha(out) if out.exists() else None,current_last_command_us=(after.get('readback') or {}).get('width_us'),automatic_following=False)
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
assert get(8790,'/health')['pid']==13537
print(json.dumps({'status':s['phase'],'error':failure,'trial':report,'manual':after,'camera_pid':13537,
 'gui_restarted':False,'center_reference_us':1420,'center_command_applied':False,'full_follow_human_acceptance':False}))
if failure or after['state']!='READY':raise SystemExit(1)
