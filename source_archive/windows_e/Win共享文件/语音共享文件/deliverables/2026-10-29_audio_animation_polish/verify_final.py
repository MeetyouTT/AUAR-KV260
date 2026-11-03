"""Loaded endpoints, actual source pins, model ownership and data evidence."""
import concurrent.futures,datetime,hashlib,json,socket,sys,urllib.request,xml.etree.ElementTree as ET
from board_guard import H,A,capture
sys.path[:0]=[str(A),str(H.parent/'2026-10-29_service_recovery')]
from recovery_common import windows
from common import frontend_wire,portrait_wire
from common.voice_service_capabilities import require_current_voice,source_fingerprint
def read(name):return json.loads((H/name).read_text(encoding='utf-8-sig'))
def http(port,host='192.168.50.1',path='/health'):
    with urllib.request.urlopen('http://'+host+':'+str(port)+path,timeout=5) as r:return json.load(r)
def binary(port,wire,bound):
    with socket.create_connection(('192.168.50.1',port),timeout=3) as connection:
        wire.send(connection,{'protocol':wire.PROTOCOL,'kind':'health'});v,data=wire.receive(connection,bound)
    assert not data and v['ready'] and v['protocol']==wire.PROTOCOL
    return v
report=dict(status='CHECKING',checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),full_project_complete=False,
 microphone_enabled=False,audible_playback=False,motion_command_sent=False)
try:
    c=read('candidate.json');b=read('preflight.json');before=read('windows_before.json')
    for name in ('native_ipc_comparison.json','native_visual.json','renderer_before.json','renderer_after.json',
                 'muted_live_probe.json','live_ui_outage.json','database_verification.json'):
        assert read(name)['status']=='PASS',name
    assert read('deployment.json')['status']=='COMMITTED'
    current=capture();assert current['safe'] and not current['mismatches']
    assert current['actual_runtime']==c['runtime'] and current['actual_config']==c['startup']+'/config.json'
    assert current['pins']==c['pins'] and current['state']['portrait_offload']['mode']=='remote'
    for key in ('boot','mechanical_sha256','settings','firmware','fdt_sha256','vart'):assert current[key]==b[key],key
    for key in ('MainPID','ExecStart','NRestarts'):assert current['camera'][key]==b['camera'][key],key
    assert current['state']['camera_epoch']==b['state']['camera_epoch']
    assert current['pan']['pulse_us']==b['pan']['pulse_us'] and current['pan']['automatic_following'] is False
    assert current['pending_launcher_sha256']==b['pending_launcher_sha256']
    source=read('source_installation.json')
    for name,item in source['files'].items():assert hashlib.sha256((A.parent/name).read_bytes()).hexdigest()==item['after'],name
    assert source_fingerprint(A)==source['voice_fingerprint_before']==source['voice_fingerprint_after']
    assert hashlib.sha256((A/'config/model_storage.local.json').read_bytes()).hexdigest()==before['model_storage_sha256']
    jobs={'asr':lambda:http(8791),'voice':lambda:http(8792),'visual':lambda:http(8810,'127.0.0.1'),
      'memory':lambda:http(8812,'127.0.0.1'),'frontend':lambda:binary(8795,frontend_wire,2),
      'portrait':lambda:binary(8796,portrait_wire,0),'ollama':lambda:http(11435,'127.0.0.1','/api/ps')}
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
        futures={key:pool.submit(job) for key,job in jobs.items()};values={key:job.result() for key,job in futures.items()}
    assert values['asr']['ready'] and values['asr']['protocol']=='aura-asr-1'
    config=json.loads((A/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
    require_current_voice(values['voice'],config['model'],source_fingerprint(A));assert not values['voice']['busy']
    assert values['voice']['latency_options']['compact_grammar'] is False
    assert values['visual']['status']=='ok' and values['memory']['revision']=='device-timeline-v2' and values['memory']['speaker_ready']
    assert values['portrait']['revision']==c['revision']
    (H/'endpoints.json').write_text(json.dumps({'status':'PASS','services':values},ensure_ascii=False,indent=2),encoding='utf-8')
    win=windows()
    assert all(row in win['models'] for row in before['windows']['models']),'Existing model process changed'
    def listeners(rows):return sorted((r['LocalAddress'],r['LocalPort'],r['OwningProcess']) for r in rows if r['LocalPort']!=8796)
    assert listeners(win['listeners'])==listeners(before['windows']['listeners']),'An unrelated listener changed'
    tests={}
    for label,name in [('audio','audio_tests_verified.xml'),('visual','visual_tests.xml'),('portrait','portrait_tests.xml')]:
        suites=ET.parse(H/name).getroot();suite=suites if suites.tag=='testsuite' else suites.find('testsuite')
        assert int(suite.attrib.get('failures',0))==0 and int(suite.attrib.get('errors',0))==0
        tests[label]={key:int(suite.attrib.get(key,0)) for key in ('tests','failures','errors','skipped')}
    report.update(status='PASS',voice_revision=values['voice']['service_revision'],voice_fingerprint=source_fingerprint(A),
      portrait_revision=c['revision'],services_ready=list(values),tests=tests,board=current,
      actual_muted_audio=read('muted_live_probe.json')['audio_diagnostics'],
      actual_ui_outage={key:value for key,value in read('live_ui_outage.json').items() if key!='rows'},
      original_model_processes_preserved=True,unrelated_service_pids_preserved=True,windows_after=win,
      source_fingerprint_voice_unchanged=True,model_storage_unchanged=True,
      original_memory_sources_unchanged=read('database_verification.json')['conversation_visual_archive_speaker_sources_unchanged'],
      strict_memory_source_equality=read('database_verification.json')['strict_source_equality'],
      human_audio_acceptance='PENDING',speaking_strict_16fps='NOT_PASSED; measured median p95~80ms and p99~158ms',
      motion_state='ORIGINAL_FAULT_PROTECTION_PRESERVED')
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({key:report.get(key) for key in ('status','voice_revision','portrait_revision','tests','original_model_processes_preserved',
 'unrelated_service_pids_preserved','strict_memory_source_equality','human_audio_acceptance','motion_state','error')}))
raise SystemExit(0 if report['status']=='PASS' else 1)
