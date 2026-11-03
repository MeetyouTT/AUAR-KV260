"""Hidden GTK layout check; local-only rendering, ALSA null, no production stream."""
import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
job=r'''
import json,sys,time,uuid
from pathlib import Path
from unittest.mock import patch
root=Path(ROOT);stage=root.parent;sys.path.insert(0,str(root/'aura'))
from common.handsfree_settings import HandsFreeSettings
settings=HandsFreeSettings(stage/'smoke-preference.json');settings.write(False)
from tools.board_avatar_gtk import BoardAvatarStage,load_gtk
from tools.pan_controls import stage_type
from board.interaction.ui_services import UiServiceClient
class TestPan:
    def read(self):return {'state':'UNAVAILABLE','error':'TEST_ONLY_NO_HARDWARE','pulse_us':None,'minimum_us':1000,'maximum_us':2000,'left_sign':-1}
    def close(self):pass
    def stop(self):return {'ok':True}
BoardAvatarStage=stage_type(BoardAvatarStage,TestPan)
Gtk,_,_,_=load_gtk()
config=json.loads((root/'aura/config/board_avatar_gtk.json').read_text())
config.update(audio_device='null',browser_port=0,native_avatar=False)
config['portrait_offload']['enabled']=False
def offline_services(boot,values,**kwargs):return UiServiceClient(boot,dict(values,enabled=False),**kwargs)
with patch('common.handsfree_settings.HandsFreeSettings',lambda path:settings), \
     patch('board.interaction.ui_services.UiServiceClient',offline_services), \
     patch('common.profile_selection.read_selection',side_effect=FileNotFoundError), \
     patch.object(Gtk.Window,'show_all',lambda self:None), \
     patch.object(Gtk.Dialog,'run',lambda self:Gtk.ResponseType.CANCEL), \
     patch.object(BoardAvatarStage,'present_window',lambda self:False):
    ui=BoardAvatarStage(root/'deliverables/2026-10-06_xilan_live',config,
        stage/('full-smoke-evidence-'+uuid.uuid4().hex),windowed=True,settings_file=stage/'smoke-user-settings.json')
    passed=[]
    def finish():
        try:
            state=ui.controller.public()
            assert not state['handsfree_dialogue']['enabled'] and not state['handsfree_dialogue']['microphone_open']
            assert state['audio_output_state']=='IDLE_READY',state['audio_output_state']
            assert 'profile_dialog' in ui.controls and 'restore_settings' in ui.controls and 'portrait_toggle' in ui.controls
            assert state['portrait_offload']['mode']=='disabled',state['portrait_offload']
            page=ui.touch_layout['page'];rectangles=[]
            for name in ('volume_less','volume_more','mute','fullscreen','economy','portrait_toggle','profile_dialog','restore_settings'):
                button=ui.controls[name];parent=button.get_parent()
                x=parent.child_get_property(button,'x');y=parent.child_get_property(button,'y');w,h=button.get_size_request()
                assert x>=0 and y>=0 and x+w<=page['width'] and y+h<=page['height'],(name,x,y,w,h,page)
                for other,ox,oy,ow,oh in rectangles:
                    assert x+w<=ox or ox+ow<=x or y+h<=oy or oy+oh<=y,(name,other,'overlap')
                rectangles.append((name,x,y,w,h))
            before=ui.transcriber.profile_selection
            ui.controls['profile_dialog'].emit('clicked')
            assert ui.transcriber.profile_selection is before
            assert '已返回' in ui.toast,ui.toast
            assert 'pan_open' in ui.controls and ui.pan.read()['state']=='UNAVAILABLE'
            assert not ui.errors,ui.errors
            passed.append(True)
            print(json.dumps({'status':'FULL_GTK_LAYOUT_PASS','window_hidden':True,'native_video':False,
                  'audio_device':'null','microphone':False,'camera_requests':False,'physical_motion':False,
                  'profile_button_click_cancelled':True,'portrait_remote_connected':False,'button_bounds_verified':rectangles,'portrait_button_created':True,'audio_output_state':state['audio_output_state']}),flush=True)
        except Exception as exc:print('SMOKE_ERROR '+repr(exc),flush=True)
        finally:ui.close();Gtk.main_quit()
        return False
    ui.GLib.timeout_add(10000,finish);Gtk.main()
    assert passed and settings.read() is False
'''.replace('ROOT',repr(c['runtime']))
script=r'''
import base64,json,os,subprocess
from pathlib import Path
c=CANDIDATE;stage=Path(c['stage']);home=Path('/root/.local/share/aura/handsfree_dialogue.json')
before=home.read_bytes() if home.exists() else None
pid_before=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True)
result=subprocess.run(['python3','-B','-c',base64.b64decode(JOB).decode()],cwd=c['runtime'],
    env=dict(os.environ,DISPLAY=':0',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=95)
assert (home.read_bytes() if home.exists() else None)==before,'Production listening preference changed'
assert subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True)==pid_before
(stage/'full_gtk_layout.log').write_text(result.stdout+result.stderr)
value=dict(passed=result.returncode==0 and 'FULL_GTK_LAYOUT_PASS' in result.stdout,
    code=result.returncode,out=result.stdout[-7000:],error=result.stderr[-2000:],production_changed=False,
    native_video_created=False,microphone_used=False,physical_audio=False,physical_motion=False)
(stage/'full_gtk_layout.json').write_text(json.dumps(value,indent=2));print(json.dumps(value))
'''.replace('CANDIDATE',repr(c)).replace('JOB',repr(base64.b64encode(job.encode()).decode()))
value=json.loads(ssh('python3 -B -',script,timeout=110))
(HERE/'full_gtk_layout.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(value));raise SystemExit(0 if value['passed'] else 1)
