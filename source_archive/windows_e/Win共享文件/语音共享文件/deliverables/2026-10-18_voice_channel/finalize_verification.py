"""Read-only runtime checks and a reproducible source manifest."""
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

health=json.load(urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=4))
config=json.loads((ROOT/'aura/config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
assert health['llm_model']==config['model']=='aura-qwen3.8-27b-abliterated:iq4_xs'
assert health['ready'] and health['voice_channel_protocol']=='aura-channel-1'
board=json.loads(ssh('python3 -', '''import json,urllib.request
u=json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3))
print(json.dumps({'phase':u.get('phase'),'playing':u.get('playing'),'error':u.get('error'),
                 'recording_state':u.get('local_recording',{}).get('state')}))
'''))
files=['aura/common/voice_channel.py','aura/tools/dialogue_stream.py','aura/tools/voice_channel_source.py',
       'aura/board/runtime/audio/voice_channel.py','aura/tools/board_model_host.py',
       'aura/tools/dialogue_host_ollama.py','aura/tools/probe_voice_channel.py',
       'aura/tests/framework/test_voice_channel.py']
manifest={name:{'sha256':hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),
                'bytes':(ROOT/name).stat().st_size} for name in files}
record={'status':'PASS_EXPERIMENTAL_CHANNEL_RECEIVE','tests_passed':27,'health':health,
        'board_after':board,'source_manifest':manifest,'speech_models_on_board':False,
        'board_services_or_fpga_modified':False,'production_ui_channel_enabled':False,
        'acoustic_latency_verified':False,'subsecond_achieved':False,
        'limits':['OmniVoice remains full-clause synthesis','No streaming playback acknowledgements yet',
                  'Original UI and 1-second startup protection remain','Target 5090 not tested'],
        'model_config':config}
for name in ('actual_host_probe.json','actual_board_channel.json','legacy_endpoint_after.json'):
    data=json.loads((HERE/name).read_text(encoding='utf-8'))
    record[name]={'status':data['status'],'sha256':hashlib.sha256((HERE/name).read_bytes()).hexdigest()}
(HERE/'verification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':record['status'],'health':health,'board_after':board},ensure_ascii=True))
