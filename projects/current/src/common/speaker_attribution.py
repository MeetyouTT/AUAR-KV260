"""Offline candidate gate for attributed speaker results; no model or database IO.

Not a production speaker selector. Calibration and real microphone validation
are required before any caller uses an accepted result for personal memory.
"""
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class SpeakerContext:
    capture_id: str
    turn_generation: int
    model_id: str
    gallery_revision: int


def evaluate(result, current, now_ms, *, threshold, margin, minimum_voiced_ms,
             field_calibrated=False, cancelled=False):
    def reject(reason):return {'accepted':False,'reason':reason,'personal_memory_allowed':False}
    if cancelled:return reject('CANCELLED')
    if not field_calibrated:return reject('NOT_FIELD_CALIBRATED')
    if not isinstance(current,SpeakerContext) or not isinstance(result,dict):return reject('INVALID_CONTEXT')
    if (not current.capture_id or not current.model_id or type(current.turn_generation) is not int
            or current.turn_generation<0 or type(current.gallery_revision) is not int or current.gallery_revision<0):
        return reject('INVALID_CONTEXT')
    expected={'capture_id':current.capture_id,'turn_generation':current.turn_generation,
              'model_id':current.model_id,'gallery_revision':current.gallery_revision}
    if any(type(result.get(k)) is not type(v) or result.get(k)!=v for k,v in expected.items()):
        return reject('CONTEXT_MISMATCH')
    start,end,deadline=(result.get(k) for k in ('started_ms','ended_ms','deadline_ms'))
    if (any(type(v) is not int for v in (start,end,deadline,now_ms))
            or not 0<=start<=end<=now_ms<deadline):return reject('EXPIRED_OR_INVALID_WINDOW')
    if (type(minimum_voiced_ms) is not int or minimum_voiced_ms<=0
            or type(result.get('voiced_ms')) is not int or not minimum_voiced_ms<=result['voiced_ms']<=end-start):
        return reject('INSUFFICIENT_OR_INVALID_SPEECH')
    if result.get('single_speaker_verified') is not True:return reject('SPEAKER_OVERLAP_UNVERIFIED')
    if not all(type(v) in (int,float) and math.isfinite(v) for v in (threshold,margin)) or not -1<=threshold<=1 or not 0<=margin<=2:
        return reject('INVALID_OPERATING_POINT')
    scores=result.get('scores')
    if not isinstance(scores,dict) or not scores or any(not isinstance(k,str) or not k
            or type(v) not in (int,float) or not math.isfinite(v) or not -1<=v<=1 for k,v in scores.items()):
        return reject('INVALID_SCORES')
    ranked=sorted(scores.items(),key=lambda row:row[1],reverse=True)
    if ranked[0][1]<threshold:return reject('LOW_SIMILARITY')
    if len(ranked)>1 and ranked[0][1]-ranked[1][1]<margin:return reject('AMBIGUOUS')
    # Face identity has a separate trust boundary; never infer it from a face box.
    if result.get('face_identity_conflict') is not False:return reject('FACE_CONFLICT_OR_UNVERIFIED')
    return {'accepted':True,'reason':'CANDIDATE_SPEAKER_MATCH','identity_id':ranked[0][0],
            'personal_memory_allowed':False}
