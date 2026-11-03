"""Prepare the confirmed direct-link ASR target without sending any recording."""
import json
from pathlib import Path
import subprocess
import urllib.request
ROOT=Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
BASE='http://127.0.0.1:8783'
def state():
    with urllib.request.urlopen(BASE+'/api/state',timeout=3) as r:return json.load(r)
before=state()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='25c4401f-471d-4383-8159-03b8bcaf480b'
assert before['local_recording']['result'] is None and before['local_recording']['can_start']
assert before['phase']=='IDLE' and not before['avatar_command_pending']
neighbors=json.loads(subprocess.check_output(['ip','-j','neigh'],text=True))
assert any(row.get('dst')=='192.168.50.1' and row.get('lladdr')=='40:c2:ba:9d:77:22' for row in neighbors)
p=subprocess.run(['python3','-B','tools/configure_board_asr.py','--host','192.168.50.1'],
                 cwd=str(ROOT/'aura'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=7)
assert p.returncode==0,p.stdout
final=state()
assert final['local_transcription']['service']['enabled']
assert final['local_transcription']['service']['host']=='192.168.50.1'
assert final['local_recording']['result'] is None and not final['local_transcription']['text']
assert final['local_recording']['can_start'] and final['phase']=='IDLE' and not final['error']
try:
    with urllib.request.urlopen('http://192.168.50.1:8791/health',timeout=2) as r:health=json.load(r)
except Exception as exc:health={'error':type(exc).__name__+': '+str(exc)}
print(json.dumps({'status':'ASR_TARGET_CONFIGURED','service_ready_verified':health.get('ready') is True,
    'health':health,'configuration_ack':json.loads(p.stdout),
    'final':{k:final[k] for k in ('ui_page','ui_layer','phase','local_recording','local_transcription','ui_settings','error')}}))
