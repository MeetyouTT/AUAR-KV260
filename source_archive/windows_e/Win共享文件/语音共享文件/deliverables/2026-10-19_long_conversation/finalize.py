"""Record only completed checks; keep live human acceptance explicitly pending."""
import hashlib
import http.client
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
load=lambda name:json.loads((HERE/name).read_text(encoding='utf-8-sig'))
actual=load('actual_27b_summary.json');assert actual['passed'] and actual['actual_model_turns']==50
deployment=load('deployment.json');assert deployment['status']=='LONG_CONVERSATION_READY'
source=load('source_verification.json');assert source['status']=='PASS_ACTIVE_LONG_CONVERSATION_AND_UNCHANGED_PHOTO_CAMERA'
for name in ('http_before_restart.json','http_after_restart.json'):
    assert load(name)['unplayed_assistant_not_committed']
config_before=load('preserved_configs_before.json')
assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha for name,sha in config_before.items())
connection=http.client.HTTPConnection('192.168.50.1',8792,timeout=4)
try:
    connection.request('GET','/health');response=connection.getresponse();health=json.loads(response.read())
finally:connection.close()
assert health['ready'] and not health['busy'] and health['conversation_memory']['version']==1
assert health['llm_model']==actual['model'] and health['tts']=='omnivoice' and health['num_step']==16
pc=(HERE/'tests_pc_final.log').read_text(encoding='utf-8',errors='replace')
board=(HERE/'tests_board.log').read_text(encoding='utf-8',errors='replace')
assert '152 passed' in pc and '155 passed' in board
summary={'status':'DEPLOYED_PERSISTENT_CONVERSATION_AND_BOUNDED_RECALL_LIVE_ACCEPTANCE_PENDING',
         'date':'2026-10-19','windows_tests_passed':152,'linux_tests_passed':155,
         'actual_27b_turns':50,'actual_27b_named_checks_passed':5,
         'actual_27b_playback':'controlled_ack_simulation_no_audio',
         'actual_asr_llm_tts_http_before_after_process_restart':True,
         'unplayed_assistant_excluded':True,'explicit_resume_or_new_in_board_ui':True,
         'live_microphone_50_turns_verified':False,'live_listening_verified':False,
         'summary_strategy':'source_excerpts_v1_not_abstractive_summary',
         'personal_identity_memory':False,'general_forget_commands':False,
         'voice_barge_in':False,'touch_interrupt_and_speak':False,
         'model_and_audio_configs_unchanged':True,'camera_pid_preserved':deployment['camera_pid_preserved'],
         'identity_database_unchanged':deployment['database_hash_unchanged'],
         'runtime':deployment['runtime'],'host_health':health,
         'next':'Live long conversation acceptance; then controlled long-term memory and interruption'}
(HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'listening.json').write_text(json.dumps({'status':'PENDING_USER_LIVE_CONVERSATION',
    'new_recording_claimed':False,'user_feedback':None},indent=2),encoding='utf-8')
print(json.dumps({key:summary[key] for key in ('status','windows_tests_passed','linux_tests_passed','actual_27b_turns')}))
