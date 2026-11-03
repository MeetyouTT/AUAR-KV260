"""Per-turn descriptive voice evidence. No profile selection or biometric templates."""
import copy,math,re
from common.asr_wire import context
from common.conversation_store import conversation_id
from common.speaker_visual import unavailable,validate_visual

STATES={'PENDING','COMPLETE','UNAVAILABLE','CANCELLED','EXPIRED'}
VOICE_STATES={'NOT_CALIBRATED','NO_ENROLLMENT','INSUFFICIENT_SPEECH','UNKNOWN','AMBIGUOUS','CANDIDATE','CANDIDATE_STABLE','UNAVAILABLE'}
FIELDS={'version','context','conversation_id','status','reason','voice','visual','relation','personal_memory_allowed'}
VOICE_FIELDS={'state','model_id','gallery_revision','candidate_id','score','voiced_ms','field_calibrated',
              'single_speaker_verified','consecutive_distinct'}

def record(meta,cid,*,status='PENDING',reason='ANALYSIS_PENDING',voice=None,visual=None):
    result=dict(version=1,context=context(meta),conversation_id=conversation_id(cid),status=status,reason=reason,
      voice=copy.deepcopy(voice),visual=validate_visual(visual,meta) if visual is not None else unavailable(meta),
      relation='INDEPENDENT_EVIDENCE',personal_memory_allowed=False)
    return validate_record(result,meta,cid)

def validate_record(value,meta,cid):
    if not isinstance(value,dict) or set(value)!=FIELDS or type(value.get('version')) is not int or value['version']!=1:
        raise ValueError('Invalid speaker turn record')
    if value['context']!=context(meta) or value['conversation_id']!=conversation_id(cid):raise ValueError('Speaker evidence belongs to another turn')
    if value['status'] not in STATES or not isinstance(value['reason'],str) or not re.fullmatch('[A-Z0-9_]{1,64}',value['reason']):
        raise ValueError('Invalid speaker terminal state')
    if value['personal_memory_allowed'] is not False or value['relation']!='INDEPENDENT_EVIDENCE':raise ValueError('Speaker candidates cannot grant profile access')
    validate_visual(value['visual'],meta)
    voice=value['voice']
    if voice is not None:
        if not isinstance(voice,dict) or set(voice)!=VOICE_FIELDS or voice.get('state') not in VOICE_STATES:raise ValueError('Invalid voice evidence')
        if (not isinstance(voice['model_id'],str) or not 1<=len(voice['model_id'])<=160 or
            type(voice['gallery_revision']) is not int or voice['gallery_revision']<0 or
            type(voice['voiced_ms']) is not int or not 0<=voice['voiced_ms']<=20000 or
            type(voice['consecutive_distinct']) is not int or not 0<=voice['consecutive_distinct']<=3 or
            type(voice['field_calibrated']) is not bool or voice['single_speaker_verified'] is not False):
            raise ValueError('Invalid voice provenance')
        candidate=voice['candidate_id'];score=voice['score']
        if candidate is not None and (not isinstance(candidate,str) or not re.fullmatch('[A-Za-z0-9_-]{1,96}',candidate)):
            raise ValueError('Invalid voice candidate')
        if score is not None and (type(score) not in (int,float) or not math.isfinite(score) or not -1<=score<=1):raise ValueError('Invalid voice score')
        if voice['state'] in ('CANDIDATE','CANDIDATE_STABLE'):
            if candidate is None or not voice['field_calibrated'] or score is None:raise ValueError('Uncalibrated speaker claim')
            if voice['state']=='CANDIDATE_STABLE' and voice['consecutive_distinct']!=3:raise ValueError('Unstable voice candidate')
        elif candidate is not None:raise ValueError('Unknown voice must not retain an old identity')
    if value['status']!='COMPLETE' and voice is not None:raise ValueError('Inactive turn must remain anonymous')
    return copy.deepcopy(value)
