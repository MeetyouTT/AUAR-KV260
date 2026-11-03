"""Bind the guarded normal lifecycle to the actual 380 pinned sources."""
import base64, copy, hashlib, json, uuid
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

TASK = Path(__file__).resolve().parent
OLD = TASK.parent/'2026-11-02_identity_named_reply'
VOICE = TASK.parent/'2026-11-02_voice_speaker_recognition'
def sha(raw): return hashlib.sha256(raw).hexdigest()
def save(name, data):
    with (TASK/name).open('xb') as f: f.write(data if isinstance(data, bytes) else data.encode())
def bind(text, prefix, value, suffix=''):
    lines = text.splitlines(keepends=True)
    assert sum(line.startswith(prefix) for line in lines) == 1
    return ''.join(prefix+repr(value)+suffix+'\n' if line.startswith(prefix) else line for line in lines)

cases = list(ET.parse(TASK/'CONTEXT_REGRESSION_RESULT.xml').getroot().iter('testcase'))
assert len(cases) == 80
failures = [c for c in cases if c.find('failure') is not None or c.find('error') is not None]
assert len(failures) == 3 and all('character_address_understanding' in c.get('name') or
    'addressed_explicit_commands' in c.get('name') for c in failures)
baseline = list(ET.parse(TASK/'BASELINE_REGRESSION_RESULT.xml').getroot().iter('testcase'))
assert {c.get('name') for c in baseline if c.find('failure') is not None} == {c.get('name') for c in failures}
fresh = json.loads((TASK/'fresh_read_1_RESULT.json').read_bytes())['board_result']
assert fresh['status'] == 'READONLY_RECONCILED' and not fresh['errors'] and fresh['all380_actual_bytes_match']
state = fresh['current_state']
assert not any(state[k] for k in ('listening_enabled','microphone_open','playing','pending_job','speaker_busy','follow'))
assert state['runtime_fault_count'] == 0 and state['axis_readback']['flags'] == 0
paths = ['board/runtime/board_memory_policy.py','board/runtime/board_business.py','common/board_memory.py']
payload = []
for name in paths:
    assert not any(p.endswith('/'+name) for p in fresh['selected_face_binding']['source_pin_names'])
    before = (TASK/'baseline'/name).read_bytes(); after = (TASK/'candidate_runtime'/name).read_bytes()
    assert sha(before) == fresh['component_sha256'][name]
    compile(after,name,'exec')
    payload.append(dict(path=name,before_sha256=sha(before),after_sha256=sha(after),content_base64=base64.b64encode(after).decode()))
raw = base64.b64decode(fresh['startup_content_base64'],validate=True)
assert sha(raw) == fresh['startup_sha256']
updated = json.loads(raw)
for row in payload: updated['component_sha256'][row['path']] = row['after_sha256']
newraw = (json.dumps(updated,sort_keys=True,indent=2)+'\n').encode()
save('startup.before.json',raw); save('startup.after.json',newraw)
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
prefix='/home/root/aura-5090-recovery-20261102-a6d4a069/five-turn-'+stamp
transactions=dict(stop=prefix+'-stop',start=prefix+'-start',startup_before=sha(raw),startup_after=sha(newraw))
save('TRANSACTIONS.json',json.dumps(transactions,indent=2)+'\n')
expected=json.loads((TASK/'EXPECTED_BEFORE.json').read_bytes())
for key in ('gui_owner','gtk_owner','camera_owner'): expected[key]=fresh[key]
expected.update(startup_sha256=sha(newraw),component_sha256=updated['component_sha256'],
    stop_transaction=transactions['stop'],transaction_path=transactions['start'],phase_sha256=sha((TASK/'DEVICE_MAINTENANCE.json').read_bytes()))
expected['identity_four_core']={p:updated['component_sha256'][p] for p in expected['identity_four_core']}
save('EXPECTED_AFTER.json',json.dumps(expected,ensure_ascii=False,indent=2)+'\n')
grant={k:fresh[k] for k in ('startup_sha256','gui_owner','gtk_owner','camera_owner')}
stop=(OLD/'stop_gui_1.py').read_text(encoding='utf-8')
stop=bind(stop,'GRANT=',grant); stop=bind(stop,'SESSION=',transactions['stop']); stop=bind(stop,'BOOT = ',expected['boot_id'])
stop=bind(stop,'OVERRIDE = Path(','/run/systemd/system/aura-avatar-ui.service.d/zzzzzz-root-five-turn-'+stamp+'.conf',')')
save('stop_gui_1.py',stop)
apply_expected=dict(boot_id=expected['boot_id'],startup_path=expected['startup_path'],startup_before_sha256=sha(raw),startup_after_sha256=sha(newraw),
    component_sha256=fresh['component_sha256'],payload=payload,stop_transaction=transactions['stop'],camera_owner=expected['camera_owner'],
    camera_config=expected['camera_config'],original_GUI_properties=expected['original_GUI_properties'])
apply=bind((OLD/'apply_context_1.py').read_text(encoding='utf-8'),'E=',apply_expected)
apply=apply.replace("=={'board/runtime/board_dialogue.py'}",'=='+repr(set(paths)))
apply=apply.replace('NAMED_REPLY_SOURCE_AND_STARTUP_PIN_APPLIED','FIVE_TURN_SOURCES_AND_STARTUP_PINS_APPLIED').replace('other379_actual_components_preserved','other377_actual_components_preserved')
save('apply_context_1.py',apply)
start=bind((OLD/'start_gui_1.py').read_text(encoding='utf-8'),'EXPECTED = ',expected)
start=start.replace("assert backend['tts_ready'] is True", "assert backend['context_limit'] == 4096\n    assert backend['tts_ready'] is True")
save('start_gui_1.py',start)
ready=(VOICE/'release/wait_ready_template.py').read_text(encoding='utf-8').replace('E=None  # VOICE_READY_EXPECTED','E='+repr(expected))
ready=ready.replace("out['board_mono_ms']=int(time.monotonic()*1000);print(json.dumps(out))", """cfg=json.loads(Path(E['startup_path']).read_bytes());aura=Path(cfg['runtime'])/'aura'
assert cfg['component_sha256']==E['component_sha256'] and all(sha(aura/k)==v for k,v in E['component_sha256'].items())
saved=json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes())
assert saved=={'version':1,'enabled':False}
if out['ready']:
    assert not out['state']['listening_enabled'] and not out['state']['microphone_open']
out['all380_actual_bytes_match']=True;out['saved_listening_preference']=saved
out['board_mono_ms']=int(time.monotonic()*1000);print(json.dumps(out))""")
save('ready_read_1.py',ready)
for name in ('stop_gui_1.py','apply_context_1.py','start_gui_1.py','ready_read_1.py'): compile((TASK/name).read_bytes(),name,'exec')
manifest=dict(schema='aura-five-turn-context-source-manifest-1',created_utc=datetime.now(timezone.utc).isoformat(),
    changed_files=[{k:v for k,v in row.items() if k!='content_base64'} for row in payload],
    startup_before_sha256=sha(raw),startup_after_sha256=sha(newraw),other_components_preserved=377,
    context_limit=4096,prior_user_turns=4,raw_recent_completed_turns_preserved=5,model_weights_changed=False)
save('SOURCE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(manifest,ensure_ascii=False))
