"""Two public-data regressions of actual Editor methods, without Gtk or devices."""
import ast
import collections
import hashlib
import json
import math
from pathlib import Path
import threading

HERE=Path(__file__).resolve().parent
raw=(HERE/'face_zone_editor.py').read_bytes()


class Clock:
    def __init__(self,ms):self.ms=ms
    def monotonic(self):return self.ms/1000


class Loop:
    def __init__(self):self.next=1;self.sources={};self.removed=[]
    def add(self,kind,fn,args,delay=0):
        source=self.next;self.next+=1;self.sources[source]=(kind,fn,args,delay);return source
    def idle_add(self,fn,*args):return self.add('idle',fn,args)
    def timeout_add(self,delay,fn,*args):return self.add('timeout',fn,args,delay)
    def source_remove(self,source):self.removed.append(source);return self.sources.pop(source,None) is not None
    def dispatch(self,source):
        kind,fn,args,delay=self.sources.pop(source)
        assert fn(*args) is False


class Widget:
    def __init__(self,visible=False):self.visible=visible;self.text='';self.rectangle=None
    def show_all(self):self.visible=True
    def hide(self):self.visible=False
    def set_text(self,text):self.text=text
    def move(self,x,y):self.xy=(x,y)
    def resize(self,w,h):self.rectangle=(*self.xy,w,h)


class Gate:
    def __init__(self):self.revision=1;self.page='vision'
    def snapshot(self):return dict(revision=self.revision,page=self.page)
    def allows_overlay(self):return self.page=='vision'


class Channel:
    def __init__(self):self.gate=Gate();self.closed=False
    def close(self):self.closed=True


def setup(clock):
    loop=Loop();tree=ast.parse(raw)
    nodes=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('VIEW','CONTENT') for t in n.targets)]
    nodes += [n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('image_ratio','widget_ratio','face_position')]
    nodes += [n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Editor']
    scope=dict(math=math,threading=threading,time=clock,GLib=loop,collections=collections)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual-offline-editor-methods>','exec'),scope)
    editor=scope['Editor'].__new__(scope['Editor'])
    editor.closed=threading.Event();editor.condition=threading.Condition();editor.poll_wakeup=threading.Event()
    editor._display_lock=threading.Lock();editor._display_pending=None;editor._display_idle=None;editor._display_generation=0
    editor._face_expiry_source=None;editor._face_expiry_token=0
    editor.visibility_channel=Channel();editor.boot='public-test-boot'
    editor.left_camera_ratio=.05;editor.ratio=scope['widget_ratio'](.75);editor.target_center_ratio=.5
    editor.recenter_enabled=False;editor.active=False
    editor.line=Widget();editor.left_line=Widget();editor.center_line=Widget();editor.panel=Widget()
    editor.hint_window=Widget();editor.hint_label=Widget();editor.faces=[Widget() for _ in range(5)]
    editor.pending='original-save-queue-sentinel';editor.timer='original-save-debounce-sentinel'
    editor.command=lambda *_:(_ for _ in ()).throw(AssertionError('No axis command permitted'))
    editor.queue_save=lambda *_:(_ for _ in ()).throw(AssertionError('No settings save permitted'))
    return editor,loop,scope


def packet(stamp):
    return dict(state='READY',target_kind='face',board_boot_id='public-test-boot',camera_epoch='public-camera-epoch',
        source_frame_id=stamp,source_mono_ms=stamp,face_detection_mono_ms=stamp,mirror_horizontal=True,
        frame_width=640,frame_height=480,target=dict(box=[160,120,100,100],score=.95))


def queue(editor,scope,value,clock):
    face,hint,_=scope['face_position'](value,editor.boot,int(clock.monotonic()*1000),editor.left_camera_ratio,.75)
    assert face is not None
    preview=dict(frame_visible=True,frame_reference=dict(camera_epoch='public-camera-epoch',frame_id=value['source_frame_id']-2,captured_mono_ms=value['source_mono_ms']-80))
    editor.enqueue_display(True,face,hint,value,preview,editor.visibility_channel.gate.revision)


results=[]
clock=Clock(1050);editor,loop,scope=setup(clock);value=packet(1000)
queue(editor,scope,value,clock)
first_idle=editor._display_idle
queue(editor,scope,value,clock)
assert editor._display_idle==first_idle and len(loop.sources)==1, 'Only one pending latest-update slot'
for window in editor.faces:window.visible=True
clock.ms=1250;loop.dispatch(first_idle)
assert all(not window.visible for window in editor.faces)
assert editor.hint_label.text=='人脸位置：未确认'
assert editor._face_expiry_source is None
assert editor.pending=='original-save-queue-sentinel' and editor.timer=='original-save-debounce-sentinel'
results.append(dict(name='worker_valid_GUI_late_at_original250ms_boundary',passed=True,
    worker_age_ms=50,GUI_age_ms=250,five_faces_hidden=True,unconfirmed_hint=True,
    single_pending_display_callback=True,axis_and_settings_untouched=True))

clock=Clock(2050);editor,loop,scope=setup(clock)
queue(editor,scope,packet(2000),clock);loop.dispatch(editor._display_idle)
old_id=editor._face_expiry_source;_,old_fn,old_args,_=loop.sources[old_id]
clock.ms=2150;queue(editor,scope,packet(2100),clock);loop.dispatch(editor._display_idle)
new_id=editor._face_expiry_source
assert new_id!=old_id and all(window.visible for window in editor.faces)
clock.ms=2250
assert old_fn(*old_args) is False
assert editor._face_expiry_source==new_id and new_id in loop.sources
assert all(window.visible for window in editor.faces), 'Old timeout must not hide the newer face'
clock.ms=2350;loop.dispatch(new_id)
assert editor._face_expiry_source is None and all(not window.visible for window in editor.faces)
assert editor.hint_label.text=='人脸位置：未确认'
clock.ms=2450;queue(editor,scope,packet(2400),clock)
late_idle=editor._display_idle;_,late_fn,late_args,_=loop.sources[late_idle]
editor.close()
assert editor.closed.is_set() and editor.visibility_channel.closed and editor._display_idle is None
assert late_idle not in loop.sources and late_fn(*late_args) is False
assert all(not window.visible for window in editor.faces)
assert editor.pending=='original-save-queue-sentinel' and editor.timer=='original-save-debounce-sentinel'
results.append(dict(name='old_timeout_cannot_clear_new_face_or_timer_and_independent_expiry',passed=True,
    old_timer_deadline_ms=2250,new_timer_deadline_ms=2350,old_timer_preserves_new_timer_and_face=True,
    newer_face_expires_without_another_poll=True,close_cancels_pending_display_source=True,
    stale_callback_after_close_cannot_revive_face=True,axis_and_settings_untouched=True))

report=dict(schema='aura-editor-freshness-two-public-clock-queue-regressions-1',passed=True,
    candidate_sha256=hashlib.sha256(raw).hexdigest(),scenarios=results,
    actual_candidate_methods_executed=True,original_face_position_executed=True,
    synthetic_public_metadata_only=True,GTK_GStreamer_or_device_or_model_or_database_loaded=False,
    real_rendering_or_live_deployment_verified=False)
(HERE/'TWO_CLOCK_QUEUE_REGRESSIONS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
