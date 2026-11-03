"""Independent late-adoption/cancellation and namespace stress on real worker."""
import copy,hashlib,json,struct,sys,threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
import pytest
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
from composition import c
QUERY='你可以根据我的声音辨认我是谁吗'

def saved(c):
 c.say('登记声纹，我叫合成复验')
 for text in ('合成登记段一','合成登记段二','合成登记段三'):c.say(text)
 c.say('确认保存声纹');assert c.voice_count()==1;c.encoder.calls=0

def owner_after(previous,seed,request):
 raw=struct.pack('<h',1000+seed)*48000
 meta=dict(previous,request_id=request,capture_id='independent-capture-'+str(seed),
     generation=previous['generation']+1,pcm_sha256=hashlib.sha256(raw).hexdigest())
 return meta,raw

def test_changed_encoder_namespace_never_forms_new_candidate_against_old_store(c):
 saved(c);c.say(QUERY);c.say(QUERY)
 c.business.pool.submit(lambda:setattr(c.business.hub.speaker.encoder,'model_id','different-synthetic-model')).result(timeout=2)
 before=c.encoder.calls
 for _ in range(3):c.say(QUERY)
 assert c.encoder.calls==before
 assert c.business.public()['self_match_probe']['phase']=='SOURCE_CHANGED'
 assert '合成复验' not in c.last_reply

@pytest.mark.parametrize('surface',['public','health'])
def test_public_time_projection_never_takes_clock_while_holding_worker_lock(c,monkeypatch,surface):
 saved(c)
 for _ in range(3):c.say(QUERY)
 observed=[];original=c.business.wall_clock
 def clock():
  observed.append(c.business.lock._is_owned())
  return original()
 monkeypatch.setattr(c.business,'wall_clock',clock)
 value=getattr(c.business,surface)()['self_match_probe']
 assert value['phase']=='CANDIDATE' and observed and not any(observed)

@pytest.mark.parametrize('surface',['public','health'])
def test_public_clock_unavailable_expires_metadata_without_api_exception(c,monkeypatch,surface):
 saved(c)
 for _ in range(3):c.say(QUERY)
 from common.board_timeline_clock import ClockUnavailable
 def unavailable():raise ClockUnavailable('synthetic_anchor_unavailable')
 monkeypatch.setattr(c.business,'wall_clock',unavailable)
 value=getattr(c.business,surface)()['self_match_probe']
 assert value['phase']=='EXPIRED' and value['field_calibrated'] is False
 assert value['identity_verified'] is False and value['personal_memory_allowed'] is False

def test_actual_yuki_probe_reuses_control_descriptor_and_exact_retry_without_extra_encode(c):
 saved(c)
 from tools import yuki_jobs_candidate
 assert c.runtime.jobs._route.__func__ is yuki_jobs_candidate._route
 assert c.runtime.identity_handler.business is c.business
 for _ in range(3):c.say(QUERY)
 assert c.encoder.calls==3
 pub=c.business.public()['self_match_probe'];assert pub['phase']=='CANDIDATE' and pub['candidate_completed']==1
 old=c.last_reply;meta=copy.deepcopy(c.last_meta);raw=c.last_raw
 assert c.business.turn(meta,QUERY,raw)==old and c.encoder.calls==3
 assert c.business.public()['self_match_probe']['candidate_completed']==1
 binding=c.business.hub.binding
 packet=c.business.pool.submit(lambda:binding.precomputed_analysis(meta,'a'*32)).result(timeout=2)
 assert packet['voice']['state']=='NOT_CALIBRATED' and packet['voice']['candidate_id'] is None
 assert '合成复验' not in json.dumps(packet,ensure_ascii=False) and c.encoder.calls==3
 assert c.business.hub.speaker.calibrated is False and c.business.health()['profile_grants_issued'] is False
 assert binding.registry.health()['active_people']==0

def test_candidate_cache_expiry_keeps_only_historical_count_not_name_or_extra_encode(c):
 saved(c)
 for _ in range(3):c.say(QUERY)
 meta=copy.deepcopy(c.last_meta);raw=c.last_raw;c.mono.now+=2.01
 pub=c.business.public()['self_match_probe']
 assert pub['phase']=='EXPIRED' and pub['candidate_completed']==1 and pub['completed_is_historical'] is True
 reply=c.business.turn(meta,QUERY,raw)
 assert '合成复验' not in reply and c.encoder.calls==3
 assert c.business.public()['self_match_probe']['candidate_completed']==1

