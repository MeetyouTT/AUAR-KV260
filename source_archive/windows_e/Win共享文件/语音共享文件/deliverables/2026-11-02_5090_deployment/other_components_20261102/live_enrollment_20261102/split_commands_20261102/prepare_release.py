"""Compose the two independently reviewed method regions; prepare a failed-GUI CAS transaction."""
import ast
import base64
import copy
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent
REL = HERE / 'actual_release'
REL.mkdir(exist_ok=True)
EXPECTED_BASE = 'e49436a8ada938c071b484ac04302134ac29420172457da6a2c544c841d77217'
SPLIT = {
    'common/binding_intent.py': ('8cfe3c841248b7ca56553255dcb14e400c5b52ea011e68ecd89a16862a7eb796', '8048cd5bd4f3f80cd872f373e1eed149820f37d2ec40042390c17cfb4cd94df1'),
    'board/runtime/board_business.py': ('b08209eca7979825e26845080bca5e1d64e065d3cabd1178df763a93540573f2', 'c01bb04c7bfbce8d78b51aefa5faf0426527be13edf6e26d8d28828c488222b3'),
    'board/runtime/audio/board_dialogue_jobs.py': ('01b27ede0d8889c35fc9ac990e03538a55fecc7c6a604fb6f781bc5d54c09087', '43708b7fcbf72b11d7a37b01ae090c2cdb3e621b5f334151601206735a34a1fc'),
}

def sha(raw): return hashlib.sha256(raw).hexdigest()

def method(source):
    tree = ast.parse(source)
    nodes = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'initialize_clock']
    assert len(nodes) == 1
    return nodes[0]

def replacement(source, node, text):
    lines = source.splitlines(keepends=True)
    return ''.join(lines[:node.lineno - 1]) + text + ''.join(lines[node.end_lineno:])

