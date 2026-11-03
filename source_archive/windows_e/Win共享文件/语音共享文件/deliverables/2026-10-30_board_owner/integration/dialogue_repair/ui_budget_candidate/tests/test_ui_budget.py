"""Visible repaint, expiry, invalidation and one-public-call audio consistency."""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('ui_budget_presentation',ROOT/'after/tools/production_memory_presentation.py')
presentation=importlib.util.module_from_spec(spec);spec.loader.exec_module(presentation)

class Widget:
    def __init__(self):self.text='';self.tooltip='';self.writes=0;self.tooltip_writes=0
    def set_text(self,text):self.text=text;self.writes+=1
    def get_text(self,*args):return self.text
    def set_tooltip_text(self,text):self.tooltip=text;self.tooltip_writes+=1
    def get_tooltip_text(self):return self.tooltip
    def get_bounds(self):return 0,len(self.text)

def make():
    clock=SimpleNamespace(now=10.)
    view=SimpleNamespace(buffer=Widget());view.get_buffer=lambda:view.buffer
    stage=SimpleNamespace(closed=False,transcript_label=Widget(),reply_view=view,reply=Widget(),runtime_view={})
    lifecycle=presentation.PresentationLifecycle(stage,SimpleNamespace(),clock=lambda:clock.now)
    owner=dict(board_boot_id='public-boot',session_id='public-session',generation=1,request_id='public-request')
    lifecycle.channel(dict(kind='start'),owner,clock.now)
    lifecycle.channel(dict(kind='transcript',text='公开问题'),owner,clock.now)
    lifecycle.channel(dict(kind='text',text='公开回答'),owner,clock.now)
    return lifecycle,stage,clock,owner

def test_identical_paint_keeps_text_without_rewriting_widgets():
    p,s,c,o=make();p.repaint()
    for _ in range(50):p.repaint()
    assert s.reply_view.buffer.writes==s.reply.writes==s.transcript_label.writes==1
    assert s.transcript_label.tooltip_writes==1
    assert s.reply_view.buffer.text=='公开回答' and len(p._painted)==4
    assert all(isinstance(item[1],bytes) and len(item[1])==32 for item in p._painted.values())

def test_changed_reply_is_painted_and_no_plaintext_is_added_to_cache():
    p,s,c,o=make();p.repaint();p.channel(dict(kind='text',text='第二句'),o,c.now);p.repaint()
    assert s.reply_view.buffer.writes==2 and s.reply_view.buffer.text=='公开回答第二句'
    assert all(not isinstance(v,str) for item in p._painted.values() for v in item)

def test_repainting_does_not_renew_ttl_and_expiry_clears_all_visible_reply():
    p,s,c,o=make();deadline=p.deadline;p.repaint();c.now+=200;p.repaint()
    assert p.deadline==deadline
    c.now=deadline;p.repaint()
    assert p.expirations==1 and not p.reply and not p.transcript
    assert s.reply_view.buffer.text==s.reply.text==s.reply_text==''
    assert s.transcript_label.text==s.transcript_label.tooltip=='等待你的声音…'

def test_invalidation_clears_even_if_old_content_is_unchanged():
    p,s,c,o=make();p.repaint();p.invalidate();p.repaint()
    assert s.reply_view.buffer.text==s.reply.text==s.reply_text==''
    assert p.current is None and p.invalidations==1
    p.channel(dict(kind='text',text='旧队列内容'),o,c.now);p.repaint()
    assert s.reply_view.buffer.text==''

def test_new_widget_receives_first_paint_even_with_same_content():
    p,s,c,o=make();p.repaint();s.reply_view.buffer=Widget();s.reply=Widget();p.repaint()
    assert s.reply_view.buffer.writes==s.reply.writes==1
    assert s.reply.text==s.reply_view.buffer.text=='公开回答'

def test_external_widget_overwrite_is_repaired_despite_matching_fingerprint():
    p,s,c,o=make();p.repaint();s.reply_view.buffer.text='外部旧内容';p.repaint()
    assert s.reply_view.buffer.text=='公开回答' and s.reply_view.buffer.writes==2
    p.invalidate();p.repaint();s.reply_view.buffer.text='外部旧内容';p.repaint()
    assert s.reply_view.buffer.text==''

def test_runtime_body_cleaning_still_runs_on_identical_repaint():
    p,s,c,o=make();p.repaint();s.runtime_view={'reply':'旧副本','child':{'text':'旧副本'},'n':2};p.repaint()
    assert s.runtime_view=={'reply':'','child':{'text':''},'n':2}

def test_failed_widget_read_forces_redraw():
    p,s,c,o=make();p.repaint()
    def fail(*args):raise RuntimeError('public fixture')
    s.reply_view.buffer.get_bounds=fail;p.repaint()
    assert s.reply_view.buffer.writes==2

def public_method():
    tree=ast.parse((ROOT/'after/tools/realtime_controller.py').read_text(encoding='utf-8'))
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='public')
    scope={};exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-public-method>','exec'),scope)
    return scope['public']

def public_owner(output):
    return SimpleNamespace(last_meta={},phase='IDLE',core=SimpleNamespace(fsm=SimpleNamespace(state=SimpleNamespace(label='IDLE'),rejected_count=0),talk_gen=1),
        reply='',output=output,pause_started=None,now=lambda:1.,last_error='',pending=None,last_job=None,log=[],turns=[],metrics={})

def test_audio_public_uses_one_explicit_read_for_both_metadata_fields():
    class Output:
        active=False;ready=True;duration=0.;reads=0
        def position(self):return 0.
        def read(self):
            self.reads+=1
            return {'device_state':'version-'+str(self.reads),'underrun_packets':self.reads,'private_extra':'omit'}
    out=Output();result=public_method()(public_owner(out))
    assert out.reads==1
    assert result['audio_output_state']==result['audio_output']['device_state']=='version-1'
    assert result['audio_output']['underrun_packets']==1 and 'private_extra' not in result['audio_output']

def test_audio_public_without_read_keeps_existing_fallback():
    out=SimpleNamespace(active=False,ready=True,duration=0.,position=lambda:0.)
    result=public_method()(public_owner(out))
    assert result['audio_output_state'] is None and result['audio_output']=={}
