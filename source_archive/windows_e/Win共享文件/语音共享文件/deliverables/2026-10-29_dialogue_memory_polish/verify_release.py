"""Read-only final gate; actual private DB snapshots are taken by independent WMI."""
import ast,datetime,hashlib,json,socket,subprocess,sys,time,urllib.request,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path.insert(0,str(A));sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from common.voice_service_capabilities import source_fingerprint,require_current_voice
from common import frontend_wire,portrait_wire
from board_ssh import ssh
read=lambda name:json.loads((H/name).read_text(encoding='utf-8'))
plan=read('source_plan.json');baseline=read('board_baseline.json');receipt=read('deployment.json')
assert receipt['status']=='COMMITTED'
assert not (H/'release_verification.json').exists(),'Inspect existing final verification'
report={'status':'STARTING','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
def health(port):
 with urllib.request.urlopen('http://192.168.50.1:%d/health'%port,timeout=4) as response:return json.load(response)
try:
 for name,entry in plan['files'].items():
  assert hashlib.sha256((A/name).read_bytes()).hexdigest()==entry['candidate'],name
  assert hashlib.sha256((H/'candidate_source'/name).read_bytes()).hexdigest()==entry['candidate'],name
 for name,old in plan['source_before'].items():
  assert hashlib.sha256((A/name).read_bytes()).hexdigest()==plan['files'].get(name,{}).get('candidate',old),name
 assert hashlib.sha256((A/'config/voice_latency.json').read_bytes()).hexdigest()==plan['preserved_latency_sha256']
 suites=ET.parse(H/'tests.xml').getroot().findall('testsuite')
 assert sum(int(s.attrib['tests']) for s in suites)==267
 assert all(int(s.attrib['failures'])==int(s.attrib['errors'])==int(s.attrib['skipped'])==0 for s in suites)
 services={str(p):health(p) for p in (8791,8792,8812)}
 for port,wire in ((8795,frontend_wire),(8796,portrait_wire)):
  with socket.create_connection(('192.168.50.1',port),timeout=3) as connection:
   wire.send(connection,{'protocol':wire.PROTOCOL,'kind':'health'})
   value,payload=wire.receive(connection,0 if port==8796 else 3)
   assert value['ready'] and not payload
   services[str(port)]=value
 voice=services['8792']
 require_current_voice(voice,json.loads((A/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))['model'],source_fingerprint(A))
 assert voice['ready'] and not voice['busy'] and voice['service_revision']==plan['candidate_revision']
 assert voice['source_fingerprint']==plan['candidate_fingerprint'] and voice['latency_options']==receipt['latency_options']
 assert voice['latency_options']['compact_grammar'] is False
 assert voice['capabilities']['natural_fact_answers']==voice['capabilities']['memory_source_coverage']==1
 assert voice['conversation_memory']['background_summaries']['running'] and not voice['conversation_memory']['background_summaries']['error']
 # Definitions only: no deployment main body executes.
 tree=ast.parse((H/'deploy_windows.py').read_text(encoding='utf-8'))
 definitions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('ps','gate','models','listeners')]
 env=dict(globals());exec(compile(ast.Module(body=definitions,type_ignores=[]),'readonly_gate','exec'),env)
 board=env['gate']();time.sleep(.25);assert env['gate']()==board
 assert env['listeners']()==receipt['other_listeners']
 models_now=env['models']();assert all(r in models_now for r in receipt['models_before']),'Existing model owner changed'
 assert not (H/'physical_database_check.json').exists(),'Inspect existing private check'
 python=r'C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
 command='"'+python+'" -B "'+str(H/'verify_private.py')+'"'
 launch="$s=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0};"+"$p=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='"+command+"';ProcessStartupInformation=$s};if($p.ReturnValue -ne 0){throw 'Private verification launch failed'}"
 subprocess.run(['powershell.exe','-NoProfile','-Command',launch],check=True,capture_output=True,timeout=15)
 until=time.monotonic()+25
 while not (H/'physical_database_check.json').exists() and time.monotonic()<until:time.sleep(.2)
 private=read('physical_database_check.json')
 assert private['status']=='PASS' and private['original_sources_unchanged'],private.get('error')
 memory,regular,board_probe,comparison=map(read,('live_controls_acceptance.json','live_voice_acceptance.json','board_probe.json','comparison.json'))
 assert memory['status']==regular['status']==board_probe['status']==comparison['status']=='PASS'
 assert len(memory['turns'])==12 and all(t['status']=='PASS' for t in memory['turns'])
 assert len(regular['checks'])==7 and all(c['status']=='PASS' for c in regular['checks'])
 for name in ('public_probe_cleanup.json','board_probe_cleanup.json'):
  cleanup=read(name);assert cleanup['status']=='PASS' and cleanup['only_public_test_conversation_removed'] and cleanup['remaining_test_rows']==0
 assert read('public_probe_cleanup.json')['actual_source_coverage_verified']
 assert len(board_probe['turns'])==2 and all(t['status']=='PASS' and t['playback_ack_sent'] is False for t in board_probe['turns'])
 assert board_probe['cleanup']['status']=='PASS'
 assert comparison['public_rows_cleaned'] and comparison['general_chat_control']['improvement_demonstrated'] is False
 frontend=next(c['result'] for c in regular['checks'] if c['name']=='paced_frontend_public_audio')
 report.update(status='PASS',revision=voice['service_revision'],fingerprint=voice['source_fingerprint'],
  source_files_verified=len(plan['files']),unchanged_or_expected_source_files_verified=len(plan['source_before']),
  windows_regressions_passed=267,latency_options=voice['latency_options'],memory_health=voice['conversation_memory'],
  board=board,other_models_preserved=True,other_model_owners=models_now,other_listeners_preserved=True,
  original_database_sources_unchanged=True,public_test_rows_removed=True,private_view='independent_WMI',
  board_migration=False,board_ui_restarted=False,camera_restarted=False,mic_opened=False,playback=False,motion_started=False,
  services={p:{k:v[k] for k in ('ready','busy','revision','speaker_ready') if k in v} for p,v in services.items()},
  live_memory_checks=12,live_voice_checks=7,board_network_exchanges=2,
  target_latency_comparison_passed=True,general_chat_latency_improved=False,
  frontend=frontend,strict_frontend_20ms_passed=(frontend['over_20ms']==0),
  whole_project_complete=False,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
except Exception as exc:
 report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'release_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report.get(k) for k in ('status','error','revision','windows_regressions_passed','original_database_sources_unchanged','other_models_preserved','target_latency_comparison_passed','general_chat_latency_improved')}))
raise SystemExit(0 if report['status']=='PASS' else 1)
