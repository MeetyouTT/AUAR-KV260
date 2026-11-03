import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'stable_fps_candidate.json').read_text())
job=r'''
import json,sys,time
from pathlib import Path
from unittest.mock import patch
root=Path(RUNTIME);stage=root.parent;sys.path.insert(0,str(root/'aura'))
from common.handsfree_settings import HandsFreeSettings
pref=HandsFreeSettings(stage/'smoke-monitor.json');pref.write(False)
from tools.board_avatar_gtk import BoardAvatarStage,load_gtk
Gtk,_,_,_=load_gtk();original=Gtk.Window.show_all
def offscreen(window):
 window.set_accept_focus(False);window.set_focus_on_map(False);window.realize();window.get_window().set_override_redirect(True);window.move(-2500,-2500);original(window)
config=json.loads((root/'aura/config/board_avatar_gtk.json').read_text());config.update(audio_device='null',browser_port=0)
with patch('common.handsfree_settings.HandsFreeSettings',lambda unused:pref),patch.object(Gtk.Window,'show_all',offscreen),patch.object(BoardAvatarStage,'present_window',lambda self:False):
 print('SMOKE_INIT_START',flush=True)
 ui=BoardAvatarStage(root/'deliverables/2026-10-06_xilan_live',config,stage/('native-smoke-evidence-'+str(time.time_ns())),windowed=True,settings_file=stage/'smoke-ui-settings.json')
 print('SMOKE_INIT_READY',flush=True)
 start=time.monotonic();observations=[]
 def observe():
  try:
   s=ui.controller.public();sink=ui.native_video.read();observations.append({'at':time.monotonic(),'sink':sink,'renderer':s['avatar_renderer']})
   assert not s['handsfree_dialogue']['enabled'] and not s['handsfree_dialogue']['microphone_open']
   if time.monotonic()-start<25:return True
   report={'status':'NATIVE_GTK_SMOKE_PASS','window_offscreen':True,'microphone':False,'audio_device':'null','errors':ui.errors,'rows':observations,'sink':sink,'renderer':s['avatar_renderer'],'state':s['state']}
   assert sink['received']>=100,sink
   assert not ui.errors,ui.errors
   ui.close();assert pref.read() is False;print(json.dumps(report),flush=True);return False
  except BaseException as exc:
   print(json.dumps({"status":"SMOKE_FAILED","error":repr(exc),"ui_errors":ui.errors}),flush=True);ui.close();Gtk.main_quit();return False
 ui.GLib.timeout_add(500,observe);Gtk.main()
'''.replace('RUNTIME',repr(c['runtime']),1)
remote=r'''
import base64,json,os,subprocess
from pathlib import Path
stage=Path(STAGE);env=dict(os.environ,DISPLAY=':0',PYTHONDONTWRITEBYTECODE='1',PATH='/usr/sbin:/usr/bin:/sbin:/bin')
try:r=subprocess.run(['python3','-B','-c',base64.b64decode(JOB).decode()],env=env,capture_output=True,text=True,timeout=120)
except subprocess.TimeoutExpired as exc:
 r=type('Result',(),{'returncode':124,'stdout':str(exc.stdout),'stderr':str(exc.stderr)})()
result={'code':r.returncode,'out':r.stdout,'error':r.stderr};(stage/'native-smoke.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''.replace('STAGE',repr(c['stage']),1).replace('JOB',repr(base64.b64encode(job.encode()).decode()),1)
r=json.loads(ssh('python3 -B -',remote,timeout=210));(HERE/'stable_fps_smoke.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
if r['code']==0:
 v=json.loads(r['out'].strip().splitlines()[-1]);print(json.dumps({'code':0,'status':v['status'],'sink':v.get('sink'),'renderer':v.get('renderer'),'details':v if v['status']!='NATIVE_GTK_SMOKE_PASS' else None}))
else:print(json.dumps(r))
