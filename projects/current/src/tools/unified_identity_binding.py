"""One user enrollment intent, original face then original voice workflow.

Router decisions must be evaluated before device_client.command. In particular
face_exchange returns no device_reply, so it cannot suppress IdentityReplyStream.
"""
import copy,json,uuid
from common.asr_wire import context
from common.identity_links import binding_intent,_guard

class UnifiedBindingRouter:
    def __init__(self,registry,speaker_bridge,*,voice_gallery,face_gallery):
        self.registry=registry;self.speaker=speaker_bridge
        self.voice_gallery=voice_gallery;self.face_gallery=face_gallery;self.active={};self.name_waiting={}
    @staticmethod
    def actor(meta):return meta['board_boot_id'],meta['session_id']
    @staticmethod
    def decision(route,*,reply=None,attempt_id=None,board_text=None,reason=None):
        return dict(route=route,reply=reply,attempt_id=attempt_id,board_text=board_text,reason=reason,
          skip_legacy_device_command=route!='ordinary',unified_saved=False,personal_memory_allowed=False)
    def route(self,meta,text,pcm,*,visual=None,anonymous=None):
        context(meta,pcm);actor=self.actor(meta);intent=binding_intent(text);attempt=self.active.get(actor);raw_text=text;name_followup=False
        now=self.registry.clock()
        self.name_waiting={key:value for key,value in self.name_waiting.items() if now<value['expires']}
        if attempt is None:
            waiting=self.name_waiting.get(actor)
            if waiting is not None and text.strip(' 。！!？?') in ('取消','取消登记','取消身份关联','不保存'):
                waiting['cancel_context']=dict(meta)
                return self.decision('face_exchange',attempt_id=waiting['ticket'],board_text='取消登记',reason='NAME_REQUEST_CANCELLED')
            if intent['kind']=='name_hint':
                waiting=self.name_waiting.pop(actor,None)
                if waiting is None:return self.decision('ordinary',reason='SELF_NAME_HINT_NOT_ENROLLMENT_CONSENT')
                try:same=_guard(visual,meta)==waiting['face_guard']
                except (ValueError,TypeError,KeyError):same=False
                if not same:
                    return self.decision('ordinary_skip_speaker',reason='NAME_FOLLOWUP_FACE_CHANGED')
                # A previous explicit remember-self request arms exactly this
                # short same-face exchange; the original final confirmation is
                # still required before either store may be written.
                text='记住我，我叫'+intent['name'];intent=binding_intent(text)
                name_followup=waiting['face_guard']['face_identity_id'] is None
            if intent['kind']!='remember_self':return self.decision('ordinary')
            if intent['name'] is None:
                try:guard=_guard(visual,meta)
                except (ValueError,TypeError,KeyError):guard=None
                if guard is not None:
                    if len(self.name_waiting)>=4:self.name_waiting.pop(next(iter(self.name_waiting)))
                    ticket='name-wait-'+uuid.uuid4().hex
                    self.name_waiting[actor]={'face_guard':guard,'context':dict(meta),'expires':now+120,'ticket':ticket}
                    return self.decision('face_exchange',attempt_id=ticket,board_text='帮我登记身份',reason='NAME_REQUIRED')
                return self.decision('device_reply',reply='统一关联时需要一张清晰人脸。请一个人正对镜头，再说“记住我，我叫某某”；普通聊天可以继续。',reason='NAME_AND_FACE_REQUIRED')
            try:
                start=self.registry.start(meta,text,visual=visual,anonymous=anonymous,
                  face_gallery=self.face_gallery(),voice_gallery=self.voice_gallery())
            except (ValueError,TimeoutError):
                return self.decision('device_reply',reply='身份关联还没有开始。请一个人正对镜头；若称呼已经登记，请先明确选择原身份。',reason='BINDING_PRECONDITION_UNAVAILABLE')
            attempt=start['attempt_id'];self.active[actor]=attempt
            return self.decision('face_exchange',attempt_id=attempt,board_text=raw_text if name_followup else '帮我登记身份，我叫'+intent['name'],reason='ORIGINAL_FACE_WORKFLOW')
        row=self.registry.attempt(attempt,meta);state=row['state']
        if state in ('ACTIVE','CANCELLED','EXPIRED','PARTIAL_CANCELLED','PARTIAL_EXPIRED','PARTIAL_CONFLICT'):
            self.active.pop(actor,None)
            return self.decision('ordinary_skip_speaker',reason=state)
        if text.strip(' 。！!？?') in ('取消','取消登记','取消身份关联','不保存'):
            result=self.registry.cancel(attempt,meta)
            if state=='SAMPLING_VOICE':self.speaker.cancel(meta,pcm)
            self.active.pop(actor,None)
            reply='关联已取消；此前已提交的人脸登记仍保留。' if result['face_already_saved'] else '这次身份关联已取消。'
            return self.decision('face_exchange' if state in ('AWAIT_CONFIRMATION','SAMPLING_FACE') else 'device_reply',
              reply=reply,attempt_id=attempt,board_text='取消登记',reason=result['state'])
        if state in ('AWAIT_CONFIRMATION','SAMPLING_FACE'):
            if state=='AWAIT_CONFIRMATION':
                if intent['kind'] in ('name_hint','remember_self') and intent['name'] is not None and intent['name']!=row['name']:
                    return self.decision('device_reply',reply='称呼有变化。请先取消本次关联，再按新称呼重新发起；不会沿用旧的保存授权。',reason='NAME_CHANGE_REQUIRES_NEW_CONSENT')
                try:confirmed=self.registry.confirm(attempt,meta,text,visual)
                except (ValueError,TimeoutError):
                    return self.decision('device_reply',reply='确认前需要同一张清晰人脸，请正对镜头后再确认；普通聊天仍可继续。',reason='BINDING_CONFIRMATION_VISUAL_UNAVAILABLE')
                if not confirmed:
                    if self.registry.attempt(attempt,meta)['state']=='CANCELLED':
                        self.active.pop(actor,None)
                        return self.decision('face_exchange',attempt_id=attempt,board_text='取消登记',reason='FACE_LIFECYCLE_CHANGED')
                    # The board's existing face flow owns confirmation prompts.
                    # A non-confirmation can still be a natural name correction.
                    return self.decision('face_exchange',attempt_id=attempt,board_text=text,reason='FACE_CONFIRMATION_PENDING')
                if json.loads(row['face_guard'])['face_identity_id'] is not None:
                    # The original known-face reply resets its enrollment FSM.
                    # Re-enter only that read-only query; this capture's explicit
                    # consent is kept in the registry for EXISTING_CONFIRMED.
                    return self.decision('face_exchange',attempt_id=attempt,board_text='帮我登记身份，我叫'+row['name'],reason='EXISTING_FACE_LINK_CONFIRMED')
            return self.decision('face_exchange',attempt_id=attempt,board_text=text,reason='ORIGINAL_FACE_WORKFLOW')
        if state=='SAMPLING_VOICE':
            from tools.provisional_voice import query_reply
            if query_reply(text,{'state':'UNKNOWN'}) is not None:
                # A read-only face/voice query is not one of the three voice
                # enrollment samples. The existing hub resolves this ordinary
                # route with current face/voice evidence and its conflict rules.
                return self.decision('ordinary',reason='IDENTITY_QUERY_DURING_VOICE_ENROLLMENT')
            face=json.loads(row['face_receipt'])
            try:
                current=_guard(visual,meta);original=json.loads(row['face_guard'])
                valid=(current['service_epoch']==original['service_epoch'] and current['camera_epoch']==original['camera_epoch']
                  and current['gallery_revision']==face['revision_after'] and current['face_identity_id']==face['identity_id'])
            except (ValueError,TypeError,KeyError):valid=False
            if not valid:
                # Continuing ordinary speech must skip the old standalone
                # enrollment adapter while unified enrollment is paused.
                return self.decision('ordinary_skip_speaker',attempt_id=attempt,reason='BINDING_PAUSED_NO_FRESH_BOUND_FACE')
            try:reply,payload=self.speaker.turn(meta,text,pcm)
            except (ValueError,TimeoutError):
                self.registry.partial(attempt,meta,'VOICE_WORKFLOW_CHANGED');self.active.pop(actor,None)
                return self.decision('device_reply',reply='人脸已保存，但这次声纹关联未完成，请稍后重新核对。',reason='VOICE_WORKFLOW_CHANGED')
            alias=self.speaker.take_alias(meta)
            if alias is not None:
                try:self.registry.attach_alias(attempt,meta,alias)
                except (ValueError,TimeoutError):pass
            if payload is not None:
                try:result=self.registry.accept_receipt(attempt,meta,self.registry.authority.sign(payload))
                except (ValueError,TimeoutError):
                    self.registry.partial(attempt,meta,'VOICE_RECEIPT_REJECTED');self.active.pop(actor,None)
                    return self.decision('device_reply',reply='声纹已按原流程保存，但关联元数据需要核对，尚未完成整合。',reason='VOICE_RECEIPT_REJECTED')
                self.active.pop(actor,None)
                if result['state']=='ACTIVE':
                    decision=self.decision('device_reply',reply='姓名、人脸和声纹已经关联保存。声纹的现场识别效果仍需按原流程标定。',attempt_id=attempt,reason='TWO_ORIGINAL_COMMITS_LINKED')
                    decision['unified_saved']=True;return decision
                return self.decision('device_reply',reply='人脸和声纹已分别提交，但身份关联发生冲突，尚未合并。',attempt_id=attempt,reason=result['state'])
            if not self.speaker.device.state(meta).get('active'):
                self.registry.partial(attempt,meta,'VOICE_ENROLLMENT_NOT_COMMITTED');self.active.pop(actor,None)
                return self.decision('device_reply',reply='人脸已保存，声纹没有确认成功，关联尚未完成。',reason='VOICE_ENROLLMENT_NOT_COMMITTED')
            if self.speaker.device.sessions[self.speaker.device.key(meta)]['stage']=='confirm':
                reply='人脸已保存，三段声纹也已准备好。要完成关联，请说“确认保存身份关联”；也可以取消。'
            return self.decision('device_reply',reply=reply,attempt_id=attempt,reason='ORIGINAL_VOICE_WORKFLOW')
        return self.decision('ordinary_skip_speaker',attempt_id=attempt,reason='BINDING_STATE_UNAVAILABLE')
    def face_result(self,meta,pcm,attempt_id,value,signed_receipt=None):
        """Called by the matching request-scoped identity exchange, not by LLM text."""
        from common.voice_enrollment import render
        context(meta,pcm)
        waiting=self.name_waiting.get(self.actor(meta))
        if waiting is not None and waiting['ticket']==attempt_id:
            cancel=waiting.get('cancel_context')
            if cancel is not None:
                if cancel!=meta or value['code']!='cancelled':raise ValueError('Stale name-request cancellation')
                self.name_waiting.pop(self.actor(meta),None);return '这次身份关联已取消。'
            if waiting['context']!=meta:raise ValueError('Name request belongs to another capture')
            if signed_receipt is not None:raise ValueError('No enrollment can commit before a name and confirmation')
            return '可以。这次会关联姓名、人脸和声纹。请告诉我你希望我怎么称呼你，说“我叫某某”。'
        row=self.registry.attempt(attempt_id,meta)
        if value['code']=='cancelled' and row['state'] in ('CANCELLED','PARTIAL_CANCELLED'):
            return '关联已取消，已提交的人脸登记仍保留。' if row['state']=='PARTIAL_CANCELLED' else '这次身份关联已取消。'
        if self.active.get(self.actor(meta))!=attempt_id:raise ValueError('Binding exchange is no longer current')
        code=value['code'];part=render(value)
        if code in ('prepare_name','prepare_update_name'):
            return part+'这次会按原流程把姓名、人脸和声纹关联；两部分都完成后才算保存成功。'
        if code=='already_known' and row['state']=='AWAIT_CONFIRMATION':
            return '当前人脸已有记录。要把同一称呼和声纹关联，请说“确认登记”；也可以取消。'
        if code not in ('registered','already_known'):return part
        if signed_receipt is None:
            return '人脸提交结果需要核对，声纹和姓名的关联还没有完成。'
        try:result=self.registry.accept_receipt(attempt_id,meta,signed_receipt)
        except (ValueError,TimeoutError):
            self.registry.partial(attempt_id,meta,'FACE_RECEIPT_REJECTED');self.active.pop(self.actor(meta),None)
            return '人脸结果需要核对，声纹和姓名的关联还没有完成。'
        if result['state']!='SAMPLING_VOICE':raise ValueError('Face receipt did not start unified voice stage')
        try:
            reply=self.speaker.start(meta,pcm,attempt_id=attempt_id,origin=json.loads(row['origin']),name=row['name'],
              gallery=json.loads(row['voice_gallery']),face_guard=json.loads(row['face_guard']))
        except (ValueError,TimeoutError):
            self.registry.partial(attempt_id,meta,'VOICE_START_FAILED');self.active.pop(self.actor(meta),None)
            return '人脸已保存，但声纹登记暂未开始，身份关联还没有完成。'
        return '人脸已保存，接下来继续登记声纹，不用再发登记指令。'+reply
