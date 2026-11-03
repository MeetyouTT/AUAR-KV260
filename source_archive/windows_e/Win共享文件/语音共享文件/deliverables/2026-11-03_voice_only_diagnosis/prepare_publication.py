"""Bind previously reviewed guarded lifecycle templates to fresh one-file evidence."""
from datetime import datetime, timezone
import base64
import copy
import hashlib
import json
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET

TASK = Path(__file__).resolve().parent
OLD = TASK.parent / '2026-11-02_identity_named_reply'
VOICE = TASK.parent / '2026-11-02_voice_speaker_recognition'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def save(name, value):
    data = value if isinstance(value, bytes) else value.encode('utf-8')
    with (TASK / name).open('xb') as stream:
        stream.write(data)


def bind_line(source, prefix, value):
    lines = source.splitlines(keepends=True)
    assert sum(line.startswith(prefix) for line in lines) == 1, prefix
    return ''.join(prefix + repr(value) + '\n' if line.startswith(prefix) else line for line in lines)


for name, count in (('SHORT_VOICE_TEST_RESULT_FIXED.xml', 17), ('VOICE_REGRESSION_RESULT.xml', 21),
                    ('NAMED_REPLY_WITH_SHORT_INTEGRATION_RESULT.xml', 21)):
    cases = list(ET.parse(TASK / name).getroot().iter('testcase'))
    assert len(cases) == count
    assert not any(case.find('failure') is not None or case.find('error') is not None for case in cases)
fresh = json.loads((TASK / 'fresh_read_1_RESULT.json').read_bytes())['board_result']
assert fresh['status'] == 'READONLY_RECONCILED' and not fresh['errors'] and fresh['all380_actual_bytes_match']
state = fresh['current_state']
assert not any(state[key] for key in ('listening_enabled', 'microphone_open', 'playing', 'pending_job', 'speaker_busy', 'follow'))
assert state['runtime_fault_count'] == 0 and state['axis_readback']['flags'] == 0
relative = 'board/runtime/board_speaker_business.py'
assert not any(path.endswith('/' + relative) for path in fresh['selected_face_binding']['source_pin_names'])
before = (TASK / 'baseline/board_speaker_business.py').read_bytes()
after = (TASK / 'candidate_runtime' / relative).read_bytes()
assert digest(before) == fresh['component_sha256'][relative]
compile(after, relative, 'exec')
startup_before = base64.b64decode(fresh['startup_content_base64'], validate=True)
assert digest(startup_before) == fresh['startup_sha256']
updated = json.loads(startup_before)
updated['component_sha256'][relative] = digest(after)
startup_after = (json.dumps(updated, sort_keys=True, indent=2) + '\n').encode()
save('startup.before.json', startup_before)
save('startup.after.json', startup_after)
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
prefix = '/home/root/aura-5090-recovery-20261102-a6d4a069/voice-short-ordinary-' + stamp
transactions = dict(stop=prefix + '-stop', start=prefix + '-start',
    startup_before=digest(startup_before), startup_after=digest(startup_after))
save('TRANSACTIONS.json', json.dumps(transactions, indent=2) + '\n')
phase_sha = digest((TASK / 'DEVICE_MAINTENANCE.json').read_bytes())
expected = json.loads((TASK / 'EXPECTED_BEFORE.json').read_bytes())
for key in ('gui_owner', 'gtk_owner', 'camera_owner'):
    expected[key] = fresh[key]
expected.update(startup_sha256=digest(startup_after), component_sha256=updated['component_sha256'],
    stop_transaction=transactions['stop'], transaction_path=transactions['start'], phase_sha256=phase_sha)
