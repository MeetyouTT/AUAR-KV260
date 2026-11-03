"""Verify only public portrait and static navigation pixels; preserve page."""
import base64
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

SCRIPT=r'''
import sys,json,os,hashlib,urllib.request,importlib.util,base64,subprocess,time
from pathlib import Path
root=Path('/home/root/aura-character-xuefei-20261030/f94fca2c94288acb');aura=root/'runtime/aura'
assert hashlib.sha256((root/'startup/config.json').read_bytes()).hexdigest()=='4c78824ba9c1c04bb95389a49b64215a7f624a323becae637bc8d4e7c4db4d7e'
launch=json.loads((root/'runtime/launch.json').read_bytes());pid=launch['pid']
unit_pid=int(subprocess.check_output(['/bin/systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True));assert launch['supervisor_pid']==unit_pid and Path('/proc',str(pid)).exists()
for entry in (Path('/proc')/str(pid)/'environ').read_bytes().split(bytes([0])):
 if b'=' in entry:
  k,v=entry.split(b'=',1)
  if k.decode() in ('DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS'):os.environ[k.decode()]=v.decode()
p=Path('/home/root/aura-board-owner-candidate-20261030/ui-round2-4750fc97e43a75bd/x11_close.py');assert hashlib.sha256(p.read_bytes()).hexdigest()=='d7dde3d9ae4ed27e0e06ff9d79a94f70cd94c54842ae5652fd7510b68bab9364'
spec=importlib.util.spec_from_file_location('_appearance_owned_window',str(p));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);x=m.X11(':0')
try:
 rows=x.windows(pid);assert len(rows)==1 and rows[0]['normal']
finally:x.close()
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def state():
 return json.loads(opener.open('http://127.0.0.1:8783/api/state',timeout=2).read(2097152))
def page(name):
 request=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps(dict(type='ui_page',page=name)).encode(),method='POST',headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783','Host':'127.0.0.1:8783'})
 with opener.open(request,timeout=4) as response:result=json.loads(response.read(65536));assert result.get('ok') is True
before=state();saved=before['ui_page'];assert saved in ('main','vision','demo','devices','connection','settings');temporary=saved!='main'
if temporary:page('main')
try:
 deadline=time.monotonic()+5
 while True:
  v=state()
  if v['avatar_display'].get('visible') is True:break
  assert time.monotonic()<deadline;time.sleep(.1)
 assert v['avatar_display']['kind']=='native_yuki_egl' and v['character_pair']['state']=='READY'
 sys.path.insert(0,str(aura));from board.interaction.avatar_board import avatar_box,load_layout
 b=avatar_box(load_layout());regions={'portrait_after':(b['x'],b['y'],b['w'],b['h']),'navigation_after':(8,58,569,48)}
 import gi;gi.require_version('Gdk','3.0');from gi.repository import Gdk
 Gdk.init([]);d=Gdk.Display.get_default();screen=d.get_default_screen();window=screen.get_root_window();assert (screen.get_width(),screen.get_height())==(1024,600)
 time.sleep(.2)
 folder=Path('/home/root/aura-character-appearance-20261030');images={}
 for name,bounds in regions.items():
  pix=Gdk.pixbuf_get_from_window(window,*bounds);assert pix is not None
  out=folder/(name+'.png');pix.savev(str(out),'png',[],[]);out.chmod(0o600);raw=out.read_bytes()
  images[name]=dict(bounds=bounds,png=base64.b64encode(raw).decode(),sha256=hashlib.sha256(raw).hexdigest())
 colors=json.loads((aura/'ui/ui_tokens.json').read_bytes())['colors']
 result=dict(status='PUBLIC_APPEARANCE_CAPTURE',supervisor_pid=unit_pid,gtk_pid=pid,images=images,palette={k:colors[k] for k in ('panel_bg','bg','accent','accent_dark','text_primary','text_secondary')},pair_ready=True,no_camera_or_identity_or_dialogue_region=True)
finally:
 if temporary and state()['ui_page']=='main':page(saved)
result.update(original_page=saved,final_page=state()['ui_page'])
print(json.dumps(result))
'''

def main():
    value=json.loads(ssh('python3 -B -',SCRIPT,timeout=20))
    folder=HERE/'evidence';folder.mkdir(exist_ok=True);paths={}
    for name,item in value['images'].items():
        path=folder/(name+'.png');path.write_bytes(base64.b64decode(item.pop('png')));paths[name]=str(path)
    (folder/'appearance_after.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(output=paths,**value),ensure_ascii=True))

if __name__=='__main__':main()
