"""Exercise actual GTK tick and optimized render worker, hidden and silent."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'performance_candidate.json').read_text())
job=r'''
import json,sys,time
from pathlib import Path
from unittest.mock import patch
root=Path(RUNTIME);stage=root.parent;sys.path.insert(0,str(root/'aura'))
from common.handsfree_settings import HandsFreeSettings
settings=HandsFreeSettings(stage/'smoke-preference.json');settings.write(False)
from tools.board_avatar_gtk import BoardAvatarStage,load_gtk
Gtk,_,_,_=load_gtk()
config=json.loads((root/'aura/config/board_avatar_gtk.json').read_text());config.update(audio_device='null',browser_port=0)
with patch('common.handsfree_settings.HandsFreeSettings',lambda unused:settings),patch.object(Gtk.Window,'show_all',lambda self:None),patch.object(BoardAvatarStage,'present_window',lambda self:False):
 ui=BoardAvatarStage(root/'deliverables/2026-10-06_xilan_live',config,stage/'smoke-evidence',windowed=True,settings_file=stage/'smoke-ui-settings.json')
 deadline=time.monotonic()+15
 def finish():
  if ui.controller.read()['sequence']<35 and time.monotonic()<deadline:return True
  s=ui.controller.public();assert not s['handsfree_dialogue']['enabled'] and not s['handsfree_dialogue']['microphone_open']
  assert s['audio_output_state']=='IDLE_READY',s.get('audio_output_state')
  assert Path(sys.modules['common'].__file__).resolve().is_relative_to(root)
  assert ui.displayed_frames>1,(ui.errors,ui.displayed_frames)
  report={'status':'HIDDEN_GTK_PASS','microphone_opened':False,'audio_device':'null','errors':ui.errors,
          'displayed_frames':ui.displayed_frames,'renderer':s['avatar_renderer']}
  ui.close();assert not ui.errors;print(json.dumps(report),flush=True);return False
 ui.GLib.timeout_add(500,finish);Gtk.main()
'''.replace('RUNTIME',repr(c['runtime']))
remote=r'''
import base64,json,os,subprocess
from pathlib import Path
stage=Path(STAGE);env=dict(os.environ,DISPLAY=':0',PATH='/usr/sbin:/usr/bin:/sbin:/bin',PYTHONDONTWRITEBYTECODE='1')
job=base64.b64decode(JOB).decode()
r=subprocess.run(['python3','-B','-c',job],env=env,capture_output=True,text=True,timeout=150)
report={'code':r.returncode,'output':r.stdout,'error':r.stderr}
(stage/'smoke.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
'''
import base64
remote=remote.replace('STAGE',repr(c['stage']),1).replace('JOB',repr(base64.b64encode(job.encode()).decode()),1)
r=json.loads(ssh('python3 -B -',remote,timeout=170))
(HERE/'performance_smoke.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
assert r['code']==0
