"""Finalize completed machine evidence; never fabricate live user acceptance."""
import hashlib,json,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
load=lambda name:json.loads((HERE/name).read_text(encoding='utf-8'))
c=load('candidate.json');d=load('deployment.json');v=load('source_verification.json');h=load('actual_http.json')
assert c['tests_passed'] and c['preflight_passed']
assert d['status']=='HANDS_FREE_AV_ENTRY_DEPLOYED' and v['status']=='PASS_ACTIVE_HANDSFREE_SOURCE_AND_CONFIG'
assert h['actual_asr_silence_rejected'] and h['silence_no_history_write'] and h['archived_speech_entry_passed']
assert '174 passed' in (HERE/'tests_pc.log').read_text(encoding='utf-8',errors='replace')
assert '270 passed' in (HERE/'tests_board.log').read_text(encoding='utf-8',errors='replace')
for name,sha in load('preserved_sources.json').items():
 assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
host=json.load(urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=4))
assert host['ready'] and host['handsfree_entry']['gate']=='energy_then_asr_first_turn'
summary={'status':'DEPLOYED_HANDSFREE_VISUAL_AUDIO_RULES_LIVE_USER_ACCEPTANCE_PENDING',
 'date':'2026-10-20','runtime':c['runtime'],'windows_tests_passed':174,'linux_tests_passed':270,
 'no_click_start':True,'wake_name_required':False,'identity_name_required':False,
 'criteria':['fresh_stable_single_frontal_face','same_face_at_speech_onset_and_submission',
             'sustained_raw_audio_activity','valid_first_turn_asr'],
 'actual_silence_initial_failure_fixed':True,'actual_archived_voice_http_passed':True,
 'new_anonymous_conversation_on_automatic_entry':True,'old_user_memory_auto_resume':False,
 'model_voice_context_unchanged':True,'identity_threshold_preserved':v['threshold_preserved'],
 'identity_database_unchanged':v['identity_database_unchanged'],
 'new_photos_saved_by_this_feature':False,'speaker_binding_verified':False,
 'television_bystander_rejection_verified':False,'voice_barge_in':False,'full_duplex':False,
 'live_user_acceptance':False,'listening_verified':False,
 'passive_states':sorted(set(row['handsfree']['state'] for row in v['passive_observation']))}
(HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
if not (HERE/'listening.json').exists():
 (HERE/'listening.json').write_text(json.dumps({'status':'PENDING_LIVE_NO_CLICK_CONVERSATION',
    'user_feedback':None,'new_recording_claimed':False},indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=True))
