"""Headless behavior checks using real v18/candidate refresh and tick methods."""
from collections import defaultdict
import copy
import importlib.util
import json
from pathlib import Path
import queue
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


HERE=Path(__file__).resolve().parent
RUNTIME=HERE.parent/'runtime_v16'
sys.path.insert(0,str(RUNTIME))


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


BEFORE=load('baseline_gtk',HERE/'before/aura/tools/board_avatar_gtk.py')
AFTER=load('candidate_gtk',HERE/'candidate/aura/tools/board_avatar_gtk.py')
DISPLAY=load('candidate_display',HERE/'candidate/aura/tools/x11_display_activity.py')


class Style:
    def __init__(self):self.values=set()
    def has_class(self,value):return value in self.values
    def add_class(self,value):self.values.add(value)
    def remove_class(self,value):self.values.discard(value)


class Widget:
    def __init__(self):
        self.values=dict(text='',label='',sensitive=True,visible=True,tooltip_text=None,value=0)
        self.writes=0;self.style=Style()
    def get_style_context(self):return self.style
    def get_buffer(self):return self
    def __getattr__(self,name):
        if name.startswith('get_'):
            return lambda:self.values[name[4:]]
        if name.startswith('set_'):
            def assign(value):
                self.values[name[4:]]=value;self.writes+=1
            return assign
        raise AttributeError(name)


def state_for(phase='IDLE',paused=False,task='IDLE'):
    return dict(phase=phase,paused=paused,playing=phase=='SPEAKING',error='',reply='',
        portrait_offload=dict(mode='native_yuki_egl'),avatar_command_pending=0,
        local_recording=dict(state='IDLE',can_start=True,can_stop=False),
        local_transcription=dict(state=task,service=dict(conversation=True,streaming=True)),
        automatic_conversation=dict(enabled=True,state='LISTENING',can_stop=True,can_start=False),
        handsfree_dialogue=dict(enabled=True,state='WAITING_SPEECH'),
        visual_time=1.,state='IDLE',asset='public',index=0,speech_gain=0.,mouth_level=0.,
        blink_active=False,audio_time=0.)


class FakeStage:
    def __init__(self,module):
        self.module=module;self.widgets={}
        for name in ('controls','insight_labels','device_cards'):
            setattr(self,name,defaultdict(Widget))
        self.config=dict(automatic_turns=True)
        self.preferences=dict(fullscreen=False,economy=False)
        self.native_yuki=SimpleNamespace(ready=True)
        self.last_touch_scan=time.monotonic();self.touch_inputs=[]
        self.device_inventory=dict(camera_present=False,lan=None)
        self.volume_dragging=False;self.updating_volume=False
        self.page='main';self.ui_layer='presentation';self.page_names=['main']
        self.production_presentation=object();self.large_preview=None
        self.toast='';self.toast_until=0.;self.reply_text='';self.last_service_result=None
        self.connection_store=SimpleNamespace(error='')
        self.mixer=SimpleNamespace(read=lambda:dict(pending=False,available=True,volume=70,muted=False,error=''))
        self.services=SimpleNamespace(read=lambda:dict(snapshot=None,link='DISABLED',error='',results=[],pending_count=0,connection={}))
        self.preview_output=SimpleNamespace(read=lambda _:dict(frame_visible=False,frame_reference=None),
            placeholder_visible=lambda value,_:not value['frame_visible'])
        self.display_activity=SimpleNamespace(tick=lambda _:None)
        self.refresh_voice_face_dialog=lambda _:None
        self.lines=[];self.board_business=None
        self.refresh_settings=lambda state:module.BoardAvatarStage.refresh_settings(self,state)
        self.refresh_runtime=lambda state,text:module.BoardAvatarStage.refresh_runtime(self,state,text)
        if module is AFTER:self._ui_set=lambda *args:module.BoardAvatarStage._ui_set(self,*args)
    def __getattr__(self,name):
        if name.startswith('_') or name in ('ui_callback_previous','runtime_faults'):
            raise AttributeError(name)
        if name not in self.widgets:self.widgets[name]=Widget()
        return self.widgets[name]
    def snapshot(self):
        value={key:copy.deepcopy(widget.values) for key,widget in self.widgets.items()}
        for field in ('controls','insight_labels','device_cards'):
            value[field]={key:copy.deepcopy(widget.values) for key,widget in getattr(self,field).items()}
        return value
    def writes(self):
        return sum(widget.writes for widget in self.widgets.values())+sum(
            widget.writes for field in ('controls','insight_labels','device_cards')
            for widget in getattr(self,field).values())


