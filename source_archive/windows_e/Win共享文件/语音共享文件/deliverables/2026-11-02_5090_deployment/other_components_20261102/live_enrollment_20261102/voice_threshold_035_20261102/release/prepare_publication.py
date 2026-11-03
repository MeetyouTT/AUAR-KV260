"""Prepare source-CAS publication from the freshly observed current startup."""
import ast
import base64
import hashlib
import json
from pathlib import Path

RELEASE = Path(__file__).resolve().parent
TASK = RELEASE.parent
ENROLL = TASK.parent
OLD = ENROLL / 'voice_self_match_query_alias_20261102/release'
BASE = '44e8f154c9dd72d3b7619160f7a2dac64fda529daba91a96a196c12f68c8a295'
OLD_BASE = '4b4d98494d43bd44aa21b28c960fd8480f0f61f4a5741f212fb541abdf4c147b'
manifest = json.loads((TASK / 'SOURCE_MANIFEST.json').read_bytes())
keys = set(manifest['files'])
assert keys == {'board/runtime/board_speaker_business.py', 'tools/provisional_voice.py', 'tools/yuki_business_gui.py'}
payload = {'base_startup_sha256': BASE, 'files': {}}
after = {}
for key, spec in manifest['files'].items():
    data = (TASK / 'candidate_runtime' / key).read_bytes()
    before = (TASK / 'baseline_runtime' / key).read_bytes()
    assert hashlib.sha256(data).hexdigest() == spec['after_sha256']
    assert hashlib.sha256(before).hexdigest() == spec['before_sha256']
    compile(data, key, 'exec')
    after[key] = spec['after_sha256']
    payload['files'][key] = dict(before_sha256=spec['before_sha256'],
        candidate_sha256=spec['after_sha256'], payload_base64=base64.b64encode(data).decode())

def change(text, old, new):
    assert old in text, old
    return text.replace(old, new)

def assignment(text, name, value):
    tree = ast.parse(text)
    node = next(n for n in tree.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
    lines = text.splitlines(keepends=True)
    lines[node.lineno-1:node.end_lineno] = [name + ' = ' + repr(value) + '\n']
    return ''.join(lines)

def common(text):
    return text.replace(OLD_BASE, BASE).replace('voice-self-match-alias', 'voice-threshold-035')

stop = common((OLD / 'stop_gui_once.py').read_text(encoding='utf-8'))
for before, new in [('196138', '209823'), ('196171', '209835'), ('1530509', '1626221'),
    ('1534107', '1627082'), ('06e4fa8f8dba520e72b9736d522949eb26cc64d98a7c08401928eb6152232c85',
     'c4999fc4bf50c9f4cf289bb1a02c83c90206794051e9f31791668e0cfffc52bc')]:
    stop = change(stop, before, new)

# The old embedded payload is deliberately discarded before adapting the guarded transaction.
apply = (OLD / 'apply_fix_once.py').read_text(encoding='utf-8').split('\n', 1)[1]
apply = common(apply)
apply = assignment(apply, 'KEYS', keys)
apply = change(apply, 'two-file candidate', 'three-file candidate')
apply = change(apply, '/proc/196138', '/proc/209823')
apply = change(apply, '/proc/196171', '/proc/209835')
apply = change(apply, 'voice-entry-name-fix', 'voice-threshold-035')
apply = change(apply, 'VOICE_SELF_MATCH_ALIAS_APPLIED_GUI_STOPPED', 'VOICE_THRESHOLD_035_APPLIED_GUI_STOPPED')
apply = change(apply, '2ad13c7a5a175a85dfb412182fca44a79229962ff742b18691a7b72ea75f15f2',
    '901c74d8de825bf6f22ac7cca608db3840ea7d39cc104ac4b5392dca3f7d8f6c')
apply = change(apply, "'other_component_pins_preserved': 378", "'other_component_pins_preserved': 377")
apply = change(apply, "'identity_thresholds_or_time_policy_or_private_store_changed': False,",
    "'identity_match_threshold_changed_to': .35, 'time_policy_or_private_store_changed': False,")
apply = 'PAYLOAD = ' + repr(payload) + '\n' + apply

start = common((OLD / 'start_gui_once.py').read_text(encoding='utf-8'))
start = change(start, 'VOICE_SELF_MATCH_ALIAS_APPLIED_GUI_STOPPED', 'VOICE_THRESHOLD_035_APPLIED_GUI_STOPPED')
start = assignment(start, 'TARGETS', after)

startup_raw = (RELEASE / 'startup.before.read.json').read_bytes()
assert hashlib.sha256(startup_raw).hexdigest() == BASE
startup = json.loads(startup_raw)
for key, digest in after.items():
    assert startup['component_sha256'][key] == manifest['files'][key]['before_sha256']
    startup['component_sha256'][key] = digest
predicted = (json.dumps(startup, sort_keys=True, indent=2) + '\n').encode()
records = {}
for filename, data in [('stop_gui_once.py', stop.encode()), ('apply_fix_once.py', apply.encode()),
    ('start_gui_once.py', start.encode()), ('startup.after.predicted.json', predicted)]:
    target = RELEASE / filename
    assert not target.exists()
    if filename.endswith('.py'):
        compile(data, str(target), 'exec')
    target.write_bytes(data)
    records[filename] = hashlib.sha256(data).hexdigest()
result = dict(base_startup_sha256=BASE,
    predicted_startup_after_sha256=hashlib.sha256(predicted).hexdigest(),
    source_before={k:v['before_sha256'] for k,v in manifest['files'].items()},
    source_after=after, generated_files=records, device_actions=False)
(RELEASE / 'RELEASE_MANIFEST.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result))
