"""Uncalibrated computational matches are candidates, never verified identity.

Runs on the existing sole CPU speaker worker using its already computed vector.
Three distinct captures, the original model/threshold/margin and ACTIVE binding
are all required before a linked display-name candidate can be shown.
"""
import copy,hashlib,time
from collections import OrderedDict
from common.asr_wire import context

class ProvisionalVoiceMatcher:
    def __init__(self,device,*,clock=time.time):
        self.device=device;self.clock=clock;self.streaks=OrderedDict();self.results=OrderedDict()
    @staticmethod
    def key(meta):return meta['board_boot_id'],meta['session_id'],meta['request_id']
    def observe(self,meta,vector,*,is_current=lambda:True):
        meta=context(meta);device=self.device;actor=(meta['board_boot_id'],meta['session_id']);now=self.clock()
        self.results.pop(self.key(meta),None)
        if device.calibrated or device.threshold<.8 or device.margin<.1 or not is_current():return None
        revision=device.store.revision;matched=device.store.match(vector)
        if matched.state!='KNOWN' or device.store.revision!=revision or matched.revision!=revision or not is_current():
            self.streaks.pop(actor,None);return None
        signature=(device.encoder.model_id,revision,matched.identity_id);old=self.streaks.get(actor)
        if old and meta['generation']<old['generation']:return None
        if old and old['signature']==signature and now-old['at']<=30:
            captures=list(old['captures']);digests=list(old['digests'])
            if meta['capture_id'] not in captures and meta['pcm_sha256'] not in digests:
                captures=(captures+[meta['capture_id']])[-3:];digests=(digests+[meta['pcm_sha256']])[-3:]
        else:captures=[meta['capture_id']];digests=[meta['pcm_sha256']]
        self.streaks[actor]=dict(signature=signature,captures=captures,digests=digests,at=now,generation=meta['generation'])
        self.streaks.move_to_end(actor)
        while len(self.streaks)>32:self.streaks.popitem(last=False)
        if len(captures)<3:return None
        row=device.store.db.execute('SELECT embedding FROM templates WHERE identity_id=? AND model_id=?',(matched.identity_id,device.encoder.model_id)).fetchone()
        if row is None or not is_current():return None
        value=dict(context=meta,modality='voice',source_kind='actual',match_state='PROVISIONAL_NAME_CANDIDATE',
          original_matcher_accepted=True,field_calibrated=False,identity_id=matched.identity_id,model_id=device.encoder.model_id,
          gallery_revision=revision,template_fingerprint=hashlib.sha256(row[0].encode()).hexdigest(),
          consecutive_distinct=3,observed_at=now,expires_at=now+2)
        self.results[self.key(meta)]=value
        while len(self.results)>32:self.results.popitem(last=False)
        return copy.deepcopy(value)
    def proof(self,meta,*,store_id):
        meta=context(meta);row=self.results.get(self.key(meta))
        if row is None or row['context']!=meta or not self.clock()<row['expires_at']:return None
        return dict(copy.deepcopy(row),store_id=store_id)

def query_reply(text,resolution):
    """Only explicit identity questions produce a naming/confirmation prompt."""
    from common.voice_enrollment import identity_query_requested
    if not identity_query_requested(text) and text.strip(' 。！!？?') not in ('听声音我是谁','你认识我的声音吗'):return None
    state=resolution['state'];name=resolution.get('name')
    if state=='CONFLICT':return '当前人脸和声音对应的记录不一致，我先不确定是谁；普通聊天可以继续。'
    if state=='PROVISIONAL_NAME_CANDIDATE':return '声音可能对应登记的'+name+'，但声纹还未现场标定，不能确认身份。这个称呼对吗？'
    if state=='MATCH_CANDIDATE' and name:
        return ('当前画面中的人脸匹配到'+name+'；这不代表画外的说话者也是同一人。' if resolution['claim_scope']=='visible_person'
          else '声音按已标定的匹配规则对应'+name+'；这不会自动打开个人记忆。')
    return '这次还不能确定对应哪条身份记录，我先按访客和你聊天。'
