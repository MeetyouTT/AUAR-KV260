"""Read audio capabilities and the active base without opening capture."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import ctypes.util,hashlib,json,re,subprocess,urllib.request
from pathlib import Path
import gi
gi.require_version('Gst','1.0')
from gi.repository import Gst
Gst.init(None)
elements={}
for name in ('webrtcdsp','webrtcechoprobe','alsasrc','appsink','appsrc','alsasink','audioconvert','audioresample'):
 factory=Gst.ElementFactory.find(name);row={'available':bool(factory)}
 if factory:
  element=Gst.ElementFactory.make(name,None)
  row['plugin']=factory.get_plugin_name()
  if name.startswith('webrtc'):row['properties']={p.name:str(element.get_property(p.name)) for p in element.list_properties() if p.flags&1}
 elements[name]=row
def get(port,path):return json.load(urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=4))
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
cfgpath=Path(re.search(r'--config (\S+)',unit).group(1));cfg=json.loads(cfgpath.read_text());root=Path(cfg['runtime'])
camera_unit=subprocess.check_output(['systemctl','cat','aura-camera-ui.service'],text=True)
camcfgpath=Path(re.search(r'--config (\S+)',camera_unit).group(1));camcfg=json.loads(camcfgpath.read_text())
idcfgpath=Path(camcfg['identity']['config']);idraw=idcfgpath.read_bytes();idcfg=json.loads(idraw);db=Path(idcfg['database']).expanduser()
state=get(8783,'/api/state');cam=get(8790,'/health')
source={}
rows=subprocess.check_output(['ps','-eo','pid,args'],text=True).splitlines()
pids=[int(row.split()[0]) for row in rows if str(root)+'/aura/tools/board_avatar_gtk.py' in row]
assert len(pids)==1,pids
env=dict(v.split('=',1) for v in Path('/proc/%d/environ'%pids[0]).read_bytes().decode().split('\0') if '=' in v)
for package in ('tools','board','common','host'):
 for path in (root/'aura'/package).rglob('*.py'):source[path.relative_to(root).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
result={'runtime':str(root),'ui_home':env['HOME'],'config_path':str(cfgpath),'startup_config':cfg,'ui_unit':unit,'camera_unit':camera_unit,
 'camera_pid':cam['pid'],'camera_service_epoch':cam['service_epoch'],
 'camera_config_sha256':hashlib.sha256(camcfgpath.read_bytes()).hexdigest(),
 'identity_config_sha256':hashlib.sha256(idraw).hexdigest(),'identity_threshold':idcfg['threshold'],
 'identity_db_sha256':hashlib.sha256(db.read_bytes()).hexdigest(),'source_hashes':source,
 'ui_state':{k:state.get(k) for k in ('phase','playing','paused','handsfree_dialogue','local_recording','automatic_conversation','audio_output_state')},
 'gstreamer':Gst.version_string(),'elements':elements,
 'libraries':{n:ctypes.util.find_library(n) for n in ('speexdsp','webrtc_audio_processing','asound')},
 'alsa_streams':{str(p):p.read_text() for p in Path('/proc/asound').glob('card*/stream*')},
 'audio_holders':subprocess.run(['fuser','/dev/snd/pcmC0D0c','/dev/snd/pcmC1D0c'],capture_output=True,text=True).stdout}
print(json.dumps(result))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=30))
(HERE/'board_baseline.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps({k:r[k] for k in ('runtime','gstreamer','elements','libraries','alsa_streams','ui_state')},ensure_ascii=True))
