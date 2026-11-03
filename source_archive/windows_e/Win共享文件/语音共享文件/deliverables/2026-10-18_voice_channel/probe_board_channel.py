"""Copy transport-only code to an isolated board folder and receive real PCM.

No board service restart, playback, FPGA overlay, DPU or model changes.
"""
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

names=['aura/common/asr_wire.py','aura/common/voice_channel.py',
       'aura/board/runtime/audio/voice_channel.py','aura/tools/probe_voice_channel.py']
files={name:base64.b64encode((ROOT/name).read_bytes()).decode('ascii') for name in names}
recording=ROOT/'aura/report/recording_20261016/microphone-5s.wav'
files['data/historical.wav']=base64.b64encode(recording.read_bytes()).decode('ascii')
release=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:12]
payload={'files':files,'release':release}
remote=r'''
import base64,hashlib,json,subprocess,sys,urllib.request
from pathlib import Path
payload=PAYLOAD
root=Path('/home/root/aura-voice-channel-20261018')/('transport-'+payload['release'])
root.mkdir(parents=True,exist_ok=True)
for name,encoded in payload['files'].items():
    target=(root/name).resolve()
    if root.resolve() not in target.parents:raise ValueError('Invalid staging path')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(base64.b64decode(encoded,validate=True))
health=json.load(urllib.request.urlopen('http://192.168.50.1:8792/health',timeout=4))
if health.get('voice_channel_protocol')!='aura-channel-1':raise RuntimeError('Updated host not ready')
result=subprocess.run([sys.executable,'-B',str(root/'aura/tools/probe_voice_channel.py'),
    '--wav',str(root/'data/historical.wav'),'--rounds','2','--report',str(root/'report.json'),
    '--output',str(root/'received.wav')],capture_output=True,text=True,timeout=210)
if result.returncode:raise RuntimeError(result.stderr[-2000:])
report=json.loads((root/'report.json').read_text())
report.update(board_stage=str(root),board_services_modified=False,board_models_installed=False,
              fpga_or_dpu_modified=False,actual_playback=False,host_health=health)
print(json.dumps(report))
'''.replace('PAYLOAD',repr(payload))
result=json.loads(ssh('python3 -',remote,timeout=230))
(HERE/'actual_board_channel.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