def render(stage,state):
    text=stage.refresh_settings(state);stage.refresh_runtime(state,text)


def tick_stage():
    stage=FakeStage(AFTER)
    stage.closed=False;stage.last_tick=None;stage.last_runtime_refresh=0.
    stage.diagnostic_result=None;stage.native_video=None;stage.character_pair=None
    stage.last_avatar_sequence=0;stage.displayed_frames=0
    stage.character='public';stage.samples=[];stage.errors=[];stage.diagnostic_job=None
    stage.production_presentation=None
    stage.state=state_for()
    stage.controller=SimpleNamespace(read=lambda:dict(state=copy.deepcopy(stage.state),jpeg=b'',
        rgb=None,image=None,sequence=0),cancel=MagicMock())
    stage.bridge=SimpleNamespace(commands=queue.Queue())
    stage.bridge.publish=lambda state,frame:setattr(stage,'published',copy.deepcopy(state))
    def command(data):
        if data['type']=='pause':
            stage.state.update(phase='SPEAKING',paused=True,playing=False)
        elif data['type']=='cancel':
            stage.state.update(phase='IDLE',paused=False,playing=False)
            stage.state['local_transcription']['state']='CANCELLED'
        return dict(ok=True)
    stage.command=command
    return stage


class WidgetTests(unittest.TestCase):
    def test_final_widgets_match_v18_through_all_control_states(self):
        old,new=FakeStage(BEFORE),FakeStage(AFTER)
        for phase,paused,task in (('IDLE',False,'IDLE'),('THINKING',False,'GENERATING'),
                ('SPEAKING',False,'PLAYING'),('SPEAKING',True,'PLAYING'),
                ('IDLE',False,'CANCELLED'),('IDLE',False,'ERROR')):
            with self.subTest(phase=phase,paused=paused,task=task):
                render(old,state_for(phase,paused,task));render(new,state_for(phase,paused,task))
                self.assertEqual(old.snapshot(),new.snapshot())

    def test_repeated_refresh_removes_most_gtk_mutations(self):
        old,new=FakeStage(BEFORE),FakeStage(AFTER)
        render(old,state_for());render(new,state_for())
        before_old,before_new=old.writes(),new.writes()
        for _ in range(10):render(old,state_for());render(new,state_for())
        old_delta,new_delta=old.writes()-before_old,new.writes()-before_new
        self.assertLess(new_delta,old_delta*.25)
        self.assertGreater(new._ui_widget_writes['skipped'],35)
        self.write_counts=dict(baseline=old_delta,candidate=new_delta)

    def test_guard_checks_widget_value_without_retaining_text(self):
        stage=FakeStage(AFTER);widget=Widget()
        for method,value in (('set_text','SYNTHETIC_BODY'),('set_label','Pause'),
                ('set_sensitive',False),('set_visible',False),('set_tooltip_text','Hint'),('set_value',70)):
            self.assertTrue(stage._ui_set(widget,method,value))
            self.assertFalse(stage._ui_set(widget,method,value))
        self.assertEqual(dict(applied=6,skipped=6),stage._ui_widget_writes)
        self.assertNotIn('SYNTHETIC_BODY',repr(stage._ui_widget_writes))

    def test_pause_command_reflects_in_same_refresh(self):
        stage=tick_stage();request=dict(data=dict(type='pause'),deadline=time.monotonic()+3,done=threading.Event())
        stage.bridge.commands.put_nowait(request)
        self.assertTrue(AFTER.BoardAvatarStage.tick(stage))
        self.assertTrue(request['done'].is_set());self.assertTrue(request['result']['ok'])
        self.assertTrue(stage.published['paused'])
        self.assertEqual('继续',stage.pause_button.values['label'])

    def test_cancel_command_reflects_in_same_refresh(self):
        stage=tick_stage();stage.state=state_for('SPEAKING',False,'PLAYING')
        request=dict(data=dict(type='cancel'),deadline=time.monotonic()+3,done=threading.Event())
        stage.bridge.commands.put_nowait(request)
        self.assertTrue(AFTER.BoardAvatarStage.tick(stage))
        self.assertTrue(request['done'].is_set());self.assertTrue(request['result']['ok'])
        self.assertEqual('IDLE',stage.published['phase']);self.assertFalse(stage.published['playing'])
        self.assertFalse(stage.cancel_button.values['sensitive'])

    def test_error_is_displayed_and_cancellation_preserved(self):
        stage=tick_stage()
        def fail():raise ValueError('SYNTHETIC_PRIVATE_ERROR_DO_NOT_EXPORT')
        stage.controller.read=fail
        self.assertTrue(AFTER.BoardAvatarStage.tick(stage))
        self.assertEqual('ValueError',stage.status.values['text'])
        stage.controller.cancel.assert_called_once()
        self.assertNotIn('SYNTHETIC_PRIVATE_ERROR',json.dumps(stage.runtime_faults))

    def test_completed_callback_meter_includes_publish_wait(self):
        stage=tick_stage();original=stage.bridge.publish
        def slow_publish(state,frame):time.sleep(.03);original(state,frame)
        stage.bridge.publish=slow_publish
        AFTER.BoardAvatarStage.tick(stage)
        self.assertGreaterEqual(stage.ui_callback_previous['publish_ms'],25)
        self.assertGreaterEqual(stage.ui_callback_previous['wall_ms'],stage.ui_callback_previous['publish_ms'])
        stage.last_runtime_refresh=0.
        AFTER.BoardAvatarStage.tick(stage)
        self.assertGreaterEqual(stage.published['ui_callback_previous']['publish_ms'],25)
        self.assertEqual(1,stage.published['ui_callback_previous']['sequence'])


