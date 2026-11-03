"""Final non-biometric service/source/ownership audit. Never enrolls or plays."""
import concurrent.futures,datetime,hashlib,json,ntpath,socket,sys,urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1];A=P/'aura'
sys.path[:0]=[str(A),str(H.parent/'2026-10-29_audio_animation_polish'),str(H.parent/'2026-10-29_service_recovery')]
from board_guard import capture,same
from recovery_common import windows,powershell
from common import frontend_wire,portrait_wire
from common.voice_service_capabilities import require_current_voice,source_fingerprint

def read(name):return json.loads((H/name).read_text(encoding='utf-8-sig'))
def http(port,host='192.168.50.1',path='/health'):
 with urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=5) as response:return json.load(response)
def binary(port,wire,bound):
 with socket.create_connection(('192.168.50.1',port),timeout=3) as connection:
  wire.send(connection,{'protocol':wire.PROTOCOL,'kind':'health'});value,data=wire.receive(connection,bound)
 assert not data and value['ready'] and value['protocol']==wire.PROTOCOL
 return value
def process_record(pid):
 command=r"""[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false)
$auditProcess=Get-CimInstance Win32_Process -Filter 'ProcessId = PID_VALUE'
if (-not $auditProcess) {throw 'Expected process missing'}
[pscustomobject]@{pid=[int]$auditProcess.ProcessId;creation_utc=$auditProcess.CreationDate.ToUniversalTime().ToString('o');
exe=$auditProcess.ExecutablePath;command_line=$auditProcess.CommandLine} | ConvertTo-Json -Compress
""".replace('PID_VALUE',str(int(pid)))
 return json.loads(powershell(['-Command',command]))
def owner_matches(old,current):
 assert old['pid']==current['pid'] and old['creation_utc']==current['creation_utc'],'PID/creation changed'
 assert ntpath.normcase(old.get('exe',old.get('executable')))==ntpath.normcase(current['exe']),'Executable changed'
 assert old['command_line']==current['command_line'],'Command line changed'

report=dict(status='CHECKING',checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 full_project_complete=False,identity_network_acceptance='AWAITING_EXPLICIT_APPROVAL',
 microphone_enabled=False,audible_playback=False,motion_command_sent=False)
