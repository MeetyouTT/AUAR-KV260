"""Stage an existing synthetic OmniVoice clip without opening any device."""
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
candidate = json.loads((HERE / 'candidate.json').read_text(encoding='utf-8'))
clips = []
for path in (ROOT / 'deliverables/2026-10-21_response_latency').glob('profile_*/voice/cache/*.json'):
    value = json.loads(path.read_text(encoding='utf-8'))
    if value['identity'].get('engine') == 'omnivoice':
        clips.append((abs(value['duration_seconds']-9), path.with_suffix('.wav'), value))
_, wave, clip = min(clips, key=lambda row: row[0])
audio = wave.read_bytes()
assert hashlib.sha256(audio).hexdigest() == clip['sha256']
payload = {'stage':candidate['stage'], 'probe':base64.b64encode((HERE/'verified_acoustic_probe.py').read_bytes()).decode(),
           'audio':base64.b64encode(audio).decode(), 'sha256':clip['sha256'], 'text':clip['identity']['text']}
remote = 'payload = ' + repr(payload) + '\n' + r'''
import base64,hashlib,json
from pathlib import Path
stage=Path(payload['stage'])
probe=stage/'verified_acoustic_probe.py';probe.write_bytes(base64.b64decode(payload['probe']))
wave=stage/'probe-selected-omnivoice.wav';wave.write_bytes(base64.b64decode(payload['audio']))
assert hashlib.sha256(wave.read_bytes()).hexdigest()==payload['sha256']
(stage/'probe_clip.json').write_text(json.dumps({'path':str(wave),'sha256':payload['sha256'],'text':payload['text']}))
print(json.dumps({'prepared':True,'probe_sha256':hashlib.sha256(probe.read_bytes()).hexdigest(),
 'audio_sha256':payload['sha256'],'no_device_opened':True}))
'''
result = json.loads(ssh('python3 -B -', remote, timeout=15))
(HERE/'probe_prepared.json').write_text(json.dumps(result,indent=2), encoding='utf-8')
source = (ROOT/'deliverables/2026-10-20_listening_timing/activate.py').read_text(encoding='utf-8')
source = source.replace('zz-aura-listening-timing-20261020.conf', 'zzzz-aura-echo-verify-20261021.conf')
needle = " subprocess.run(['systemctl','stop','aura-avatar-ui.service'],check=True,timeout=40)\n"
assert source.count(needle) == 1
insert = """ probe_run=subprocess.run(['python3','-B',str(stage/'verified_acoustic_probe.py'),str(root),str(stage/'probe_clip.json')],capture_output=True,text=True,timeout=35)
 (stage/'verified_acoustic_probe.log').write_text(probe_run.stdout+probe_run.stderr)
 probe_rows=[json.loads(line[len('VERIFIED_PROBE '):]) for line in probe_run.stdout.splitlines() if line.startswith('VERIFIED_PROBE ')]
 report['acoustic_probe']=probe_rows[-1] if probe_rows else {'passed':False,'error':probe_run.stderr[-1500:]}
 assert probe_run.returncode==0 and report['acoustic_probe']['passed'],'Self-playback gate failed; restore previous UI'
"""
source = source.replace(needle, needle+insert, 1)
source = source.replace('UI_TIMING_DEPLOYED','UI_ECHO_VERIFY_DEPLOYED').replace('human_timing_verified','human_echo_verified').replace('wait_ready(False)','wait_ready(True)')
(HERE/'activate.py').write_text(source, encoding='utf-8')
print(json.dumps(result), flush=True)