manifest = json.loads((HERE / 'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
assert manifest['status'] == 'FINAL_LOCAL_CANDIDATE_NOT_DEPLOYED'
files = {}
for key, (before, after) in SPLIT.items():
    raw = (HERE / 'candidate_runtime' / key).read_bytes()
    assert sha(raw) == after
    entry = next(v for v in manifest['changed_files'] if v['file'] == key)
    assert (entry['before_sha256'], entry['after_sha256']) == (before, after)
    files[key] = raw

overlay = LIVE / 'gui_clock_readonly_review/retry_safety_assessment/business_overlay'
clock_raw = (overlay / 'candidate/board/runtime/board_business.py').read_bytes()
assert sha(clock_raw) == 'aac26f39b8cbec1496df93a3de24b0bc2a14289552d2728c585f3625ef779eae'
base_raw = (LIVE / 'start_sync_fix/candidate_runtime/board/runtime/board_business.py').read_bytes()
assert sha(base_raw) == SPLIT['board/runtime/board_business.py'][0]
clock_source = clock_raw.decode('utf-8'); split_source = files['board/runtime/board_business.py'].decode('utf-8')
original_method = method(base_raw); split_method = method(split_source); clock_method = method(clock_source)
assert ast.dump(original_method, include_attributes=False) == ast.dump(split_method, include_attributes=False)
clock_text = ''.join(clock_source.splitlines(keepends=True)[clock_method.lineno-1:clock_method.end_lineno])
combined = replacement(split_source, split_method, clock_text)
back = replacement(combined, method(combined), ''.join(split_source.splitlines(keepends=True)[split_method.lineno-1:split_method.end_lineno]))
assert back == split_source
assert ast.dump(method(combined), include_attributes=False) == ast.dump(clock_method, include_attributes=False)
files['board/runtime/board_business.py'] = combined.encode('utf-8')
for key, raw in files.items():
    compile(raw, key, 'exec')
    destination = REL / 'candidate' / key
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream: stream.write(raw)

base = (HERE / 'startup.e494.before.json').read_bytes(); assert sha(base) == EXPECTED_BASE
startup = json.loads(base); after = copy.deepcopy(startup)
payload = {'base_startup_sha256': EXPECTED_BASE, 'files': {}}
for key, raw in files.items():
    assert startup['component_sha256'][key] == SPLIT[key][0]
    after['component_sha256'][key] = sha(raw)
    payload['files'][key] = {'before_sha256': SPLIT[key][0], 'candidate_sha256': sha(raw), 'payload_base64': base64.b64encode(raw).decode()}
after_raw = (json.dumps(after, sort_keys=True, indent=2) + '\n').encode()
assert len(after['component_sha256']) == 380
assert {k for k in after['component_sha256'] if after['component_sha256'][k] != startup['component_sha256'][k]} == set(SPLIT)
with (REL / 'startup.after.predicted.json').open('xb') as stream: stream.write(after_raw)

template = (LIVE / 'lifecycle_review/no_speech_fix/apply_no_speech_fix.template.py').read_text(encoding='utf-8')
template = template.replace('import base64\n', 'import base64\nimport http.client\n')
template = template.replace('/no-speech-enrollment-v1', '/split-enrollment-entry-v1')
template = template.replace("KEYS = {'board/runtime/audio/board_asr.py', 'board/runtime/audio/board_dialogue_jobs.py'}", "KEYS = {'common/binding_intent.py', 'board/runtime/board_business.py', 'board/runtime/audio/board_dialogue_jobs.py'}")
tree = ast.parse(template)
node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'owners')
owners = '''def owners():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == 'a6d4a069-e9b0-4065-8df7-dc23556b168e'
    gui = unit('aura-avatar-ui.service')
    assert gui['MainPID'] == '0' and gui['ActiveState'] in {'failed','inactive'} and not gui['Job']
    assert gui['SubState'] in {'failed','dead'}
    launch = json.loads(raw(ROOT / 'runtime/launch.json'))
    assert launch['boot_id'] == 'a6d4a069-e9b0-4065-8df7-dc23556b168e'
    assert not Path('/proc/' + str(launch['supervisor_pid'])).exists() and not Path('/proc/' + str(launch['pid'])).exists()
    for base in ('/sys/fs/cgroup','/sys/fs/cgroup/systemd','/sys/fs/cgroup/unified'):
        group = Path(base) / 'system.slice/aura-avatar-ui.service/cgroup.procs'
        if group.is_file(): assert not group.read_text().strip()
    assert unit('aura-camera-ui.service') == {'MainPID':'1332','ActiveState':'active','SubState':'running','Job':''}
    assert Path('/proc/1332/stat').read_text().rsplit(')',1)[1].split()[19] == '2236'
    assert sha('/proc/1332/cmdline') == 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
'''
template = replacement(template, node, owners)
old = "assert json.loads(raw(TX / 'stop-result.json'))['status'] == 'GUI_NORMAL_STOPPED'\nassert TX.resolve(strict=True) == TX and TX.stat().st_uid == 0\nassert not (TX / 'apply-intent.json').exists() and not (TX / 'applied.json').exists()"
assert old in template
template = template.replace(old, "assert not TX.exists() and not TX.is_symlink()\nassert TX.parent.resolve(strict=True) == TX.parent and TX.parent.stat().st_uid == 0")
template = template.replace('9a9a709a7b2e898879bac595758f9b7ece6f2ff2e75a4c9f42ed9c38e043072a', EXPECTED_BASE)
point = "create(TX / 'apply-intent.json',"
assert point in template
template = template.replace(point, "c = http.client.HTTPConnection('127.0.0.1',8790,timeout=3)\ntry:\n    c.request('GET','/v1/ui/status'); response=c.getresponse(); data=response.read(2097153)\n    assert response.status==200 and len(data)<=2097152\n    identity=(json.loads(data).get('modules') or {}).get('identity') or {}\n    assert (identity.get('enrollment_sampling') or {}).get('stage') in ('idle','failed','cancelled','done')\n    assert (identity.get('last_operation') or {}).get('state') != 'PENDING'\n    assert len(identity.get('people') or []) >= 1\nfinally: c.close()\nTX.mkdir(mode=0o700); sync_dir(TX.parent)\n" + point)
template = template.replace('aura-no-speech-enrollment-fix-applied-1', 'aura-separated-entry-clock-recovery-applied-1')
template = template.replace('NO_SPEECH_FIX_APPLIED_GUI_STOPPED', 'SPLIT_ENTRY_CLOCK_FIX_APPLIED_GUI_FAILED_NO_OWNER')
template = template.replace("'other_component_pins_preserved': 378", "'other_component_pins_preserved': 377")
template = template.replace("'voice_a911_and_router85_preserved': True", "'voice_a911_and_router85_preserved': True, 'asr_c514_preserved': True, 'clock_retake_keeps_original_one_second_policy_and_shared_three_second_default': True")
source = 'PAYLOAD = ' + repr(payload) + '\n' + template
compile(source, 'apply_split_entry.py', 'exec')
with (REL / 'apply_split_entry.py').open('x', encoding='utf-8', newline='\n') as stream: stream.write(source)
seal = {'schema':'aura-composed-split-entry-clock-release-1','production_changed':False,
        'base_startup_sha256':EXPECTED_BASE,'predicted_startup_sha256':sha(after_raw),
        'method_overlay_is_byte_exact_and_all_other_split_code_unchanged':True,
        'files':{k:{'before_sha256':SPLIT[k][0],'after_sha256':sha(v)} for k,v in files.items()},
        'apply_script_sha256':sha(source.encode()),'component_count':380,'other_component_pins_preserved':377,
        'gtk_two_component_pins_preserved':{k:after['component_sha256'][k] for k in ['board/interaction/ui_services.py','tools/board_camera_preview.py']}}
with (REL / 'RELEASE_MANIFEST.json').open('x',encoding='utf-8') as stream: json.dump(seal,stream,indent=2);stream.write('\n')
print(json.dumps(seal))