try:
 baseline=read('baseline.json');manifest=read('final_manifest.json');candidate=read('board_candidate.json')
 assert read('final_installation.json')['status']=='INSTALLED_FINAL'
 assert read('final_ready_fixed.json')['status']=='READY'
 assert read('board_deployment.json')['status']=='COMMITTED'
 assert read('public_gpu_final_adaptive.json')['status']=='PASS'
 assert len(read('public_gpu_final_adaptive.json')['checks'])==3
 assert all(v['tts_cache_hits']==0 for v in read('public_gpu_final_adaptive.json')['checks'])
 assert read('arm_transport_verification.json')['status']=='PASS'
 assert read('database_verification.json')['status']=='PASS'
 assert read('database_verification.json')['strict_source_equality']
 source_hashes={name:hashlib.sha256((A/name).read_bytes()).hexdigest() for name in manifest['files']}
 assert all(source_hashes[name]==value['sha256'] for name,value in manifest['files'].items())
 assert len(source_hashes)==46 and source_fingerprint(A)==manifest['fingerprint']
 assert hashlib.sha256((A/'config/model_storage.local.json').read_bytes()).hexdigest()==baseline['model_storage_sha256']
 board=capture();assert board['safe'] and not board['mismatches']
 assert board['actual_runtime']==candidate['runtime'] and board['pins']==candidate['pins'] and len(board['pins'])==286
 assert board['actual_config']==candidate['startup']+'/config.json' and board['pending_config']==board['actual_config']
 assert board['state']['portrait_offload']['mode']=='remote'
 for key in ('boot','mechanical_sha256','settings','firmware','fdt_sha256','vart','pending_launcher_sha256'):
  assert board[key]==baseline['board'][key],key
 for key in ('MainPID','ExecStart','NRestarts','ActiveState','DropInPaths'):
  assert board['camera'][key]==baseline['board']['camera'][key],'Camera '+key
 assert board['state']['camera_epoch']==baseline['board']['state']['camera_epoch']
 assert board['pan']['state']=='FAULT' and board['pan']['pulse_us'] is None and board['pan']['target_us'] is None
 changed=sorted(name for name,sha in baseline['board']['pins'].items() if board['pins'][name]!=sha)
 assert changed==['board/runtime/audio/channel_jobs.py','board/runtime/audio/voice_channel.py']
 assert len(set(board['pins'])-set(baseline['board']['pins']))==7
 jobs={'asr':lambda:http(8791),'voice':lambda:http(8792),'visual':lambda:http(8810,'127.0.0.1'),
  'memory':lambda:http(8812,'127.0.0.1'),'frontend':lambda:binary(8795,frontend_wire,2),
  'portrait':lambda:binary(8796,portrait_wire,0),'project_ollama':lambda:http(11435,'127.0.0.1','/api/ps')}
 with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
  futures={name:pool.submit(job) for name,job in jobs.items()};endpoints={name:f.result() for name,f in futures.items()}
 assert endpoints['asr']['ready'] and endpoints['asr']['protocol']=='aura-asr-1'
 config=json.loads((A/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
 require_current_voice(endpoints['voice'],config['model'],manifest['fingerprint'])
 assert endpoints['voice']['service_revision']==manifest['revision'] and not endpoints['voice']['busy']
 assert endpoints['voice']['gpu_coordination']['mode']=='adaptive' and endpoints['voice']['gpu_coordination']['enforcing']
 assert endpoints['voice']['cold_startup']['capacity_verified'] and not endpoints['voice']['cold_startup']['automatic_unload']
 assert endpoints['voice']['latency_options']['compact_grammar'] is False
 assert endpoints['memory']['speaker_ready'] and endpoints['memory']['anonymous_binding']['enabled']
 assert endpoints['memory']['speaker_calibrated'] is False and endpoints['memory']['automatic_profile_access'] is False
 assert endpoints['visual']['status']=='ok'
 assert endpoints['portrait']['revision']=='763d0b05a67a79ff6f8a6d9d5e2a67cc9cc060181499cef7a416bccdf7315bac'
 win=windows();assert win['last_boot']==baseline['windows']['last_boot']
 old_project_pid=read('runtime_owners_before.json')['11435']['pid']
 preserved=[row for row in baseline['windows']['models'] if row['ProcessId']!=old_project_pid]
 assert all(row in win['models'] for row in preserved),'Unrelated model process changed'
 owned_ports={8792,8812,11435}
 def unrelated(rows):return sorted((r['LocalAddress'],r['LocalPort'],r['OwningProcess']) for r in rows if r['LocalPort'] not in owned_ports)
 assert unrelated(win['listeners'])==unrelated(baseline['windows']['listeners']),'Unrelated listener changed'
 records=dict(read('service_processes.json'))
 project_record=json.loads((P/'deliverables/2026-10-18_board_dialogue/project_ollama_process.json').read_text(encoding='utf-8-sig'))
 records['11435']=project_record['ownership'];records['11434']=read('runtime_owners_before.json')['11434']
 actual_owners={port:process_record(record['pid']) for port,record in records.items()}
 for port,record in records.items():
  owner_matches(record,actual_owners[port])
  assert any(r['LocalPort']==int(port) and r['OwningProcess']==record['pid'] for r in win['listeners']),port
 assert project_record['runtime_policy']['fit_target_mib']==4096
 assert hashlib.sha256((A/'config/ollama_runtime.local.json').read_bytes()).hexdigest()==project_record['runtime_policy']['config_sha256']
 xml=ET.parse(H/'final_tests.xml').getroot();suite=xml if xml.tag=='testsuite' else xml.find('testsuite')
 tests={key:int(suite.attrib.get(key,0)) for key in ('tests','failures','errors','skipped')}
 assert tests=={'tests':637,'failures':0,'errors':0,'skipped':0}
 after=capture();same(board,after)
 report.update(status='PASS',acceptance_scope='available_non_biometric_automated_checks',voice_revision=manifest['revision'],
  voice_fingerprint=manifest['fingerprint'],source_files=46,source_hashes=source_hashes,tests=tests,board=after,
  endpoints=endpoints,windows_after=win,actual_owners=actual_owners,
  other_model_processes_preserved=True,unrelated_service_pids_preserved=True,model_storage_unchanged=True,
  original_memory_sources_unchanged=True,strict_memory_source_equality=True,
  changed_original_board_components=changed,added_board_components=7,
  observed_min_free_mib=read('public_gpu_final_adaptive.json')['observed_min_free_mib'],
  human_identity_acceptance='PENDING',human_audio_acceptance='PENDING',
  speaking_strict_16fps='NOT_PASSED_IN_PRIOR_MEASUREMENT',motion_state='ORIGINAL_FAULT_PROTECTION_PRESERVED')
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({key:report.get(key) for key in ('status','acceptance_scope','voice_revision','tests','other_model_processes_preserved',
 'unrelated_service_pids_preserved','strict_memory_source_equality','observed_min_free_mib','identity_network_acceptance','error')}))
raise SystemExit(0 if report['status']=='PASS' else 1)
