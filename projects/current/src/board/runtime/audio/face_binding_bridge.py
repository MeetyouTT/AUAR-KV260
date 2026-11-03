"""Observe the original face FSM's real transactions without replacing it."""
from contextlib import contextmanager
import copy,threading
from common.asr_wire import context
from common.face_binding_wire import validate_binding_request
from common.voice_enrollment import confirmed,update_confirmed
from board.interaction.ui_contract import millis,validate_snapshot,validate_ack,identity_completion
from tools.enrollment_receipts import face_commit_payload,existing_face_payload

def _identity(snapshot):return snapshot['modules'].get('identity',{})

class FaceExchange:
    def __init__(self,meta,request,capture_snapshot,text,is_current,readback,clock):
        self.meta=context(meta);self.request=validate_binding_request(request,meta)
        self.capture=copy.deepcopy(capture_snapshot);self.text=text;self.current=is_current
        self.readback=readback;self.clock=clock;self.last_snapshot=None;self.committed=None;self.used=False

    def check(self):
        if not self.current():raise InterruptedError('Binding exchange is no longer current')

    def snapshot(self,value):
        self.check();value=validate_snapshot(value,self.meta['board_boot_id'],self.clock())
        if value['source_kind']!='actual':raise ValueError('Binding face source must be actual')
        self.last_snapshot=copy.deepcopy(value);return value

    def _guard(self,value,*,allow_recovered=False,command=None):
        self.check();s=validate_snapshot(value,self.meta['board_boot_id'],self.clock());i=_identity(s);g=self.request['face_guard']
        key=i.get('face_target');sample=i.get('enrollment_sampling',{})
        same_key=key==g['target']
        if allow_recovered and not same_key:
            # Only the original camera's accepted biometric sample binding may
            # recover a track. Never accept a geometry-only replacement.
            same_key=(sample.get('stage')=='ready' and sample.get('bound_target')==key and command is not None
                and command.get('params',{}).get('sampling_session_id')==sample.get('session_id'))
        if (s['source_kind']!='actual' or s['service_epoch']!=g['service_epoch'] or i.get('target_kind')!='face'
           or s['modules'].get('camera',{}).get('state')!='READY'
           or s.get('preview',{}).get('camera_epoch')!=g['camera_epoch']
           or i.get('face_count')!=1 or not key or key.get('camera_epoch')!=g['camera_epoch']
           or not same_key or i.get('db_version')!=g['gallery_revision']):raise ValueError('Original face binding owner changed')
        return s

    def observe_command(self,command,send,snapshot):
        self.check()
        if command.get('action')!='identity_enroll':return send(command)
        if not (confirmed(self.text) or update_confirmed(self.text)):
            raise ValueError('No original ASR confirmation for face enrollment')
        before=self.last_snapshot
        if before is None or (command.get('snapshot_sequence')!=before['sequence']
           or command.get('context')!=before['context']):raise ValueError('Enrollment command has no exact original snapshot')
        before=self._guard(before,allow_recovered=True,command=command)
        g=self.request['face_guard'];params=command.get('params',{})
        if (command.get('board_boot_id')!=self.meta['board_boot_id'] or command.get('service_epoch')!=g['service_epoch']
           or params.get('target')!=_identity(before).get('face_target') or params.get('confirmed') is not True
           or params.get('display_name')!=self.request['name']):raise ValueError('Original enrollment consent/target mismatch')
        ack=send(command)
        validate_ack(ack,command,self.clock())
        after=self.snapshot(snapshot())
        if identity_completion(dict(ack,action='identity_enroll'),_identity(after)):
            if after['service_epoch']!=before['service_epoch']:raise ValueError('Face service changed across commit')
            self.committed=(copy.deepcopy(command),copy.deepcopy(ack),copy.deepcopy(before),copy.deepcopy(after))
        return ack

    def receipt(self,reply,snapshot):
        self.check()
        if self.used or self.readback is None or self.request['attempt_id'].startswith('name-wait-'):return None
        r=self.request;g=r['face_guard'];code=reply.get('code')
        if code=='registered' and self.committed is not None:
            command,ack,before,after=self.committed
            # Metadata and fingerprints are taken from the real post-commit
            # gallery in one local read-only transaction.
            packet=self.readback.read(self.meta,after);gallery=dict(packet['gallery']);gallery.pop('source_kind')
            if gallery['revision']!=g['gallery_revision']+1:raise ValueError('Post-commit face gallery changed')
            gallery['revision']=g['gallery_revision']
            payload=face_commit_payload(attempt_id=r['attempt_id'],origin=r['origin_context'],commit=self.meta,
                face_guard=g,gallery=gallery,name=r['name'],command=command,ack=ack,
                before=_identity(before),after=_identity(after))
            found=[row for row in packet['inventory'] if row[0]==payload['identity_id']]
            if len(found)!=1:raise ValueError('Committed template is no longer present')
            payload['template_fingerprint']=found[0][1]
        elif code=='already_known' and r['confirmed_existing'] is True:
            if not (confirmed(self.text) or update_confirmed(self.text)):raise ValueError('No explicit same-turn existing-face link consent')
            start=self._guard(self.capture);latest=self._guard(snapshot())
            a,b=_identity(start),_identity(latest)
            if (a.get('state')!='KNOWN' or b.get('state')!='KNOWN' or a.get('person_id')!=g['face_identity_id']
               or b.get('person_id')!=g['face_identity_id'] or a.get('target')!=g['target'] or b.get('target')!=g['target']):
                raise ValueError('Original known face changed')
            # Both actual matching observations must still be within their
            # original face-result TTL. UI status freshness alone is not enough.
            now=self.clock()
            cfg=getattr(self.readback,'config',{})
            ttl=cfg.get('result_ttl_ms') if isinstance(cfg,dict) else None
            for value in (a,b):
                stamp=value.get('source_mono_ms')
                if (type(stamp) is not int or type(ttl) is not int or not 100<=ttl<=5000
                   or not 0<=now-stamp<ttl or type(value.get('source_frame_id')) is not int or value['source_frame_id']<1):
                    raise ValueError('Original KNOWN face result expired')
            packet=self.readback.read(self.meta,latest);gallery=dict(packet['gallery']);gallery.pop('source_kind')
            current=packet['current']
            if current is None or current['identity_id']!=g['face_identity_id']:raise ValueError('Known face template missing')
            payload=existing_face_payload(attempt_id=r['attempt_id'],origin=r['origin_context'],commit=self.meta,
                face_guard=g,gallery=gallery,name=r['name'],identity=b,confirmed_link=True,
                template_fingerprint=current['template_fingerprint'])
        else:return None
        self.check();self.used=True;return payload

class FaceBindingBridge:
    def __init__(self,snapshot,command,readback,*,clock=millis):
        self.original_snapshot=snapshot;self.original_command=command;self.readback=readback
        self.clock=clock;self.local=threading.local()

    def exchange(self,meta,request,capture_snapshot,text,is_current):
        return FaceExchange(meta,request,capture_snapshot,text,is_current,self.readback,self.clock)

    @contextmanager
    def scope(self,exchange):
        previous=getattr(self.local,'exchange',None);self.local.exchange=exchange
        try:yield exchange
        finally:self.local.exchange=previous

    def snapshot(self):
        value=self.original_snapshot();exchange=getattr(self.local,'exchange',None)
        return exchange.snapshot(value) if exchange is not None else value

    def command(self,command):
        exchange=getattr(self.local,'exchange',None)
        return (exchange.observe_command(command,self.original_command,self.original_snapshot)
            if exchange is not None else self.original_command(command))
