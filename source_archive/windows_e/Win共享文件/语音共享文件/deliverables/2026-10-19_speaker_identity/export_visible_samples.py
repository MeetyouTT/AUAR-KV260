"""Retrieve only the four explicitly click-collected board samples to the PC."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import wave

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
sid=json.loads((HERE/'visible_sampler_deployment.json').read_text(encoding='utf-8'))['session_id']
script='''import base64,json,pathlib
directory=pathlib.Path.home()/'.local/share/aura/speaker_test_recordings'/SESSION
state=json.loads((directory/'sampler_state.json').read_text())
result={'state':state['status'],'clips':[]}
if len(state['clips'])==4 and not state['microphone_open']:
    for number in (1,2,3,4):
        path=directory/('clip-%02d.wav'%number)
        result['clips'].append({'metadata':json.loads(path.with_suffix('.json').read_text()),
                                'wav_base64':base64.b64encode(path.read_bytes()).decode('ascii')})
print(json.dumps(result))
'''.replace('SESSION',repr(sid))
value=json.loads(ssh('python3 -',script,timeout=20))
if len(value['clips'])!=4:
    print(json.dumps({'state':'PENDING_USER_CAPTURE','board_state':value['state']}));raise SystemExit(2)
directory=ROOT/'声纹测试录音'/sid;directory.mkdir(parents=True,exist_ok=True)
report=[]
for index,row in enumerate(value['clips'],1):
    meta=row['metadata'];raw=base64.b64decode(row['wav_base64'],validate=True)
    if meta['session_id']!=sid or meta['clip_number']!=index or hashlib.sha256(raw).hexdigest()!=meta['wav_sha256']:
        raise ValueError('Unexpected recording or transport mismatch')
    path=directory/('clip-%02d.wav'%index)
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('Never overwrite different recording bytes')
    else:
        with path.open('xb') as output:output.write(raw)
    with wave.open(str(path)) as audio:
        if (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())!=(16000,1,2):raise ValueError('Unexpected audio format')
        pcm=audio.readframes(audio.getnframes())
    if hashlib.sha256(pcm).hexdigest()!=meta['pcm_sha256']:raise ValueError('PCM mismatch')
    path.with_suffix('.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    report.append({'clip':index,'wav_sha256':meta['wav_sha256'],'duration_seconds':meta['duration_seconds']})
config=json.loads((HERE/'actual_experiment.json').read_text(encoding='utf-8'))
config.update(session_id=sid,capture_method='VISIBLE_BOARD_USER_CLICK',capture_duration_seconds=10)
(HERE/'actual_experiment_visible.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'visible_samples_export.json').write_text(json.dumps({'state':'EXPORTED_VERIFIED','session_id':sid,'clips':report},indent=2),encoding='utf-8')
print(json.dumps({'state':'EXPORTED_VERIFIED','session_id':sid,'clips':report}))
