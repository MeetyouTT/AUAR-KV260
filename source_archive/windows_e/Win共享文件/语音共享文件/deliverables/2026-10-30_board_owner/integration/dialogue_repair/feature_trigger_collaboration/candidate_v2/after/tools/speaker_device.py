"""Explicit three-utterance voice enrollment. No automatic profile grants."""
import hashlib,re,time,uuid
from common.asr_wire import context
from common.speaker_identity import SpeakerStore,voiced_pcm,enrollment_vector

class SpeakerDevice:
    def __init__(self,encoder,database,*,calibration=None,clock=time.monotonic,quality=None):
        self.encoder=encoder;self.database=database;self.clock=clock;self.sessions={};self.latest={};self.replies={}
        if quality is not None and not callable(quality):raise ValueError('A speaker quality gate is required')
        self.quality=quality if quality is not None else lambda raw:voiced_pcm(raw)
        # No threshold is presented as field calibrated without a model-bound
        # calibration artifact. Enrollment still works with a strict consistency check.
        c=calibration or {};self.calibrated=(c.get('model_id')==encoder.model_id and c.get('field_calibrated') is True
            and isinstance(c.get('evidence'),str) and bool(c['evidence']))
        self.threshold=c.get('threshold',.8);self.margin=c.get('margin',.1);self.consistency=c.get('consistency',.6)
        self.store=SpeakerStore(database,encoder.model_id,encoder.dimension,self.threshold,self.margin,create=True)
    def key(self,meta):
        context(meta);return (meta['board_boot_id'],meta['session_id'])
    def state(self,meta):
        key=self.key(meta);row=self.sessions.get(key)
        if row and self.clock()>=row['until']:self.sessions.pop(key);row=None
        return {'active':bool(row),'calibrated':self.calibrated,'automatic_profile_access':False}
    def analyze(self,meta,pcm):
        """Read-only evidence for one captured turn; never enroll or select a profile."""
        context(meta,pcm)
        result={'state':'NOT_CALIBRATED','model_id':self.encoder.model_id,'gallery_revision':self.store.revision,
                'candidate_id':None,'score':None,'voiced_ms':0,'field_calibrated':self.calibrated,
                'single_speaker_verified':False,'consecutive_distinct':0}
        # Skip the expensive embedding while the operating point is unvalidated.
        # Ordinary conversation remains recorded anonymously, without false names.
        if not self.calibrated:return result
        if not self.store.people():result['state']='NO_ENROLLMENT';return result
        try:
            raw,quality=self.quality(pcm)
            result['voiced_ms']=min(20000,round(quality['vad_speech_seconds']*1000))
            matched=self.store.match(self.encoder.encode(raw))
        except ValueError:result['state']='INSUFFICIENT_SPEECH';return result
        if matched.revision!=result['gallery_revision'] or self.store.revision!=matched.revision:
            result['state']='UNAVAILABLE';return result
        result['state']='CANDIDATE' if matched.state=='KNOWN' else matched.state
        result['score']=matched.score
        if matched.state=='KNOWN':result['candidate_id']=matched.identity_id
        return result
    def turn(self,meta,text,pcm):
        context(meta,pcm)
        rid=(meta['board_boot_id'],meta['session_id'],meta['request_id'])
        fingerprint=hashlib.sha256((repr(meta)+text).encode()+pcm).hexdigest()
        if rid in self.replies:
            old,value=self.replies[rid]
            if old!=fingerprint:raise ValueError('Request identity reused with different input')
            return value
        reply=self._turn(meta,text,pcm)
        self.replies[rid]=(fingerprint,reply)
        while len(self.replies)>64:self.replies.pop(next(iter(self.replies)))
        return reply
    def _turn(self,meta,text,pcm):
        key=self.key(meta);generation=meta['generation'];old=self.latest.get(key,-1)
        if generation<old:raise ValueError('Stale speaker request')
        self.latest[key]=generation
        while len(self.latest)>32:self.latest.pop(next(iter(self.latest)))
        active=self.state(meta)['active'];row=self.sessions.get(key)
        from common.feature_intents import speaker_text
        compact=speaker_text(text,active=active) or text.strip(' 。！!？?')
        if compact in ('查询我的声纹','查询声纹保存状态'):
            # A question is never an enrollment sample or a save confirmation.
            if active:
                if row['stage']=='delete':return '声纹删除还在等待明确确认，本轮删除尚未执行。'
                if row['stage']=='confirm':return '本轮声纹样本已准备好，仍在等待明确确认保存。'
                return '本轮声纹仍在采样，尚未提交保存。'
            if compact=='查询声纹保存状态':
                receipt=getattr(self,'save_receipts',{}).get(key)
                if (receipt is not None and self.clock()<receipt['until']
                        and receipt['revision']==self.store.revision
                        and generation>receipt['generation']
                        and any(p['person_id']==receipt['identity_id'] for p in self.store.people())):
                    return '本次会话已收到声纹保存提交回执；这不代表说话者身份已确认。'
                return '当前没有可核对的本轮声纹保存回执，不能判断是否保存成功。'
        if compact in ('取消登记','取消声纹登记','取消','不保存'):
            self.sessions.pop(key,None);return '已取消，没有保存新的声纹。'
        if not active and compact in ('确认保存声纹','确认删除声纹'):
            return '当前没有待确认的声纹操作，没有保存或删除。'
        if not active and compact=='登记我的声纹':
            return '尚未开始声纹登记。请说“登记我的声纹，我叫某某”，再按提示采样并确认保存。'
        match=re.fullmatch(r'(?:请)?(?:登记我的声纹|记住我的声音|登记声纹)[，, ]*(?:我叫|名字是)([^，,。！？!?\s]{1,20})',compact)
        if match:
            getattr(self,'save_receipts',{}).pop(key,None)
            while len(self.sessions)>=4:self.sessions.pop(next(iter(self.sessions)))
            self.sessions[key]={'stage':'samples','name':match[1],'vectors':[],'hashes':set(),'until':self.clock()+180}
            return '好的，开始登记你的声纹。请分三次说不同的句子，每次三到十秒。先介绍一下你今天做了什么。'
        if re.fullmatch(r'(?:请)?删除声纹[，, ]*(?:名字是|名为)?([^，,。！？!?\s]{1,20})',compact):
            name=re.fullmatch(r'(?:请)?删除声纹[，, ]*(?:名字是|名为)?([^，,。！？!?\s]{1,20})',compact)[1]
            ids=[p['person_id'] for p in self.store.people() if p['display_name']==name]
            if len(ids)!=1:return '没有找到唯一对应的声纹名字，请核对后再说。'
            self.sessions[key]={'stage':'delete','id':ids[0],'revision':self.store.revision,'until':self.clock()+30}
            return '要删除这个名字的声纹，请说“确认删除声纹”。'
        if active and row['stage']=='delete':
            if compact=='确认删除声纹':
                self.store.delete(row['id'],expected_revision=row['revision']);self.sessions.pop(key,None)
                return '声纹已删除。'
            return '尚未删除。请说“确认删除声纹”，或说“取消”。'
        if active and row['stage']=='confirm':
            if compact=='确认保存声纹':
                vector=enrollment_vector(row['vectors'],self.encoder.dimension,self.consistency)
                other=self.store.best_other_score(vector)
                if other is not None and other>=self.threshold:
                    self.sessions.pop(key,None);return '样本与已有声纹过于接近，这次没有新增，请先核对已有登记。'
                identity_id=uuid.uuid4().hex
                self.store.enroll(identity_id,row['name'],vector,consent=True,expected_revision=row['revision'],max_people=32)
                # Receipt is derived from the actual original transaction and
                # exact resulting gallery revision, never from spoken/LLM text.
                if (self.store.revision==row['revision']+1
                        and any(p['person_id']==identity_id for p in self.store.people())):
                    self.save_receipts=getattr(self,'save_receipts',{})
                    self.save_receipts[key]=dict(identity_id=identity_id,revision=self.store.revision,
                        generation=generation,until=self.clock()+60.)
                    while len(self.save_receipts)>32:self.save_receipts.pop(next(iter(self.save_receipts)))
                self.sessions.pop(key,None)
                return '声纹样本已保存。现场识别阈值还需要校准，不会据此自动打开私人记忆。' if not self.calibrated else '声纹已保存。'
            return '样本准备好了，请说“确认保存声纹”，或说“取消”。'
        if active:
            digest=hashlib.sha256(pcm).hexdigest()
            if digest in row['hashes']:return '这段样本已经用过，请换一句话。'
            try:raw,quality=self.quality(pcm);vector=self.encoder.encode(raw)
            except ValueError:return '这段有效语音不足或不清楚，请连续说三到十秒，再试一次。'
            if self.clock()>=row['until']:self.sessions.pop(key,None);return '登记已超时，请重新开始。'
            row['vectors'].append(vector);row['hashes'].add(digest)
            if len(row['vectors'])<3:return '收到，请再说一句不同的话，保持三到十秒。'
            try:enrollment_vector(row['vectors'],self.encoder.dimension,self.consistency)
            except ValueError:
                self.sessions.pop(key,None);return '三段声音不够一致，没有保存，请在安静环境重新登记。'
            row.update(stage='confirm',revision=self.store.revision)
            return '三段样本已经准备好。要保存请说“确认保存声纹”，不保存请说“取消”。'
        if re.search('声纹|我的声音|听声音.*谁|声音.*认识',compact):
            if not self.store.people():return '还没有登记声纹。可以说“登记我的声纹，我叫某某”。'
            if not self.calibrated:return '本机有声纹记录，但现场阈值尚未校准，不能确认当前说话者是否已登记。'
            try:raw,quality=self.quality(pcm);result=self.store.match(self.encoder.encode(raw))
            except ValueError:return '这句话太短或不够清楚，请多说几秒，再让我辨认声音。'
            if result.state=='KNOWN':return '声音匹配到登记的'+result.name+'。这不是身份验证，也不会自动打开私人记忆。'
            return '这次声音匹配不确定，我先按访客和你聊天。'
        return None
