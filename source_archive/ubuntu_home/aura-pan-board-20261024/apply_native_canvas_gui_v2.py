"""Patch only own GTK proxy; preserve camera, firmware and stopped position."""
import hashlib,json,os,shutil,subprocess,urllib.request
from pathlib import Path
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');A=N/'runtime/aura';p=A/'tools/face_pan_controls.py'
src=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/gui-continuous-v2/face_pan_controls.py')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(src)=='cb973b5a6dc1e783e0fef84231964c825e24028cf83aaa831777a4594868d20c'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
m=u['manual_pan'];assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0
cfgpath=N/'startup/config.json';cfg=json.loads(cfgpath.read_text());assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
backup=N/'native-canvas-v2-before';assert not backup.exists();backup.mkdir();shutil.copy2(p,backup/p.name);shutil.copy2(cfgpath,backup/'startup.json')
temp=p.with_name(p.name+'.canvas-v2');temp.write_bytes(src.read_bytes());os.replace(temp,p)
cfg['component_sha256']['tools/face_pan_controls.py']=sha(p);temp=cfgpath.with_name('config.canvas-v2.tmp');temp.write_text(json.dumps(cfg,indent=2)+'\n');os.replace(temp,cfgpath)
assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
unit='aura-avatar-ui.service';before=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True).strip()
subprocess.run(['systemctl','restart','--no-block',unit],check=True)
print(json.dumps({'status':'NATIVE_CANVAS_V2_GUI_RESTARTING','old_gui_pid':before,'camera_restarted':False,'movement_commands':0,'pins':len(cfg['component_sha256'])}))
