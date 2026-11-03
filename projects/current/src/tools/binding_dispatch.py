"""Exact typed requests accepted only by the Hub's loopback model adapter."""
import base64
from common.asr_wire import context

def dispatch(runtime,path,value):
    if not isinstance(value,dict):raise ValueError('Binding request must be an object')
    if path=='/v1/binding/state':
        if set(value)!={'context'}:raise ValueError('Unexpected binding state fields')
        return runtime.state(value['context'])
    if path=='/v1/binding/route':
        if set(value)!={'context','text','pcm','visual','gallery_digest'}:raise ValueError('Unexpected binding route fields')
        pcm=base64.b64decode(value['pcm'],validate=True)
        try:return runtime.route(value['context'],value['text'],pcm,visual=value['visual'],gallery_digest=value['gallery_digest'])
        finally:pcm=None;value['pcm']=None
    if path=='/v1/binding/open':
        if set(value)!={'context','attempt_id','token','timeout'}:raise ValueError('Unexpected binding open fields')
        return runtime.open_exchange(value['context'],value['attempt_id'],value['token'],value['timeout'])
    if path=='/v1/binding/face-result':
        if set(value)!={'context','attempt_id','token','capability','pcm','reply','binding_receipt','final'}:raise ValueError('Unexpected binding completion fields')
        pcm=base64.b64decode(value['pcm'],validate=True)
        try:return runtime.face_result(value['context'],pcm,value['attempt_id'],value['token'],value['capability'],value['reply'],binding_receipt=value['binding_receipt'],final=value['final'])
        finally:pcm=None;value['pcm']=None
    if path=='/v1/binding/gallery':
        if set(value)!={'context','packet'} or value['context']!=value['packet'].get('context'):raise ValueError('Unexpected gallery packet fields')
        context(value['context']);return runtime.ingest_gallery(value['packet'])
    raise ValueError('Unknown typed binding route')
