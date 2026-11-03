"""Save the final health, immutable source manifest and bounded handoff archive."""
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
import zipfile

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

def get(url):
    with urllib.request.urlopen(url,timeout=4) as response:return json.load(response)

summary=json.loads((HERE/'verification_summary.json').read_text(encoding='utf-8'))
health=get('http://192.168.50.1:8792/health')
assert health['latency_options']=={'reply_first':True,'early_sentence':True,'coalesce_chat':True} and health['ready']
loaded=get('http://127.0.0.1:11435/api/ps')
model=next(row for row in loaded['models'] if row['name']==summary['model'])
assert model['details']['quantization_level']=='IQ4_XS' and model['context_length']==2048
source={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in summary['source_sha256']}
summary['source_sha256']=source
for name in ('aura/board/runtime/audio/omnivoice_voice.py','aura/tools/streaming_controller.py'):
    assert (ROOT/name).read_bytes()==(HERE/'before'/name.replace('/','__')).read_bytes(),name
board=json.loads(ssh('python3 -',r'''
import json,urllib.request
from pathlib import Path
def get(port,path):
    with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=3) as response:return json.load(response)
u=get(8783,'/api/state');camera=get(8790,'/health')
print(json.dumps({'phase':u['phase'],'error':u['error'],'recording':u['local_recording']['state'],
   'audio_output_state':u['audio_output_state'],'transcription':u['local_transcription'],
   'camera_pid':camera['pid'],'board_boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}))
''',timeout=10))
assert not board['error'] and board['camera_pid']==976
status={'status':'OPTIMIZED_SERVICE_READY','host_health':health,'loaded_model':model,'board':board,
        'voice_parameters_unchanged':True,'board_controller_unchanged':True,'source_sha256':source}
live_path=HERE/'live_playback.json'
if live_path.is_file():
    live=json.loads(live_path.read_text(encoding='utf-8'))
    summary['new_user_playback']={key:value for key,value in live.items() if key not in ('final_state','samples','state')}
    if (live['status']=='PASS_NEW_USER_PRODUCTION_PLAYBACK_ACK' and
            live.get('health',{}).get('latency_options')==health['latency_options']):
        status['status']='PASS_OPTIMIZED_SERVICE_AND_NEW_USER_PLAYBACK'
summary['status']=status['status'];summary['final_health']=status
log=(HERE/'tests.log').read_text(encoding='utf-8',errors='replace')
if '74 passed' in log:summary['tests']={'passed':74,'seconds':10.55,'log':'tests.log'}
feedback=HERE/'listening_final.json'
if feedback.is_file():summary['listening']=json.loads(feedback.read_text(encoding='utf-8'))
history=json.loads((HERE/'history_comparison.json').read_text(encoding='utf-8'))
summary['memory_diagnostic']={'cases':len(history['cases']),'all_name_and_color_correct':all(row['name_and_color_correct'] for row in history['cases']),
                              'exact_history_deployed':False}
(HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'final_health.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT.parent/'语言模型分析/27B首段延迟优化_实测摘要_20261018.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
with zipfile.ZipFile(HERE/'optimized_source.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for name in source:archive.write(ROOT/name,name)
    for path in (HERE/'before').iterdir():archive.write(path,'before/'+path.name)
    for path in HERE.iterdir():
        if path.suffix in ('.py','.ps1','.md','.json','.log'):archive.write(path,'evidence/'+path.name)
print(json.dumps({'status':status['status'],'camera_pid':board['camera_pid'],'source_files':len(source),
                  'zip_bytes':(HERE/'optimized_source.zip').stat().st_size,'host_busy':health['busy']},ensure_ascii=True))
