import copy,hashlib,time
from common.speaker_turns import record

CID='a'*32
def pcm(number=1):return bytes((number%127,0))*48000
def meta(number=1,*,raw=None,session='session',generation=None):
    raw=pcm(number) if raw is None else raw
    return dict(protocol='aura-asr-1',board_boot_id='boot',session_id=session,request_id='request-'+str(number),
      generation=number if generation is None else generation,capture_id='capture-'+str(number),sample_count=len(raw)//2,
      pcm_sha256=hashlib.sha256(raw).hexdigest(),budget_ms=10000)
def voice(*,state='CANDIDATE',revision=1,person='voice-one'):
    return dict(state=state,model_id='synthetic-ecapa',gallery_revision=revision,candidate_id=person if state.startswith('CANDIDATE') else None,
      score=.95 if state.startswith('CANDIDATE') else None,voiced_ms=3000,field_calibrated=state!='NOT_CALIBRATED',
      single_speaker_verified=False,consecutive_distinct=1 if state.startswith('CANDIDATE') else 0)
def complete(owner,cid=CID):return record(owner,cid,status='COMPLETE',reason='DESCRIPTIVE_EVIDENCE_ONLY',voice=voice())
def wait(predicate,seconds=2):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        if predicate():return
        time.sleep(.005)
    raise AssertionError('Bounded asynchronous condition did not complete')
def snapshot(stamp,frame,*,person='face-one'):
    key=dict(camera_epoch='camera',track_id=1,track_generation=1)
    identity=dict(state='KNOWN',person_id=person,display_name='公开测试姓名',db_version=2,
      target_kind='face',face_count=1,face_target=key,face_targets=[{'key':key,'label':'face'}],target=key,
      source_frame_id=frame,source_mono_ms=stamp-30,people=[{'person_id':person,'display_name':'公开测试姓名'}])
    return dict(protocol_version='aura-ui-1',board_boot_id='boot',service_epoch='camera-service',sequence=frame,
      observed_mono_ms=stamp,ttl_ms=2000,source_kind='actual',context={'session_id':'ui','request_id':'','generation':0},
      modules={'camera':{'state':'READY'},'identity':identity},capabilities={},
      preview={'camera_epoch':'camera','frame_id':frame,'captured_mono_ms':stamp-30})
