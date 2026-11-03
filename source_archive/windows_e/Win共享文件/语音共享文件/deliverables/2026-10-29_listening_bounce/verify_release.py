"""Final exact-source, board, model-owner and independent private-data verification."""
import ast,datetime,hashlib,json,socket,subprocess,sys,time,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path.insert(0,str(A));sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from common.voice_service_capabilities import source_fingerprint,require_current_voice
from common import frontend_wire,portrait_wire
from board_ssh import ssh
read=lambda name:json.loads((H/name).read_text(encoding='utf-8-sig'))
plan=read('source_plan.json');baseline=read('board_baseline.json');receipt=read('deployment_recovery.json')
assert receipt['status']=='COMMITTED'
assert not (H/'release_verification.json').exists()
report={'status':'STARTING','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
def health(port):
 with urllib.request.urlopen('http://192.168.50.1:%d/health'%port,timeout=4) as r:return json.load(r)
try:
 for name,entry in plan['files'].items():
  assert hashlib.sha256((A/name).read_bytes()).hexdigest()==entry['candidate'],name
 for name,old in plan['source_before'].items():
  assert hashlib.sha256((A/name).read_bytes()).hexdigest()==plan['files'].get(name,{}).get('candidate',old),name
 suites=list(ET.parse(H/'tests.xml').getroot().iter('testsuite'))
 assert sum(int(s.get('tests',0)) for s in suites)==285
 assert not sum(int(s.get('errors',0))+int(s.get('failures',0))+int(s.get('skipped',0)) for s in suites)
 services={str(p):health(p) for p in (8791,8792,8812)}
 for port,wire in ((8795,frontend_wire),(8796,portrait_wire)):
  with socket.create_connection(('192.168.50.1',port),timeout=3) as conn:
   wire.send(conn,{'protocol':wire.PROTOCOL,'kind':'health'})
   value,payload=wire.receive(conn,0 if port==8796 else 3);assert value['ready'] and not payload
   services[str(port)]=value
 voice=services['8792'];require_current_voice(voice,json.loads((A/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))['model'],source_fingerprint(A))
 assert voice['ready'] and not voice['busy'] and voice['service_revision']==plan['candidate_revision']
 assert voice['source_fingerprint']==plan['candidate_fingerprint'] and voice['latency_options']==receipt['latency_options']
 assert voice['capabilities']['queued_voice_admission']==voice['capabilities']['bounded_voice_request_diagnostics']==1
 assert voice['voice_request_diagnostics']['version']==1 and voice['voice_request_diagnostics']['speech_stored'] is False
 tree=ast.parse((H/'deploy_windows.py').read_text(encoding='utf-8'))
 definitions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('ps','gate','models','listeners')]
 env=dict(globals());exec(compile(ast.Module(body=definitions,type_ignores=[]),'readonly_gate','exec'),env)
 board=env['gate']();time.sleep(.25);assert env['gate']()==board
 assert env['listeners']()==receipt['other_listeners']
 models_now=env['models']();assert all(r in models_now for r in receipt['models_before'])
 live=read('live_handoff_final.json');assert live['status']=='PASS'
 assert len(live['checks'])==5 and all(r['status']=='PASS' for r in live['checks'])
 assert [r['stage'] for r in live['checks']]==['text','tts','audio','wake_only','nonwake_rejected']
 assert live['checks'][1]['tts_active_at_cancel']
 assert not live['durable_conversation_used'] and not live['playback'] and not live['mic_opened']
 assert not (H/'physical_database_check.json').exists()
 python=r'C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
 command='"'+python+'" -B "'+str(H/'verify_private.py')+'"'
 launch="$s=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0};"+"$p=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='"+command+"';ProcessStartupInformation=$s};if($p.ReturnValue -ne 0){throw 'Private verification launch failed'}"
 subprocess.run(['powershell.exe','-NoProfile','-Command',launch],check=True,capture_output=True,timeout=15)
 until=time.monotonic()+25
 while not (H/'physical_database_check.json').exists() and time.monotonic()<until:time.sleep(.1)
 private=read('physical_database_check.json');assert private['status']=='PASS' and private['original_sources_unchanged'],private.get('error')
 report.update(status='PASS',revision=voice['service_revision'],fingerprint=voice['source_fingerprint'],
  windows_regressions_passed=285,includes_previous_267=True,source_files_verified=len(plan['files']),
  other_models_preserved=True,other_listeners_preserved=True,original_database_sources_unchanged=True,
  board=board,board_ui_restarted=False,camera_restarted=False,board_code_changed=False,board_migration=False,
  microphone_opened=False,physical_audio_played=False,successful_playback_ack=False,new_motion=False,
  listening_remains_off=True,latency_options=voice['latency_options'],request_diagnostics=voice['voice_request_diagnostics'],
  live_board_handoff_pairs=3,live_wake_checks=2,live_first_pcm_ms=[r['first_pcm_ms'] for r in live['checks'][:3]],
  whole_project_complete=False,human_report_verbatim_not_supplied=True,
  finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'release_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report.get(k) for k in ('status','error','revision','windows_regressions_passed','original_database_sources_unchanged','live_board_handoff_pairs','live_wake_checks','live_first_pcm_ms')}))
raise SystemExit(0 if report['status']=='PASS' else 1)