expected['identity_four_core'] = {path: updated['component_sha256'][path] for path in expected['identity_four_core']}
save('EXPECTED_AFTER.json', json.dumps(expected, ensure_ascii=False, indent=2) + '\n')
grant = {key: fresh[key] for key in ('startup_sha256', 'gui_owner', 'gtk_owner', 'camera_owner')}
stop = (OLD / 'stop_gui_1.py').read_text(encoding='utf-8')
stop = bind_line(stop, 'GRANT=', grant)
stop = bind_line(stop, 'SESSION=', transactions['stop'])
stop = bind_line(stop, 'BOOT = ', expected['boot_id'])
stop = bind_line(stop, 'OVERRIDE = Path(', '/run/systemd/system/aura-avatar-ui.service.d/zzzzzz-root-voice-short-' + stamp + '.conf').replace(
    '.conf\'\n', '.conf\')\n')
# bind_line above needs the closing constructor parenthesis, checked by compile.
compile(stop, 'stop_gui_1.py', 'exec')
save('stop_gui_1.py', stop)
apply_expected = dict(boot_id=expected['boot_id'], startup_path=expected['startup_path'],
    startup_before_sha256=digest(startup_before), startup_after_sha256=digest(startup_after),
    component_sha256=fresh['component_sha256'],
    payload=[dict(path=relative, before_sha256=digest(before), after_sha256=digest(after),
                  content_base64=base64.b64encode(after).decode())],
    stop_transaction=transactions['stop'], camera_owner=expected['camera_owner'],
    camera_config=expected['camera_config'], original_GUI_properties=expected['original_GUI_properties'])
apply = bind_line((OLD / 'apply_context_1.py').read_text(encoding='utf-8'), 'E=', apply_expected)
apply = apply.replace("=={'board/runtime/board_dialogue.py'}", "=={'board/runtime/board_speaker_business.py'}")
assert "=={'board/runtime/board_speaker_business.py'}" in apply
apply = apply.replace('NAMED_REPLY_SOURCE_AND_STARTUP_PIN_APPLIED', 'SHORT_ORDINARY_VOICE_SOURCE_AND_STARTUP_PIN_APPLIED')
apply = apply.replace('aura-either-identity-name-CAS-result-1', 'aura-short-ordinary-voice-CAS-result-1')
compile(apply, 'apply_voice_1.py', 'exec')
save('apply_voice_1.py', apply)
start = bind_line((OLD / 'start_gui_1.py').read_text(encoding='utf-8'), 'EXPECTED = ', expected)
compile(start, 'start_gui_1.py', 'exec')
save('start_gui_1.py', start)
ready = (VOICE / 'release/wait_ready_template.py').read_text(encoding='utf-8')
assert ready.count('E=None  # VOICE_READY_EXPECTED') == 1
ready = ready.replace('E=None  # VOICE_READY_EXPECTED', 'E=' + repr(expected))
ready = ready.replace("out['board_mono_ms']=int(time.monotonic()*1000);print(json.dumps(out))", """cfg=json.loads(Path(E['startup_path']).read_bytes());aura=Path(cfg['runtime'])/'aura'
assert cfg['component_sha256']==E['component_sha256'] and all(sha(aura/k)==v for k,v in E['component_sha256'].items())
saved=json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes())
assert saved=={'version':1,'enabled':False}
if out['ready']:
    assert not out['state']['listening_enabled'] and not out['state']['microphone_open']
out['all380_actual_bytes_match']=True;out['saved_listening_preference']=saved
out['board_mono_ms']=int(time.monotonic()*1000);print(json.dumps(out))""")
compile(ready, 'ready_read_1.py', 'exec')
save('ready_read_1.py', ready)
manifest = dict(schema='aura-short-ordinary-voice-source-manifest-1',
    created_utc=datetime.now(timezone.utc).isoformat(), changed_files=apply_expected['payload'],
    startup_before_sha256=digest(startup_before), startup_after_sha256=digest(startup_after),
    other_components_preserved=379, ordinary_voiced_minimum_ms=1500,
    original_enrollment_gate_preserved=True, match_threshold_preserved=True, cross_turn_audio_combining=False,
    encoders_per_accepted_capture=1, new_profile_authority=False)
for row in manifest['changed_files']:
    row.pop('content_base64')
save('SOURCE_MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({key: manifest[key] for key in ('startup_before_sha256', 'startup_after_sha256', 'changed_files')}, ensure_ascii=False))
