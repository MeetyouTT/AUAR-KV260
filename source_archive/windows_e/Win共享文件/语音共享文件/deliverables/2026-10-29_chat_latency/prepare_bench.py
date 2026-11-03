"""Freeze a read-only r6 baseline and pause idle listening before controlled public tests."""
import ast,datetime,hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path.insert(0,str(A));sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from common.voice_service_capabilities import SOURCE_FILES,source_fingerprint
from board_ssh import ssh
assert not (H/'baseline.json').exists()
assert source_fingerprint(A)=='b991e72050af52d86e947594303fc30e5a5675aa2a95140ff7910ba8a0d582a8'
remote=r'''
import json,time,urllib.request
def state():
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as r:return json.load(r)
s=state();h=s['handsfree_dialogue'];p=s['manual_pan']
assert s['phase']=='IDLE' and not s['playing'] and s['audio_output_state']=='IDLE_READY'
assert not s.get('pending_job') and not s['automatic_conversation'].get('speech_active')
assert s['local_transcription']['state'] in ('IDLE','EMPTY','ERROR','DISABLED')
assert p['automatic_following'] is False and not p.get('readback',{}).get('active')
changed=False
if h['enabled']:
 request=urllib.request.Request('http://127.0.0.1:8783/api/command',data=b'{"type":"conversation_toggle"}',
  headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 with urllib.request.urlopen(request,timeout=6) as r:answer=json.load(r)
 assert answer.get('ok') is True;changed=True
for _ in range(60):
 after=state();h=after['handsfree_dialogue']
 if not h['enabled'] and not h['microphone_open'] and not after['automatic_conversation']['enabled']:break
 time.sleep(.1)
assert not h['enabled'] and not h['microphone_open'] and after['phase']=='IDLE' and not after['playing']
assert after['manual_pan']['pulse_us']==p['pulse_us'] and after['manual_pan']['automatic_following'] is False
print(json.dumps({'paused_via_existing_ui':changed,'before_listening':s['handsfree_dialogue']['enabled'],
 'listening':h['enabled'],'microphone_open':h['microphone_open'],'motion_changed':False}))
'''
pause=json.loads(ssh('python3 -B -',remote,timeout=18))
tree=ast.parse((H.parent/'2026-10-28_timeline_summaries/capture_board.py').read_text(encoding='utf-8'))
script=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
board=json.loads(ssh('python3 -B -',script,timeout=20));assert board['preflight_ready']
(H/'board_baseline.json').write_text(json.dumps(board,ensure_ascii=False,indent=2),encoding='utf-8')
value={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'production_revision':'voice-turn-handoff-20261029-r6',
 'production_fingerprint':source_fingerprint(A),'source_before':{n:hashlib.sha256((A/n).read_bytes()).hexdigest() for n in SOURCE_FILES},
 'pause':pause,'migration_deferred':True,'board_code_changed':False,'other_models_must_remain_running':True}
(H/'baseline.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
(H/'PROGRESS.json').write_text(json.dumps({'status':'PROFILING','complete':False,'board_migration':False,
 'listening_paused_via_existing_ui':pause['paused_via_existing_ui'],'production_revision':value['production_revision']},indent=2),encoding='utf-8')
print(json.dumps({'status':'BASELINE_FROZEN','paused':pause,'board_pins':len(board['pins'])}))
