"""Compare live UI layout and startup state without page changes or restarts."""
import base64,hashlib,json,os,re,subprocess,urllib.request
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cmd(args):
 try:
  p=subprocess.run(args,env=dict(os.environ,DISPLAY=':0'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=5)
  return {'rc':p.returncode,'text':p.stdout[-6500:]}
 except (OSError,subprocess.TimeoutExpired) as exc:return {'unavailable':str(exc)}
pid=cmd(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'])['text'].strip()
argv=(Path('/proc')/pid/'cmdline').read_bytes().decode().split('\0')
config_path=Path(argv[argv.index('--config')+1]);config=json.loads(config_path.read_text())
runtime=Path(config['runtime']);aura=runtime/'aura'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8783/api/state',timeout=2) as response:state=json.load(response)
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'runtime':str(runtime),
 'config_path':str(config_path),'config_sha256':sha(config_path),'launcher_sha256':sha(config_path.with_name('launcher.py')),
 'ui':{k:state.get(k) for k in ['phase','ui_page','ui_layer','ui_pages','ui_settings','error']},
 'unit':cmd(['systemctl','show','aura-avatar-ui.service','-p','MainPID','-p','ActiveState','-p','NRestarts']),
 'files':{},'artifacts':{},'settings':{},'files_modified':0,'page_changes_sent':0,'display_commands_sent':0,'movement_commands_sent':0}
for rel in ['tools/board_avatar_gtk.py','tools/board_avatar_pan.py','tools/board_screen_capture.py','ui/board_touch_layout.json','ui/ui_layout_spec.json','ui/ui_tokens.json','config/board_avatar_gtk.json']:
 p=aura/rel
 if not p.exists():continue
 raw=p.read_bytes();v['files'][rel]={'sha256':sha(p),'expected':config.get('component_sha256',{}).get(rel), 'bytes':len(raw)}
 if rel.startswith('ui/') or rel.endswith('board_avatar_gtk.py'):
  v['artifacts'][p.name]={'sha256':sha(p),'base64':base64.b64encode(raw).decode()}
for name in ['avatar_user_settings.json','launch.json']:
 p=runtime/name
 if not p.exists():continue
 value=json.loads(p.read_text())
 if name=='avatar_user_settings.json':v['settings'][name]=value
 else:
  v['launch']={k:value.get(k) for k in ['pid','supervisor_pid','session']}
  setup=Path(value['session'])/'setup.json'
  if setup.exists():v['display_setup']=json.loads(setup.read_text())
v['xrandr']=cmd(['xrandr','--current'])
v['xresources']=cmd(['xrdb','-query'])
v['xorg_initial_mode']=[line for line in Path('/var/log/Xorg.0.log').read_text().splitlines() if any(s in line for s in ['initial mode','Depth 16','Modeline "1024x600"'])][-12:]
print(json.dumps(v),flush=True)
