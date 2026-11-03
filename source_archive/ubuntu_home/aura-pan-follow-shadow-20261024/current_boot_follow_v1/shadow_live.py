"""Ten seconds actual observations with virtual actuator; same GUI stays up."""
import hashlib,json,os,signal,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');S=F/'shadow-v10r3'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
s=json.loads((R/'state.json').read_text());assert s['phase']=='CURRENT_BOOT_R3_PREPARED_OUTPUT_STOPPED'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(S/'manifest.json')=='777dbbddce409215db753a5ad55ed2693d3d6cb90f9ed2c91cd392e3a7cd23f0'
assert sha(R/'direction-calibration.json')==s['direction_evidence_sha256']
u=get(8783,'/api/state');m=u['manual_pan'];before=m['readback'];h=get(8790,'/health')
assert m['state']=='READY' and not m['automatic_following'] and before['flags']==0 and before['lease_left_ms']==0
assert h['pid']==13537 and not h['dpu_schedule']['owner_fenced']
pid=m['backend_pid'];proc=Path('/proc')/str(pid);birth=(proc/'stat').read_text().split()[21]
assert 'aura-avatar-ui.service' in (proc/'cgroup').read_text() and b'spawn_main' in (proc/'cmdline').read_bytes()
out=R/'shadow-v10r3-live10.json';assert not out.exists()
fd=os.pidfd_open(pid)
try:
 assert (proc/'stat').read_text().split()[21]==birth;signal.pidfd_send_signal(fd,signal.SIGTERM)
finally:os.close(fd)
end=time.monotonic()+6
while proc.exists() and time.monotonic()<end:time.sleep(.05)
assert not proc.exists()
failure=None;report=None
try:
 p=subprocess.run(['/usr/bin/python3','-B',str(S/'run_shadow.py'),'--manifest-sha256',sha(S/'manifest.json'),
  '--direction-evidence',str(R/'direction-calibration.json'),'--settings',str(R/'face-zone-settings.json'),
  '--output',str(out),'--duration','10','--confirmation','SHADOW_ONLY'],capture_output=True,text=True,timeout=22)
 report=json.loads(out.read_text()) if out.exists() else None
 assert p.returncode==0,{'stderr':p.stderr[-500:],'report':report}
 assert report['status']=='SHADOW_FINISHED' and not report['result']['fatal'] and report['control_polarity']==-1
 assert not report['MMIO_opened'] and report['physical_ARM']==0 and report['physical_COMMIT']==0
except Exception as error:failure=type(error).__name__+': '+str(error)[:1200]
finally:
 q=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_reconnect"}',headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(q,timeout=4) as stream:assert json.load(stream).get('ok')
 end=time.monotonic()+5;after=None
 while time.monotonic()<end:
  after=get(8783,'/api/state')['manual_pan']
  if after['state']=='READY':break
  time.sleep(.1)
 assert after['state']=='READY' and before==after['readback'] and not after['automatic_following']
s.update(phase='CURRENT_BOOT_R3_SHADOW_PASS_OUTPUT_STOPPED' if not failure else 'CURRENT_BOOT_R3_SHADOW_FAILED_OUTPUT_STOPPED',
 shadow_r3_pass=failure is None,shadow_r3_report=str(out),shadow_r3_report_sha256=sha(out) if out.exists() else None)
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'error':failure,'shadow':report,'manual_readback_unchanged':True,'new_backend_pid':after['backend_pid']}))
if failure:raise SystemExit(1)