def test_adoption_ledger_retains_only_metadata_event_and_boolean_not_job_audio_or_closure(c):
 saved(c);c.say(QUERY)
 for ledger in c.business._probe_captures.values():
  for row in ledger.values():
   assert set(row)=={'meta','cancelled','adopted'}
   assert isinstance(row['cancelled'],threading.Event) and type(row['adopted']) is bool
   assert all(type(value) in (str,int) for value in row['meta'].values())
 serialized=json.dumps(c.business.public(),ensure_ascii=False)
 assert '合成复验' not in serialized and c.last_meta['pcm_sha256'] not in serialized

@pytest.mark.parametrize('clock_change',['monotonic','wall_bounds','wall_unavailable'])
def test_finished_worker_candidate_is_rechecked_at_actual_call_adoption(c,monkeypatch,clock_change):
 saved(c);c.say(QUERY);c.say(QUERY)
 service=c.business;third,raw=owner_after(c.last_meta,121,'independent-expiry-adoption')
 original=service._job_current;seen=[];old_wall=service.wall_clock
 from common.board_timeline_clock import ClockUnavailable
 def guarded(job):
  if (job['meta']==third and threading.current_thread().name=='MainThread'
      and job.get('future') is not None and job['future'].done() and not seen):
   seen.append(True)
   if clock_change=='monotonic':c.mono.now+=2.01
   elif clock_change=='wall_bounds':monkeypatch.setattr(service,'wall_clock',lambda:old_wall()+3.)
   else:
    def unavailable():raise ClockUnavailable('synthetic_adoption_clock_unavailable')
    monkeypatch.setattr(service,'wall_clock',unavailable)
  return original(job)
 monkeypatch.setattr(service,'_job_current',guarded)
 if clock_change=='wall_unavailable':
  with pytest.raises(ClockUnavailable):service.turn(third,QUERY,raw,is_current=lambda:True)
 else:
  reply=service.turn(third,QUERY,raw,is_current=lambda:True)
  assert '合成复验' not in reply and service.public()['self_match_probe']['phase']=='EXPIRED'
 service.pool.submit(lambda:None).result(timeout=2)
 assert seen and c.encoder.calls==3
 assert service.public()['self_match_probe']['candidate_completed']==0

@pytest.mark.parametrize('marker',[None,{'typed_control_response':True},'different original control reply'])
def test_expired_probe_cache_never_changes_other_original_call_return_type_or_value(c,marker):
 saved(c)
 for _ in range(3):c.say(QUERY)
 meta=copy.deepcopy(c.last_meta);raw=c.last_raw;c.mono.now+=2.01
 value=c.business._call(lambda raw:marker,meta,raw,is_current=lambda:True)
 assert value is marker and c.encoder.calls==3
 assert c.business.public()['self_match_probe']['candidate_completed']==1

def test_cancel_after_worker_completed_before_adoption_cannot_contaminate_queued_next_owner(c,monkeypatch):
 saved(c);c.say(QUERY);c.say(QUERY)
 service=c.business;third,raw3=owner_after(c.last_meta,101,'independent-late-third')
 fourth,raw4=owner_after(third,102,'independent-next-fourth')
 original=service._job_current;seen=[];later=[]
 def guarded(job):
  if (job['meta']==third and threading.current_thread().name=='MainThread'
      and job.get('future') is not None and job['future'].done() and not seen):
   seen.append(True)
   # Reproduce cancellation after _run's final check. Queue the next valid
   # owner before _call can enqueue cleanup, then deterministically let that
   # sole-worker job finish first. No devices or real audio are involved.
   job['cancelled'].set()
   with ThreadPoolExecutor(max_workers=1,thread_name_prefix='independent-next-caller') as caller:
    future=caller.submit(service.turn,fourth,QUERY,raw4,is_current=lambda:True)
    later.append(future.result(timeout=3))
  return original(job)
 monkeypatch.setattr(service,'_job_current',guarded)
 with pytest.raises(InterruptedError):service.turn(third,QUERY,raw3,is_current=lambda:True)
 service.pool.submit(lambda:None).result(timeout=2)
 assert seen and later
 result=service.public()['self_match_probe']
 evidence=dict(source_sha256=hashlib.sha256((ROOT/'candidate_runtime/board/runtime/board_speaker_business.py').read_bytes()).hexdigest(),
   late_cancel_observed=True,next_phase=result['phase'],next_distinct=result['distinct_captures'],
   next_reply_contains_registered_synthetic_name='合成复验' in later[0],encoder_calls=c.encoder.calls,
   fixture_is_fresh_synthetic_only=True,board_actions=False)
 (HERE/'LATE_ADOPTION_OBSERVATION.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
 assert result['phase']!='CANDIDATE' and result['distinct_captures']<=1
 assert '合成复验' not in later[0]
