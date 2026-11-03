"""Ephemeral per-request PCM handoff; visual evidence never gates speech."""
from contextlib import contextmanager
import threading
from common.asr_wire import context
from common.conversation_store import conversation_id

@contextmanager
def speaker_capture_scope(models,meta,pcm,cid,headers=(),*,deadline=None):
    tracker=getattr(models,'speaker_turns',None)
    if tracker is None or cid is None:
        yield;return
    meta=context(meta,pcm);cid=conversation_id(cid);visual=None
    if headers:
        try:
            if len(headers)!=1:raise ValueError('Duplicate visual evidence header')
            from common.speaker_visual import decode_visual_header
            visual=decode_visual_header(headers[0],meta)
        except (ValueError,TypeError,KeyError,UnicodeError):
            # No face is safer than an unbound face. The same valid speech
            # request and anonymous durable conversation still proceed.
            models.speaker_visual_invalid_headers=getattr(models,'speaker_visual_invalid_headers',0)+1
    holder=getattr(models,'speaker_capture_local',None)
    if holder is None:holder=threading.local();models.speaker_capture_local=holder
    prior=getattr(holder,'current',None)
    value=dict(meta=meta,cid=cid,pcm=pcm,visual=visual,deadline=deadline)
    pcm=None
    holder.current=value
    try:yield
    finally:
        value['pcm']=None
        holder.current=prior

def begin_speaker_turn(models,meta,cid):
    tracker=getattr(models,'speaker_turns',None)
    holder=getattr(models,'speaker_capture_local',None)
    value=getattr(holder,'current',None)
    if tracker is None or value is None:return False
    if value['meta']!=meta or value['cid']!=cid:raise ValueError('Speaker input belongs to a different conversation turn')
    if value['pcm'] is None:return False
    pcm=value['pcm'];value['pcm']=None
    return tracker.begin(meta,cid,pcm,visual=value['visual'],deadline=value['deadline'])

def cancel_speaker_turn(models,meta):
    tracker=getattr(models,'speaker_turns',None)
    if tracker is not None:return tracker.cancel(meta)
    return False
