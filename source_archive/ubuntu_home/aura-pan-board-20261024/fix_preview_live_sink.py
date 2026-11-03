"""Apply display-only grace; preserve the already mapped canvas and 250ms source TTL."""
import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');GUI='aura-avatar-ui.service'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def atomic(p,raw):
 t=p.with_name(p.name+'.preview-fix');assert not t.exists()
 with t.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 os.replace(t,p)
cfgpath=N/'startup/config.json';oldcfg=cfgpath.read_bytes();cfg=json.loads(oldcfg);root=Path(cfg['runtime'])/'aura'
assert root.resolve().parent==N/'runtime'
b=get(8790,'/health');u=get(8783,'/api/state');m=u['manual_pan'];r=m['readback']
assert u['phase']=='IDLE' and not u['playing'] and m['state']=='READY' and r['flags']==0 and r['lease_left_ms']==0
replacements={
 'tools/board_camera_preview.py':(b'deadline=250 if self.reader_owner else 1500',b'deadline=500 if self.reader_owner else 1500'),
 'tools/board_avatar_gtk.py':(b'self.preview_placeholder.set_visible(not bool(image))',b"self.preview_placeholder.set_visible(self.preview_output.placeholder_visible(display, modules.get('camera',{}).get('state')) if self.preview_output else not bool(image))")}
assert b'self.preview_image.set_visible(True)' in (root/'tools/board_avatar_gtk.py').read_bytes()
backup=N/'preview-fix-live-sink-backup';assert not backup.exists();backup.mkdir(mode=0o700);(backup/'config.json').write_bytes(oldcfg)
files={}
for name,(before,after) in replacements.items():
 p=root/name;p.parent.resolve().relative_to(N.resolve());raw=p.read_bytes()
 assert sha(raw)==cfg['component_sha256'][name] and raw.count(before)==1
 updated=raw.replace(before,after)
 if name=='tools/board_camera_preview.py':
  marker=b"    def read(self, name='main'):";assert updated.count(marker)==1
  helper=b"    @staticmethod\n    def placeholder_visible(display, camera_state):\n        if display.get('frame_visible'):return False\n        live=(camera_state=='READY' and display.get('sink_active') and display.get('transport')=='raw-local' and not display.get('error'))\n        return not live\n\n"
  updated=updated.replace(marker,helper+marker)
 compile(updated,str(p),'exec');files[name]=(raw,updated)
 q=backup/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
subprocess.run(['systemctl','stop','--no-block',GUI],check=True);end=time.monotonic()+25
while time.monotonic()<end:
 if subprocess.check_output(['systemctl','show',GUI,'-p','MainPID','--value'],text=True).strip()=='0':break
 time.sleep(.2)
assert subprocess.check_output(['systemctl','show',GUI,'-p','MainPID','--value'],text=True).strip()=='0'
for name,(before,after) in files.items():
 p=root/name;assert p.read_bytes()==before;atomic(p,after);cfg['component_sha256'][name]=sha(after)
atomic(cfgpath,(json.dumps(cfg,indent=2)+'\n').encode())
assert all(sha((root/n).read_bytes())==v for n,v in cfg['component_sha256'].items())
subprocess.run(['systemctl','reset-failed',GUI],check=True);subprocess.run(['systemctl','start','--no-block',GUI],check=True)
end=time.monotonic()+110;ready=None
while time.monotonic()<end:
 try:
  u=get(8783,'/api/state')
  if u['phase']=='IDLE' and u['manual_pan']['state']=='READY':ready=u;break
 except Exception:pass
 state=subprocess.check_output(['systemctl','show',GUI,'-p','ActiveState','--value'],text=True).strip()
 if state=='failed':break
 time.sleep(.5)
assert ready is not None,'GUI startup failed after display continuity change'
base='http://127.0.0.1:8783'
for typ in (['pan_reverse'] if ready['manual_pan']['left_sign']==-1 else [])+['pan_dialog','pan_close']:
 req=urllib.request.Request(base+'/api/command',data=json.dumps({'type':typ}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(req,timeout=3) as response:assert json.load(response)['ok']
 time.sleep(.25)
a=get(8790,'/health');assert a['pid']==b['pid'];pid=int(subprocess.check_output(['systemctl','show',GUI,'-p','MainPID','--value'],text=True))
s=json.loads((F/'stage-state.json').read_text());s['gui_pid']=pid;(F/'stage-state.json').write_text(json.dumps(s,indent=2)+'\n')
report={'status':'DISPLAY_CONTINUITY_FIX_ACTIVE','gui_pid':pid,'camera_pid':a['pid'],'source_ttl_ms':250,'motion_ttl_ms':250,'display_grace_ms':500,
 'changed':{name:{'before_sha256':sha(v[0]),'after_sha256':sha(v[1])} for name,v in files.items()},'backup':str(backup),'config_sha256':sha(cfgpath.read_bytes()),
 'manual':get(8783,'/api/state')['manual_pan'],'primary_delta':a['dpu_schedule']['primary_period_overruns']-b['dpu_schedule']['primary_period_overruns']}
(N/'preview-continuity-fix.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,sort_keys=True))
