"""Readiness and anonymous public-WAV checks; no personal records are created."""
import http.client,json,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;AURA=HERE.parents[1]/'aura'
sys.path.insert(0,str(AURA))
from common.voice_service_capabilities import source_fingerprint,require_current_voice
from tools.profile_cli import control,key_path
from tools.probe_voice_channel import probe
c=http.client.HTTPConnection('192.168.50.1',8792,timeout=3)
try:
    c.request('GET','/health');r=c.getresponse();health=json.loads(r.read(32768));assert r.status==200
finally:c.close()
fingerprint=source_fingerprint(AURA)
config=json.loads((AURA/'config/board_dialogue_model.json').read_text(encoding='utf-8-sig'))
require_current_voice(health,config['model'],fingerprint)
assert health['profile_access']['configured'] and health['profile_access']['automatic_speaker_unlock'] is False
assert health['conversation_memory']['personal_identity_memory'] is True
profiles=control('192.168.50.1',8792,key_path().read_text(encoding='utf-8').strip(),{'action':'list'})
value={'health_ready':True,'source_fingerprint':fingerprint,'profile_access':health['profile_access'],
       'profile_count':len(profiles['profiles']),'personal_records_created_by_check':False,
       'recorded_unix':time.time()}
(HERE/'runtime_verification.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
received=probe('192.168.50.1',8792,AURA/'models/asr/sherpa-onnx-paraformer-zh-2023-09-14/test_wavs/0.wav',rounds=1)
(HERE/'public_voice_after_upgrade.json').write_text(json.dumps(received,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':'PASS','source_fingerprint':fingerprint,'profile_control_configured':True,
                  'personal_records_created':False,'public_voice_network_complete':received['turns'][0]['result']['network_complete']}))
