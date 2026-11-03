"""Concrete ModelHost adapter; call before the legacy device command.

The only PCM copy owned by an exchange lives in a mutable holder cleared by its
normal cancel/final path. The original native call may own an argument until it
returns. No PCM or receipt key is serialized into metadata/history/logs.
"""
import base64,http.client,time,json
from common.asr_wire import context
from common.binding_api import decode_gallery_header,response
from common.binding_intent import binding_intent
from tools.binding_identity_stream import BindingIdentityReplyStream

def default_call(path,value,*,timeout):
    from tools.device_client import call
    return call(path,value,timeout=timeout)

class BoundIdentityExchange(BindingIdentityReplyStream):
    def __init__(self,meta,transform,holder,timeout):
        self.pcm_holder=holder
        super().__init__(meta,transform,timeout=timeout)
    def cancel(self):
        self.pcm_holder['pcm']=None
        super().cancel()
    def __iter__(self):
        try:yield from super().__iter__()
        finally:self.pcm_holder['pcm']=None

class BindingModelAdapter:
    def __init__(self,*,call=default_call):self.call=call
    def accept_gallery(self,body,*,timeout=.3):
        from common.face_binding_wire import validate_packet,packet_sha256
        if not isinstance(body,dict) or set(body)!={'context','packet'}:raise ValueError('Invalid gallery body')
        packet=validate_packet(body['packet'],body['context'])
        if len(json.dumps(body,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())>24576:raise ValueError('Gallery body exceeds route bound')
        value=self.call('/v1/binding/gallery',dict(context=context(body['context']),packet=packet),timeout=timeout)
        if value!={'accepted':True,'packet_sha256':packet_sha256(packet)}:raise ValueError('Gallery not accepted by same owner')
        return value
    def before_device(self,meta,text,pcm,*,visual=None,gallery_headers=(),timeout=12):
        context(meta,pcm);digest=None
        try:
            if len(gallery_headers)>1:raise ValueError('Duplicate face gallery header')
            if gallery_headers:
                header=decode_gallery_header(gallery_headers[0],meta,visual);digest=header['packet_sha256']
            value=self.call('/v1/binding/route',dict(context=meta,text=text,pcm=base64.b64encode(pcm).decode('ascii'),
              visual=visual,gallery_digest=digest),timeout=min(12,timeout))
            return response(value,meta)
        except (OSError,ValueError,TypeError,KeyError,TimeoutError,http.client.HTTPException):
            # An unavailable device cannot block ordinary conversation. Explicit
            # enrollment remains uncommitted and says so rather than falling
            # into the old mutually exclusive enrollment path.
            from tools.unified_identity_binding import UnifiedBindingRouter
            controlled=binding_intent(text)['kind']=='remember_self'
            routed=UnifiedBindingRouter.decision('device_reply' if controlled else 'ordinary_skip_speaker',
              reply='身份关联服务暂不可用，这次没有确认保存；普通聊天仍可继续。' if controlled else None,reason='BINDING_UNAVAILABLE')
            return response(dict(version=1,context=meta,decision=routed,binding_request=None,analysis_mode='TRACKER'),meta)
    def open_exchange(self,meta,pcm,routed,*,timeout):
        context(meta,pcm);routed=response(routed,meta)
        if routed['decision']['route']!='face_exchange':raise ValueError('No face exchange requested')
        holder={'pcm':pcm};attempt=routed['decision']['attempt_id'];access={}
        def transform(value,receipt):
            raw=holder['pcm']
            if raw is None:raise InterruptedError('Identity exchange input was released')
            final=value['code'] not in ('sample_front','sample_left','sample_right','sample_validate','sample_auto')
            result=self.call('/v1/binding/face-result',dict(context=meta,attempt_id=attempt,token=access['token'],capability=access['capability'],
              pcm=base64.b64encode(raw).decode('ascii'),reply=value,binding_receipt=receipt,final=final),timeout=min(12,max(.05,access['until']-time.monotonic())))
            if (not isinstance(result,dict) or set(result)!={'version','context','reply','personal_memory_allowed'} or result['version']!=1
               or result['context']!=meta or result['personal_memory_allowed'] is not False):raise ValueError('Foreign binding face result')
            return result['reply']
        exchange=BoundIdentityExchange(meta,transform,holder,min(110,timeout));access['token']=exchange.token;access['until']=exchange.until
        try:
            opened=self.call('/v1/binding/open',dict(context=meta,attempt_id=attempt,token=exchange.token,timeout=min(110,timeout)),timeout=min(1,timeout))
            if (not isinstance(opened,dict) or set(opened)!={'version','context','capability'} or opened['version']!=1
                or opened['context']!=meta or not isinstance(opened['capability'],str) or len(opened['capability'])!=64):raise ValueError('Invalid scoped binding capability')
            access['capability']=opened['capability'];exchange.binding_request=routed['binding_request']
            return exchange
        except Exception:exchange.cancel();raise

def install_model_adapter(models):
    adapter=getattr(models,'binding_adapter',None)
    if adapter is None:adapter=BindingModelAdapter();models.binding_adapter=adapter
    return adapter

def before_legacy_device(models,meta,text,pcm,*,visual=None,gallery_headers=(),timeout=12):
    """Parent's ModelHandler hook returns both final device reply and route."""
    routed=install_model_adapter(models).before_device(meta,text,pcm,visual=visual,gallery_headers=gallery_headers,timeout=timeout)
    if routed['decision']['skip_legacy_device_command']:reply=routed['decision']['reply']
    else:
        from tools.device_client import command
        reply=command(meta,text,pcm)
    return reply,routed

def captured_visual(headers,meta):
    """Same exact optional capture evidence; invalid vision never gates audio."""
    values=headers.get_all('X-Aura-Speaker-Visual',[])
    if not values:return None
    try:
        if len(values)!=1:raise ValueError('Duplicate captured visual header')
        from common.speaker_visual import decode_visual_header
        return decode_visual_header(values[0],meta)
    except (ValueError,TypeError,KeyError,UnicodeError):return None

def prepare_channel(models,meta,text,pcm,headers,*,timeout):
    """Concrete one-call ModelHandler hook; call while original PCM is owned."""
    reply,routed=before_legacy_device(models,meta,text,pcm,visual=captured_visual(headers,meta),
      gallery_headers=headers.get_all('X-Aura-Face-Gallery',[]),timeout=timeout)
    exchange=None
    if routed['decision']['route']=='face_exchange':
        exchange=install_model_adapter(models).open_exchange(meta,pcm,routed,timeout=timeout)
        with models.meta_lock:
            rows=getattr(models,'identity_exchanges',None)
            if rows is None:rows={};models.identity_exchanges=rows
            for key,value in list(rows.items()):
                if time.monotonic()>=value.until or value.cancelled.is_set():rows.pop(key,None)
            while len(rows)>=8:rows.pop(next(iter(rows))).cancel()
            old=rows.get(meta['request_id'])
            if old is not None:old.cancel()
            rows[meta['request_id']]=exchange
    return reply,exchange,routed

def accept_model_result(models,value):
    """Replace ModelHost.accept_identity_result body; old result shape retained."""
    allowed=({'context','token','reply'},{'context','token','reply','sequence','final'},
      {'context','token','reply','sequence','final','binding_receipt'})
    if not isinstance(value,dict) or set(value) not in allowed:raise ValueError('Invalid identity result')
    if len(json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())>4096:raise ValueError('Identity result exceeds original bound')
    meta=context(value['context']);actor=(meta['board_boot_id'],meta['session_id'])
    with models.meta_lock:
        exchange=getattr(models,'identity_exchanges',{}).get(meta['request_id'])
        if exchange is None or models.latest_generations.get(actor)!=meta['generation']:raise ValueError('Stale identity result')
        options=dict(sequence=value.get('sequence',0),final=value.get('final',True))
        if isinstance(exchange,BoundIdentityExchange):options['binding_receipt']=value.get('binding_receipt')
        elif 'binding_receipt' in value:raise ValueError('Receipt cannot enter a non-binding identity flow')
        exchange.accept(meta,value['token'],value['reply'],**options)
    return {'accepted':True}

def accept_model_gallery(models,value,*,timeout=.3):
    """ModelHandler /v1/voice/identity/gallery forwarding hook."""
    return install_model_adapter(models).accept_gallery(value,timeout=timeout)
