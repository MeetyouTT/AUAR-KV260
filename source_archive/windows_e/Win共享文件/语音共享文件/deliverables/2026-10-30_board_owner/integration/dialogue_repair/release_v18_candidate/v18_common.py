"""Local pinned source preparation. Import never opens SSH or a database."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
INTEGRATION = HERE.parents[1]
PROJECT = HERE.parents[4]
APPLY_SHA = '74bd266353d58f7edd8728ef0dd1ae1ab613eb8386884bba32940018b510bfe2'
PUBLISH_SHA = 'fa6be3387961d32c40051fd3fd495ee1db62ef8888d23c6dcdafbab2dcc4085a'
V17_STARTUP = '0cbc191b4bf9029b15a65ef15797e43e15459e06b88381025d28a2c9b573dd2a'
V17_MANIFEST = '38a267a4f8d504803587c8be353452b146f1e232e926ac4e061a5e2832b33620'
CONFIG_SHA = 'd2511ee2b95f0ae9b2cbb18f16cde90719420d887e858926e8fd07a5c5b60013'
MAPPING_SHA = '348c435302e4e855d9bf4ef354f0b26d56ef9dfac64438a4fb11f70b5f6e63af'
NATIVE_SHA = 'b2432e75a75e4dbdebee8e89a141a68ba00671c33b2b258b81ce16794b2c73d2'
PAIR_SHA = '998710fc12bf442d6baea501bab0234665b666caa29f4be8f685741d50d82099'
V17_STAGE = 'response-latency-v17-thinking-and-feature-queries'
STAGE = 'response-latency-v18-memory-recall'
BOOT = '8100a7fd-0c6a-46c4-82b8-f874988a1521'
TARGET = '/home/root/aura-board-business-20261030/production-5259eab11e42af13'
CORE = {
    'board/runtime/board_memory_policy.py': (
        'memory_observation_candidate_r2/after/board/runtime/board_memory_policy.py',
        '6050ed5e4dcfeb456c5d0969e257f624552f80ff722b3c3999a573f86cd933c2',
        '410e5b3eaf7986be6baa68d148469eb33443654ed0db597004518877732533c5'),
    'common/board_memory.py': (
        'feature_trigger_collaboration/candidate_h01/after/common/board_memory.py',
        'fe50db190aaafcb8841eaa132ed9ea218a80bc582efacb3c3c83e952bf985e9f',
        'c27d4d3c39e5de293cbc7fed8899de8b0d39ea6ccc99c0e7f64f22c8a90a2c0b'),
    'board/runtime/board_dialogue.py': (
        'feature_trigger_collaboration/candidate_h01/after/board/runtime/board_dialogue.py',
        'bce1f21962d083275d9e8a966f244d8c227d0d62e9a30314767453d04c05b475',
        'c877cdee602ff0bda669cc2b2fefa77e9328ce205a744e317df82ffb17146de6'),
    'board/runtime/board_speaker_business.py': (
        'feature_trigger_collaboration/candidate_speaker_close/after/board/runtime/board_speaker_business.py',
        'f299273d903d3bed4f24576f12dd41e327f5a0f0b490f8f122904291a769b067',
        '56a01bee6cb93d808506564e71e56b35f3a51fa6d3432e82762e7b853e63870b'),
    'tools/board_avatar_gtk.py': (
        'animation_thinking_collaboration/frame_rate_24_candidate/ui_timing_probe/candidate/aura/tools/board_avatar_gtk.py',
        '7d95b5f682f7abf4a69509d5843c3345dcc31f8dbefeb0e9f3af27b19aa3542d',
        'c62dc730404e0de549eca2aaa886997824d4e4b381cd6b31ffb21bae509dc011'),
}

def sha(raw): return hashlib.sha256(raw).hexdigest()
def encoded(value): return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
def create_json(path, value):
    with Path(path).open('xb') as f: f.write(encoded(value))
def pinned(path, expected):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.resolve(strict=True) != path:
        raise ValueError('Canonical source required')
    raw = path.read_bytes()
    if sha(raw) != expected: raise ValueError('Source SHA mismatch')
    return raw
def remote_from(relative, expected):
    tree = ast.parse(pinned(INTEGRATION / relative, expected))
    values = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'REMOTE' for t in n.targets)]
    if len(values) != 1 or not isinstance(values[0], str): raise ValueError('One literal REMOTE required')
    return values[0]
def replace_once(source, before, after):
    if source.count(before) != 1: raise ValueError('Unique upstream anchor required')
    return source.replace(before, after)
def validate_spec(value, *, allow_v17=False):
    if (value.get('boot_id') != BOOT or value.get('target') != TARGET or value.get('component_pins') != 379
        or value.get('configuration_sha256') != CONFIG_SHA
        or value.get('native_library_sha256') != NATIVE_SHA
        or value.get('character_pair_selection_sha256') != PAIR_SHA
        or value.get('retention_enabled') is not True or value.get('automatic_listening') is not True
        or value.get('wake_word_required') is not False or value.get('conversation_mode') != 'half_duplex'):
        raise ValueError('Exact reviewed board configuration required')
    stage = value.get('release_stage')
    if allow_v17 and stage == V17_STAGE:
        if value.get('startup_sha256') != V17_STARTUP or value.get('source_manifest_sha256') != V17_MANIFEST:
            raise ValueError('Exact v17 source required')
    elif stage == STAGE:
        if (value.get('previous_startup_sha256') != V17_STARTUP
            or value.get('release_sources') != {k: row[2] for k, row in CORE.items()}
            or value.get('expected_final_listening_enabled') is not True
            or any(not isinstance(value.get(k), str) or not re.fullmatch('[a-f0-9]{64}', value[k])
                   for k in ('startup_sha256', 'source_manifest_sha256'))):
            raise ValueError('Explicit completed v18 spec required')
    else:
        raise ValueError('Reviewed v17/v18 spec required')
    return value
def frozen_v17_spec(path):
    value = validate_spec(json.loads(Path(path).read_bytes()), allow_v17=True)
    if value['release_stage'] != V17_STAGE: raise ValueError('v17 baseline required')
    return value
def ssh_json(script, *, timeout):
    # Only root's explicit execution branch may reach this lazy import.
    sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
    from board_ssh import ssh
    return json.loads(ssh('python3 -B -', script, timeout=timeout))
def publisher_script(remote, values):
    env = json.loads(pinned(INTEGRATION / 'formal_character_switch/actual_baseline.json',
        'b251f029c2f49578e99569ba16e8cb4d6fd0321f0d5af31587517e695c22b0fb'))['display_environment']
    return '\n'.join(k + '=' + repr(v) for k, v in values.items()) + '\nimport os\nos.environ.update(' + repr(env) + ')\n' + remote
