"""Freeze passed candidate; stop only currently enabled idle listening through existing UI."""
import ast,hashlib,json,shutil,sys,xml.etree.ElementTree as ET
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
sys.path.insert(0,str(A));sys.path.insert(0,str(H.parent/'2026-10-18_board_dialogue'))
from common.voice_service_capabilities import source_fingerprint
from board_ssh import ssh
plan=json.loads((H/'source_plan.json').read_text(encoding='utf-8'))
assert plan['status']=='CANDIDATE' and source_fingerprint(A)==plan['production_fingerprint']
assert not (H/'board_baseline.json').exists()
assert all(hashlib.sha256((A/n).read_bytes()).hexdigest()==v for n,v in plan['source_before'].items())
suites=list(ET.parse(H/'tests.xml').getroot().iter('testsuite'))
assert sum(int(s.get('tests',0)) for s in suites)==284
assert not sum(int(s.get('errors',0))+int(s.get('failures',0))+int(s.get('skipped',0)) for s in suites)
assert json.loads((H/'baseline_reproduction.json').read_text())['http_status']==503
for name,row in plan['files'].items():
 assert hashlib.sha256((H/'candidate_source'/name).read_bytes()).hexdigest()==row['candidate']
 ast.parse((H/'candidate_source'/name).read_text(encoding='utf-8'))
remote=r'''
import json,time,urllib.request
from pathlib import Path
root=Path('/home/root/aura-boundary-nav-20261029/gui-page-sync-v2/runtime/aura')
source=(root/'tools/board_avatar_gtk.py').read_text()
assert "intent=self.controller.handsfree_toggle()" in source
assert "kind == 'conversation_toggle'" in source
def state():
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as r:return json.load(r)
before=state();h=before['handsfree_dialogue'];pan=before['manual_pan']
assert before['phase']=='IDLE' and not before['playing'] and before['audio_output_state']=='IDLE_READY'
assert not before.get('pending_job') and not before.get('automatic_conversation',{}).get('speech_active')
assert before['local_transcription']['state'] in ('IDLE','EMPTY','ERROR','DISABLED')
assert pan['automatic_following'] is False and not pan.get('readback',{}).get('active')
action=False
if h['enabled']:
 # The state was just read ON; this existing UI action only pauses listening.
 request=urllib.request.Request('http://127.0.0.1:8783/api/command',
  data=b'{"type":"conversation_toggle"}',headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 with urllib.request.urlopen(request,timeout=6) as r:answer=json.load(r)
 assert answer.get('ok') is True,answer
 action=True
for _ in range(60):
 after=state();h=after['handsfree_dialogue']
 if not h['enabled'] and not h['microphone_open'] and not after['automatic_conversation']['enabled']:break
 time.sleep(.1)
assert not h['enabled'] and not h['microphone_open'] and not after['automatic_conversation']['enabled']
assert after['phase']=='IDLE' and not after['playing'] and after['audio_output_state']=='IDLE_READY'
assert after['manual_pan']['pulse_us']==pan['pulse_us'] and after['manual_pan']['automatic_following'] is False
print(json.dumps({'paused_via_existing_ui':action,'before_enabled':before['handsfree_dialogue']['enabled'],
 'after_enabled':h['enabled'],'microphone_open':h['microphone_open'],'pan_pulse_preserved':True,
 'ui_restarted':False,'listening_will_remain_off':True},ensure_ascii=True))
'''
pause=json.loads(ssh('python3 -B -',remote,timeout=18))
(H/'listening_pause.json').write_text(json.dumps(pause,indent=2),encoding='utf-8')
tree=ast.parse((H.parent/'2026-10-28_timeline_summaries/capture_board.py').read_text(encoding='utf-8'))
script=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='script' for t in n.targets))
current=json.loads(ssh('python3 -B -',script,timeout=20))
original=json.loads((H/'board_snapshot.json').read_text(encoding='utf-8'))['board']
assert current['preflight_ready']
for key in ('boot','actual_runtime','actual_config','config_sha256','pins','pan'):assert current[key]==original[key],key
for key in ('camera_service','ui_service'):
 for name in ('MainPID','NRestarts','ExecStart','ActiveState'):assert current[key][name]==original[key][name]
(H/'board_baseline.json').write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ('manage_owned.ps1','db_checkpoint.py','start_checkpoint.ps1','deploy_windows.py','verify_private.py','live_voice_acceptance.py'):
 shutil.copy2(H.parent/'2026-10-29_dialogue_memory_polish'/name,H/name)
p=H/'db_checkpoint.py';s=p.read_text(encoding='utf-8').replace('polish-20261029-','handoff-20261029-');p.write_text(s,encoding='utf-8')
p=H/'deploy_windows.py';s=p.read_text(encoding='utf-8').replace("plan['tests_passed']==267","plan['tests_passed']==284")
s=s.replace("    assert voice['capabilities']['natural_fact_answers']==1 and voice['capabilities']['memory_source_coverage']==1",
"    assert voice['capabilities']['natural_fact_answers']==1 and voice['capabilities']['memory_source_coverage']==1\n    assert voice['capabilities']['queued_voice_admission']==1 and voice['capabilities']['bounded_voice_request_diagnostics']==1")
p.write_text(s,encoding='utf-8')
plan.update(status='READY_WINDOWS_ONLY',tests_passed=284,preserved_latency_sha256=plan['source_before']['config/voice_latency.json'])
(H/'source_plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
print(json.dumps({'status':plan['status'],'tests':284,'paused':pause,'board_pins':len(current['pins'])}))
