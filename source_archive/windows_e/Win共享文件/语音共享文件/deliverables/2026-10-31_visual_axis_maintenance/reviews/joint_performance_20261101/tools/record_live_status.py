"""Index saved live metadata and actual paused recovery; never contact devices or models."""
from pathlib import Path
import hashlib,json,time
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parents[1];PROJECT=HERE.parents[3]
OWNER=PROJECT/'deliverables/2026-10-30_board_owner'
def read(p):return json.loads(p.read_bytes())
def raw(v):return (json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def ref(p):return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
def put(p,data):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(data)
def replace(p,data):
 tmp=p.with_name(p.name+'.live-status-tmp');put(tmp,data);tmp.replace(p)

def trial(folder,label):
 path=HERE/'evidence'/folder
 rows=[json.loads(x) for x in (path/'metadata.jsonl').read_text('utf-8').splitlines() if x.strip()]
 complete=next((r for r in rows if r.get('kind')=='complete' and r.get('status')=='ONE_NEW_TURN_COMPLETE'),None)
 samples=[r for r in rows if r.get('kind')=='sample']
 result=dict(label=label,directory=str(path),metadata=ref(path/'metadata.jsonl'),samples=len(samples),
             first_observed_mono=samples[0]['observed_mono'],last_observed_mono=samples[-1]['observed_mono'])
 if complete:
  token=complete['request_token']
  matched=next(r for r in reversed(samples) if r.get('ack_request_token')==token and r.get('ack_committed') is True
               and r.get('playing') is False and r.get('latency',{}).get('complete') is True)
  result.update(status='ONE_NEW_TURN_COMPLETE',request_token=token,matching_full_ack=True,
                latency=matched.get('latency'),prepare_latency=matched.get('prepare_latency'),
                audio_output=matched.get('audio_output'),runtime_faults=matched.get('runtime_faults'),
                result=ref(path/'RESULT.json'))
  if (path/'FINAL_PAUSED.json').exists():result['final_paused']=ref(path/'FINAL_PAUSED.json')
 else:
  result.update(status='INTERRUPTED_NO_NEW_REQUEST_OBSERVED',matching_full_ack=False,
                observed_request_tokens=sorted({r['request_token'] for r in samples if r.get('request_token')}))
  if folder=='live_trial_1793534789636233900':
   proof_path=HERE/'evidence/correlated_observer_public_and_saved_metadata_check.json';proof=read(proof_path)
   matched=next(r for r in samples if r.get('observed_mono')==proof['matched_ack_observed_mono'])
   token=proof['real_metadata_replay_first_target']
   assert matched['ack_request_token']==token and matched['ack_committed'] is True
   result.update(status='SAVED_METADATA_FIRST_REQUEST_FULL_ACK_CORRELATED',original_observer_status='WINDOW_TIMEOUT',
                 correlation_proof=ref(proof_path),request_token=token,matching_full_ack=True,
                 latency=matched['latency'],prepare_latency=matched['prepare_latency'],audio_output=matched['audio_output'],
                 runtime_faults=matched['runtime_faults'],result=ref(path/'RESULT.json'),final_paused=ref(path/'FINAL_PAUSED.json'),
                 later_request_excluded_from_target='872726c529bc6c7f42c1b642285cda3a9297c8301705667a967d494db0a03a8a')
 if (path/'USER_FEEDBACK.json').exists():result['user_feedback']=read(path/'USER_FEEDBACK.json')
 return result

def main():
 trials=[trial('live_trial_1793533963889831800','introduction'),trial('live_trial_1793534222176570200','visual_query'),
         trial('live_trial_1793534402189129700','current_dialogue_memory_input_interrupted'),
         trial('live_trial_1793534789636233900','current_dialogue_memory_input_retry'),
         trial('live_trial_1793534998542030400','current_dialogue_memory_recall_invalid_user_question'),
         trial('live_trial_1793535181537321400','user_requested_redo_memory_input'),
         trial('live_trial_1793535383341989300','user_requested_redo_memory_recall')]
 recovery=HERE/'evidence/live_trial_1793535383341989300/FINAL_PAUSED.json'
 last=read(recovery)['proof'];assert last['state']['listening_state']=='PAUSED' and not last['state']['microphone_open']
 report=dict(schema='aura-joint-live-current-status-3',status='USER_REPORTED_MULTI_TURN_MEMORY_OK_PAUSED_SUBTITLE_REPAIR_PENDING',
  recorded_utc=datetime.now(timezone.utc).isoformat(),trials=trials,latest_actual_state=last,latest_state_reference=ref(recovery),
  subtitle_display_acceptance='FAILED_BY_USER_REPORT',subtitle_control_metadata_available=False,
  full_system_acceptance=False,current_dialogue_memory_acceptance='USER_REPORTED_ACTIVE_MULTI_TURN_OK',visual_correctness_user_acceptance=True,
  user_report_multi_turn_memory_ok=True,reported_additional_turns=3,actual_extra_turn_text_or_identity_exported=False,
  over_five_minute_summary_retrieval_verified=False,extra_request_sources='Unknown individually; may include user active testing',
  invalid_prior_recall_question='live_trial_1793534998542030400',
  pre_recording_guard_refusals=[ref(HERE/'evidence'/folder/'RESULT.json') for folder in
      ('live_trial_1793535223999197000','live_trial_1793535250611397400','live_trial_1793535319070156600')],
  real_audio_first_trial_user_accepted=True,acoustic_first_sound_measured=False,raw_text_audio_images_saved=False,
  device_commands_inflight=False,
  pending='Remain paused while subtitle public harness portability is corrected and one-source publication is reviewed. No automatic extra memory or performance run.')
 path=HERE/'LIVE_STATUS.json'
 if path.exists():put(HERE/'live_status_history'/('before_'+str(time.time_ns())+'.json'),path.read_bytes())
 replace(path,raw(report))
 for p in (HERE/'LATEST.json',OWNER/'coordination/runtime_windows.json'):
  archive=HERE/'docs_state_live/before'/('t'+str(time.time_ns()))/p.relative_to(PROJECT);put(archive,p.read_bytes())
  d=read(p)
  if p.name=='LATEST.json':d.update(status=report['status'],live_status=ref(path),live_latest=ref(HERE/'LIVE_LATEST.json'))
  else:
   d.update(status=report['status'],latest_joint_live_status=ref(path),last_device_state=last['state'],
             last_device_observed_mono=last['observed_mono'],updated_utc=report['recorded_utc'])
   d['device_operation_owner']['state']='IDLE_FINAL_PAUSED_WAITING_SUBTITLE_CANDIDATE'
   d['verified_listening']=dict(enabled=False,state='PAUSED',microphone_open=False,startup_sha256=last['startup_sha256'],source=ref(recovery))
  replace(p,raw(d))
 notes=dict(schema='aura-joint-execution-notes-1',failure_history_preserved=True,items=[
  dict(stage='local transaction fixture',observed='Two NameError exceptions because standalone test fixture did not inject Path supplied by production prefix.',
       correction='Only test fixture amended; exact approved publisher bundle stayed 7da0fb13…; nine tests then passed.',
       failed_receipt='evidence/single_projection_local_transaction_tests.json',passed_receipt='evidence/single_projection_local_transaction_tests_1793533284890319100.json'),
  dict(stage='guarded first window inspection',observed='main_page_visible_original_16fps_required rejected one observation; GUI still running, no WM_DELETE sent.',
       correction='Unchanged main page/visible/scheduling true confirmed by metadata-only read; no page command; exact unchanged window gate later passed.'),
  dict(stage='first live external pause',observed='First check rejected non-IDLE state; later check rejected last-ACK no longer matching original completed target.',
       correction='Original completed target ACK already sealed; normal pause after playback idle, original target not interrupted; latest-ACK changed, so later ambient activity not folded into first turn.'),
  dict(stage='third live interruption',observed='Desktop active turn interrupted; no local Python/SSH observer remained; 56 sealed samples with no request token, no completion.',
       correction='Existing serialization lock acquired fresh, original entry paused, source/owners/firmware/output reverified. No duplicate trial launched.')])
 notes_path=HERE/'EXECUTION_NOTES.json'
 if not notes_path.exists():put(notes_path,raw(notes))
 print(json.dumps(dict(status=report['status'],live_status=ref(path),final_paused=True,device_access=False),ensure_ascii=False))

if __name__=='__main__':main()
