"""Finalize only allowlisted source/report artifacts; no models or user data."""
import datetime,hashlib,http.client,json,socket,sys,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1];AURA=ROOT/'aura'
sys.path.insert(0,str(AURA))
from common.voice_service_capabilities import source_fingerprint,require_current_voice
from common.frontend_wire import PROTOCOL,send,receive
def health(port):
    c=http.client.HTTPConnection('192.168.50.1',port,timeout=2)
    try:
        c.request('GET','/health');r=c.getresponse();v=json.loads(r.read(32768))
        assert r.status==200 and v.get('ready') is True
        return v
    finally:c.close()
fingerprint=source_fingerprint(AURA)
config=json.loads((AURA/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
asr=health(8791);voice=health(8792);require_current_voice(voice,config['model'],fingerprint)
assert voice.get('busy') is False
with socket.create_connection(('192.168.50.1',8795),timeout=2) as c:
    send(c,{'protocol':PROTOCOL,'kind':'health'});frontend,pcm=receive(c,2)
    assert not pcm and frontend.get('ready') is True
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
final={'recorded_utc':stamp,'ready':True,'asr':{'ready':True,'model_id':asr['model_id']},
       'voice':{'ready':True,'busy':False,'service_revision':voice['service_revision'],
                'source_fingerprint':fingerprint,'capabilities':voice['capabilities'],
                'tts':voice['dependencies']['tts'],'memory_scope':voice['conversation_memory']['scope'],
                'personal_identity_memory':voice['conversation_memory']['personal_identity_memory']},
       'frontend':frontend}
(HERE/'final_runtime.json').write_text(json.dumps(final,ensure_ascii=False,indent=2),encoding='utf-8')
sources=[x['path'] for x in json.loads((HERE/'baseline.json').read_text(encoding='utf-8'))['sources']]
sources+=['aura/'+p for p in ('tools/voice_worker_transport.py','tools/owned_speech_process.py',
    'tools/voice_service_health.py','common/voice_service_capabilities.py',
    'tests/framework/test_voice_worker_lifecycle.py','tests/framework/test_voice_service_health.py',
    'tests/framework/test_voice_stack_startup.py')]
entries={}
for name in sources:entries['windows/'+name]=ROOT/name
for p in (HERE/'before').rglob('*'):
    if p.is_file():entries['before/'+p.relative_to(HERE/'before').as_posix()]=p
for p in (HERE/'pan_candidate').rglob('*'):
    if p.is_file() and (p.suffix in ('.py','.json') or p.name.startswith(('LICENSE','baseline_SOURCE'))):
        entries['pan_candidate/'+p.relative_to(HERE/'pan_candidate').as_posix()]=p
for name in ('README.md','PROGRESS.json','final_runtime.json','voice_final2.xml','voice_final2.log',
    'live_voice_acceptance.json','board_live_voice.json','board_audio_auto.json','speaker_auto_tests.json',
    'motion_board_fake_device.json','validate_voice.py','live_voice_acceptance.py','board_auto_tests.py',
    'board_live_voice.py','board_audio_auto.py','speaker_auto_tests.py','finalize_report.py'):
    entries['evidence/'+name]=HERE/name
assert all(p.is_file() and p.stat().st_size<2_000_000 for p in entries.values())
manifest={n:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for n,p in sorted(entries.items())}
(HERE/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
package=HERE/'source_and_acceptance.zip'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
    for name,p in sorted(entries.items()):z.write(p,name)
    z.write(HERE/'SOURCE_MANIFEST.json','SOURCE_MANIFEST.json')
with zipfile.ZipFile(package) as z:
    assert z.testzip() is None
    for name,meta in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==meta['sha256']
print(json.dumps({'status':'READY_AND_SOURCE_PACKAGE_VERIFIED','files':len(manifest),
                  'package_bytes':package.stat().st_size,'source_fingerprint':fingerprint}))
