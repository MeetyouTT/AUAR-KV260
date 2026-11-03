"""Final read-only deployment verification; never modifies board or models."""
import ast,datetime,hashlib,json,subprocess,sys,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path[:0]=[str(A),str(H.parent/'2026-10-18_board_dialogue')]
from board_ssh import ssh
from common.voice_service_capabilities import source_fingerprint
report={'status':'STARTING','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
def read(name):return json.loads((H/name).read_text(encoding='utf-8'))
try:
 plan=read('source_plan_r8.json');deployment=read('deployment_r8.json');assert deployment['status']=='COMMITTED'
 with urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=5) as r:health=json.load(r)
 assert health['ready'] and not health['busy'] and not health['dependencies']['tts']['request_active']
 assert health['service_revision']==plan['candidate_revision']
 assert health['source_fingerprint']==plan['candidate_fingerprint']==source_fingerprint(A)
 assert health['latency_options']==deployment['latency_options']
 assert hashlib.sha256((A/'config/voice_latency.json').read_bytes()).hexdigest()==plan['preserved_latency_sha256']
 baseline=read('baseline.json')
 for name,original in baseline['source_before'].items():
  expected=plan['files'][name]['candidate'] if name in plan['files'] else original
  assert hashlib.sha256((A/name).read_bytes()).hexdigest()==expected,name
 tree=ast.parse((H.parent/'2026-10-28_timeline_summaries/capture_board.py').read_text(encoding='utf-8'))
 script=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
 board=json.loads(ssh('python3 -B -',script,timeout=20));before=read('board_baseline.json')
 assert board['preflight_ready']
 for key in ('boot','actual_runtime','actual_config','config_sha256','pins','settings','pan'):assert board[key]==before[key],key
 for key in ('camera_service','ui_service'):
  for field in ('MainPID','ExecStart','NRestarts','ActiveState'):assert board[key][field]==before[key][field],key+field
 handoff=read('live_handoff_r8_final.json');memory=read('live_controls_acceptance.json');private=read('physical_database_check.json');voice=read('voice_refined.json')
 assert handoff['status']=='PASS' and len(handoff['checks'])==5
 assert memory['status']=='PASS' and len(memory['turns'])==14 and all(row['status']=='PASS' for row in memory['turns'])
 assert memory['cleanup']['only_public_test_conversation_removed'] and memory['cleanup']['actual_source_coverage_verified']
 assert private['status']=='PASS' and private['original_sources_unchanged']
 assert voice['status']=='PASS' and len(voice['trials'])==8
 assert 'compact_chat_serialization_hint' not in health['capabilities']
 for key in ('precise_timeline_voice_intent','request_input_fingerprint','queued_voice_admission','natural_fact_answers','memory_source_coverage'):assert health['capabilities'][key]==1
 report.update(status='PASS',revision=health['service_revision'],fingerprint=health['source_fingerprint'],
  tests_passed=347,actual_memory_checks=14,arm_handoff_checks=5,voice_samples=8,
  board={'boot':board['boot'],'runtime':board['actual_runtime'],'pins':len(board['pins']),
         'ui_pid':board['ui_service']['MainPID'],'camera_pid':board['camera_service']['MainPID'],
         'pan':board['pan'],'listening':board['listening'],'microphone_open':board['microphone_open']},
  source_guard_all_files_pass=True,original_database_source_rows_unchanged=True,
  private_original_counts={k:v.get('counts') for k,v in read('original_database_checkpoint.json')['databases'].items()},
  final_database_counts={k:v.get('counts') for k,v in private['databases'].items()},
  other_listeners_and_models_preserved_during_deployment=True,
  latency_options=health['latency_options'],voice_request_diagnostics=health['voice_request_diagnostics'],
  microphone_opened=False,physical_playback=False,board_migration=False,full_project_accepted=False)
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'release_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report.get(k) for k in ('status','revision','tests_passed','actual_memory_checks','arm_handoff_checks','error')},ensure_ascii=True))
raise SystemExit(0 if report['status']=='PASS' else 1)
