"""Verify the live shadow payload and stage an owned ExecStart override only."""
import hashlib,json,os,subprocess,urllib.request
from pathlib import Path

OPS=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
SHADOW=OPS/'pan-follow-shadow-live';BOOT='1236ccf4-7df1-420e-83e7-8df17e2c53a4'
ENTRY=OPS/'native_entry_pan_shadow.py'
DROP=Path('/etc/systemd/system/aura-camera-ui.service.d/zzzzzzzzzzzz-aura-pan-follow-shadow.conf')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(port,path):
 op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def props():
 s=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','Restart','-p','KillMode','-p','SendSIGKILL','-p','TimeoutStopUSec'],text=True)
 return dict(x.split('=',1) for x in s.splitlines() if '=' in x)
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert not DROP.exists() and not DROP.is_symlink()
assert not (SHADOW/'stage-state.json').exists()
m=json.loads((SHADOW/'deployment-manifest.json').read_text());assert m['schema']=='aura-pan-follow-shadow-transfer-1'
for f in m['files']:
 p=Path(f['destination']);assert p.is_file() and not p.is_symlink() and p.stat().st_size==f['bytes'] and sha(p)==f['sha256']
meta=json.loads((OPS/'meta.json').read_text());assert meta['source_boot']!=BOOT
assert all(sha(OPS/n)==h for n,h in meta['source_pins'].items())
app=Path(meta['candidate_root'])/'aura'
assert sha(app/'board/vision/ui_camera_service.py')==meta['candidate_ui_sha256']
assert sha(app/'board/motion/camera_feed.py')=='2bf8983cf195af94d4a6faefc48eefdbc9b2a02ffcd863f9ffac006dc495f3e7'
assert sha(app/'common/motion_observation.py')=='c676a81093793ee7046d1937c56478efe27a94505c9fd62696e82fc426acf9dc'
assert sha(app/'tools/board_camera_motion.py')=='1e0e6f0b8881c2d4d4cf81a2527e79d063e673eeba1d069e33bdde2608303005'
c=props();assert c['ActiveState']=='active' and c['SubState']=='running' and c['Restart']=='no'
assert c['KillMode']=='process' and c['SendSIGKILL']=='no' and c['TimeoutStopUSec']=='infinity'
h=get(8790,'/health');u=get(8783,'/api/state');pan=u.get('manual_pan',{});rb=pan.get('readback',{})
assert str(h['pid'])==c['MainPID'] and h['dpu_schedule']['native_critical'] and not h['dpu_schedule']['owner_fenced']
assert h['identity']['ready'] and h['identity']['face_targets']['worker_alive']
assert u['phase']=='IDLE' and not u.get('playing') and u.get('audio_output_state')=='IDLE_READY'
assert pan.get('state')=='READY' and pan.get('pulse_us')==1425 and not pan.get('automatic_following') and not pan.get('panel_open')
assert rb.get('flags')==0 and rb.get('lease_left_ms')==0 and not rb.get('active') and not rb.get('armed')
checks=[(str(ENTRY),sha(ENTRY))]+[(f['destination'],f['sha256']) for f in m['files']]
code="import hashlib;checks="+repr(checks)+";assert all(hashlib.sha256(open(p,'rb').read()).hexdigest()==h for p,h in checks)"
raw=('[Service]\nExecStart=\nExecStartPre=/usr/bin/python3 -B -c "'+code+'"\nExecStart=/usr/bin/python3 -B '+str(ENTRY)+'\n').encode()
with DROP.open('xb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
try:
 subprocess.run(['systemctl','daemon-reload'],check=True,timeout=15)
 q=props();assert q['MainPID']==c['MainPID'] and q['ActiveState']=='active'
 shown=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','LoadState','-p','LoadError','-p','ExecStart','-p','ExecStartPre'],text=True)
 assert 'LoadState=loaded' in shown and 'LoadError=' in shown and ENTRY.name in shown and 'sha256' in shown
 state={'phase':'DROPIN_STAGED_NO_RESTART','boot':BOOT,'camera_pid_before':int(c['MainPID']),
  'gui_pid_before':int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True)),
  'dropin':str(DROP),'dropin_sha256':sha(DROP),'entry_sha256':sha(ENTRY),'manual_flags':rb.get('flags'),
  'manual_lease_ms':rb.get('lease_left_ms'),'motion_feed_before':404}
 (SHADOW/'stage-state.json').write_text(json.dumps(state,indent=2)+'\n')
 print(json.dumps(state,sort_keys=True))
except BaseException:
 if DROP.is_file() and not DROP.is_symlink():
  expected=hashlib.sha256(raw).hexdigest()
  if sha(DROP)==expected:
   DROP.unlink();subprocess.run(['systemctl','daemon-reload'],timeout=15)
 raise
