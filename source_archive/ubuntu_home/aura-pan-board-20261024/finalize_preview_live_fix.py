"""Finalize the already running patched GUI after its slow first startup."""
import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
cfg=json.loads((N/'startup/config.json').read_text());root=Path(cfg['runtime'])/'aura'
assert all(sha(root/n)==v for n,v in cfg['component_sha256'].items())
assert b'deadline=500 if self.reader_owner else 1500' in (root/'tools/board_camera_preview.py').read_bytes()
u=get(8783,'/api/state');h=get(8790,'/health');m=u['manual_pan'];assert u['phase']=='IDLE' and m['state']=='READY' and m['readback']['flags']==0
base='http://127.0.0.1:8783'
for typ in (['pan_reverse'] if m['left_sign']==-1 else [])+['pan_dialog','pan_close']:
 req=urllib.request.Request(base+'/api/command',data=json.dumps({'type':typ}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(req,timeout=3) as r:assert json.load(r)['ok']
 time.sleep(.3)
pid=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True))
s=json.loads((F/'stage-state.json').read_text());assert h['pid']==s['camera_pid'];s['gui_pid']=pid;(F/'stage-state.json').write_text(json.dumps(s,indent=2)+'\n')
st=json.loads((N/'stage.json').read_text());st.update(phase='READY_PREVIEW_CONTINUITY_FIX',gui_pid=pid,camera_pid=h['pid'],config_sha256=sha(N/'startup/config.json'));(N/'stage.json').write_text(json.dumps(st,indent=2)+'\n')
report={'status':'DISPLAY_CONTINUITY_FIX_ACTIVE','gui_pid':pid,'camera_pid':h['pid'],'source_ttl_ms':250,'motion_ttl_ms':250,'display_grace_ms':500,
 'changed':{name:{'before_sha256':sha(N/'preview-fix-live-sink-backup'/name),'after_sha256':sha(root/name)} for name in ('tools/board_camera_preview.py','tools/board_avatar_gtk.py')},
 'manual':get(8783,'/api/state')['manual_pan'],'camera_service_restarted':False,'new_motion_commands':0}
(N/'preview-continuity-fix.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,sort_keys=True))