class DisplayTests(unittest.TestCase):
    def tearDown(self):DISPLAY._display_libraries.cache_clear()

    def test_existing_five_second_activity_and_pause_policy(self):
        now=[10.];calls=[];display=DISPLAY.DisplayActivity(wake=lambda:calls.append(now[0]),clock=lambda:now[0])
        display.tick(False);self.assertEqual([],calls)
        display.tick(True);display.tick(True);self.assertEqual([10.],calls)
        now[0]=14.9;display.tick(True);self.assertEqual(1,len(calls))
        now[0]=15.;display.tick(True);self.assertEqual(2,len(calls))
        display.tick(False);now[0]=15.1;display.tick(True);self.assertEqual(3,len(calls))

    def test_wake_error_is_retried_at_existing_cadence(self):
        now=[10.];wake=MagicMock(side_effect=[OSError('display unavailable'),None])
        display=DISPLAY.DisplayActivity(wake=wake,clock=lambda:now[0]);display.tick(True)
        self.assertTrue(display.error);display.tick(True);self.assertEqual(1,wake.call_count)
        now[0]=15.;display.tick(True);self.assertEqual('',display.error);self.assertEqual(2,wake.call_count)

    def test_library_discovery_occurs_before_any_display_open(self):
        x,ext=MagicMock(),MagicMock();x.XOpenDisplay.return_value=1;ext.DPMSCapable.return_value=0
        with patch.object(DISPLAY.ctypes.util,'find_library',side_effect=['X11-test','Xext-test']) as find, \
                patch.object(DISPLAY.C,'CDLL',side_effect=[x,ext]) as cdll:
            DISPLAY._display_libraries.cache_clear()
            now=[0.];display=DISPLAY.DisplayActivity(clock=lambda:now[0])
            self.assertEqual(2,find.call_count);self.assertEqual(2,cdll.call_count)
            x.XOpenDisplay.assert_not_called()
            for index in range(6):now[0]=index*5.;display.tick(True)
            self.assertEqual(2,find.call_count);self.assertEqual(2,cdll.call_count)
            self.assertEqual(6,x.XOpenDisplay.call_count);self.assertEqual(6,x.XCloseDisplay.call_count)
            self.assertEqual(6,x.XResetScreenSaver.call_count)


if __name__=='__main__':unittest.main(verbosity=2)
