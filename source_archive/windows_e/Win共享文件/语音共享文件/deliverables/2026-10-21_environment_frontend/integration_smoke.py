"""Initialize hidden GTK with ALSA null, microphone paused, no second native video sink."""
import json,sys,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'integration_candidate.json').read_text(encoding='utf-8'))
remote=r'''
import json,os,subprocess,time
from pathlib import Path
c=CANDIDATE;stage=Path(c['stage']);root=Path(c['runtime'])
prefs=[Path('/home/root/.local/share/aura/handsfree_dialogue.json'),Path.home()/'.local/share/aura/handsfree_dialogue.json']
before={p:p.read_bytes() if p.exists() else None for p in prefs}
code=r"""
import json,sys,uuid
from pathlib import Path
from unittest.mock import patch
root=Path(ROOT);stage=Path(STAGE)
sys.path.insert(0,str(root/'aura'))
from common.handsfree_settings import HandsFreeSettings
settings=HandsFreeSettings(stage/'smoke-preference.json');settings.write(False)
from tools.board_avatar_gtk import BoardAvatarStage,load_gtk
from tools.pan_controls import stage_type
class TestPan:
 def read(self):return {'state':'UNAVAILABLE','error':'TEST_ONLY_NO_HARDWARE','pulse_us':None,'minimum_us':1000,'maximum_us':2000,'left_sign':-1}
 def close(self):pass
 def stop(self):return {'ok':True}
BoardAvatarStage=stage_type(BoardAvatarStage,TestPan)
Gtk,unused1,unused2,unused3=load_gtk()
config=json.loads((root/'aura/config/board_avatar_gtk.json').read_text());config.update(audio_device='null',browser_port=0,native_avatar=False)
original_show=Gtk.Window.show_all
def hidden(window):
 if not config.get('native_avatar'):return
 window.set_accept_focus(False);window.set_focus_on_map(False);window.realize()
 window.get_window().set_override_redirect(True);window.move(-2500,-2500);original_show(window)
with patch('common.handsfree_settings.HandsFreeSettings',lambda unused:settings), \
     patch.object(Gtk.Window,'show_all',hidden), \
     patch.object(BoardAvatarStage,'present_window',lambda self:False):
 ui=BoardAvatarStage(root/'deliverables/2026-10-06_xilan_live',config,stage/('smoke-evidence-'+uuid.uuid4().hex[:8]),windowed=True,settings_file=stage/'smoke-ui-settings.json')
 passed=[]
 def finish():
  try:
   state=ui.controller.public();assert not state['handsfree_dialogue']['enabled']
   assert not state['handsfree_dialogue']['microphone_open']
   assert state['audio_output_state']=='IDLE_READY',state['audio_output_state']
   assert Path(sys.modules['common'].__file__).resolve().is_relative_to(root)
   assert type(ui.controller.controller).__name__=='BargeInRecordingController'
   assert ui.controller.controller.early_listen and state['handsfree_dialogue']['listening_timing']['enabled']
   assert 'pan_open' in ui.controls and ui.pan.read()['state']=='UNAVAILABLE'
   for module in ('tools.barge_in_recording','tools.barge_in_capture','board.runtime.audio.echo_cancel','board.runtime.audio.barge_verify'):
    assert Path(sys.modules[module].__file__).resolve().is_relative_to(root),module
   if config.get('native_avatar'):assert ui.native_video.read()['received']>0
   assert state['audio_frontend']['enabled'] is True
   assert not ui.errors,ui.errors
   passed.append(True)
  except Exception as exc:print('SMOKE_ERROR '+type(exc).__name__+': '+str(exc),flush=True)
  finally:ui.close();ui.Gtk.main_quit()
  return False
 ui.GLib.timeout_add(5000,finish);ui.Gtk.main()
 assert passed and settings.read() is False
 print(json.dumps({'status':'FULL_GTK_SMOKE_PASS','window_hidden':True,'audio_device':'null','microphone_opened':False,'native_video':bool(config.get('native_avatar')),'early_listen':True,'pan_factory':'TEST_ONLY_NO_HARDWARE'}),flush=True)
""".replace('ROOT',repr(str(root)),1).replace('STAGE',repr(str(stage)),1)
run=subprocess.run(['python3','-B','-c',code],cwd=root,env=dict(os.environ,DISPLAY=':0',PYTHONPATH=str(root/'aura'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=180)
assert all((p.read_bytes() if p.exists() else None)==raw for p,raw in before.items()),'Actual monitor preference changed'
(stage/'smoke.log').write_text(run.stdout+run.stderr)
print(json.dumps({'runtime':str(root),'passed':run.returncode==0 and 'FULL_GTK_SMOKE_PASS' in run.stdout,'returncode':run.returncode,'output':run.stdout+run.stderr}))
'''.replace('CANDIDATE',repr(c),1)
r=json.loads(ssh('python3 -B -',remote,timeout=210))
(HERE/'integration_smoke.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print(json.dumps(r));assert r['passed']
