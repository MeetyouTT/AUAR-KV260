"""Local source extraction only; importing this module never opens SSH."""
import ast
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
INTEGRATION = HERE.parents[1]
PROJECT = HERE.parents[4]
APPLY_SHA = '74bd266353d58f7edd8728ef0dd1ae1ab613eb8386884bba32940018b510bfe2'
PUBLISH_SHA = 'fa6be3387961d32c40051fd3fd495ee1db62ef8888d23c6dcdafbab2dcc4085a'
V16_STARTUP = 'bf6cdd70768ea5fac4e5be874a387f444c0834d67db5e7a2a744671d9019d63c'
V16_MANIFEST = 'e488f45660e78904d04ba57fe4210e2bcf9eeffa6282219096e9d7b6115df718'
V16_CONFIG = '8c35161e766c53728c75c592a074845e35e01502e8438aaf649b4a8e078a6101'
OLD_NATIVE = '887546c09eb1897845c8d7f55a9e3f9b9c761448c7410f2b599259ae0b51efd2'
NEW_NATIVE = 'b2432e75a75e4dbdebee8e89a141a68ba00671c33b2b258b81ce16794b2c73d2'
OLD_PAIR = '87ad6a1cc520538c7c47b6b52aa5e99c24446efdeb49b69cfe65f8872398f2b0'
NEW_PAIR = '998710fc12bf442d6baea501bab0234665b666caa29f4be8f685741d50d82099'
STAGE = 'response-latency-v17-thinking-and-feature-queries'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned(path, expected):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError('Missing canonical source: ' + str(path))
    raw = path.read_bytes()
    if sha(raw) != expected:
        raise ValueError('Source SHA mismatch: ' + str(path))
    return raw


def remote_from(relative, expected):
    source = pinned(INTEGRATION / relative, expected)
    tree = ast.parse(source)
    values = [ast.literal_eval(n.value) for n in tree.body
              if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'REMOTE' for t in n.targets)]
    if len(values) != 1 or not isinstance(values[0], str):
        raise ValueError('Require one literal REMOTE')
    return values[0]


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError('Upstream edit anchor is not unique')
    return source.replace(before, after)


def frozen_v16_spec(path):
    value = json.loads(Path(path).read_bytes())
    if (value.get('boot_id') != '8100a7fd-0c6a-46c4-82b8-f874988a1521'
            or value.get('target') != '/home/root/aura-board-business-20261030/production-5259eab11e42af13'
            or value.get('startup_sha256') != V16_STARTUP
            or value.get('configuration_sha256') != V16_CONFIG
            or value.get('component_pins') != 378
            or value.get('retention_enabled') is not True
            or value.get('automatic_listening') is not True
            or value.get('wake_word_required') is not False
            or value.get('conversation_mode') != 'half_duplex'):
        raise ValueError('Exact v16 Small/paused-policy baseline required')
    return value


def ssh_json(script, *, timeout):
    # Imported only after the root operator selects execution explicitly.
    sys.path.insert(0, str(PROJECT / 'deliverables/2026-10-18_board_dialogue'))
    from board_ssh import ssh
    return json.loads(ssh('python3 -B -', script, timeout=timeout))


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def create_json(path, value):
    with Path(path).open('xb') as out:
        out.write(encoded(value))


def publisher_script(remote, values):
    env = json.loads((INTEGRATION / 'formal_character_switch/actual_baseline.json').read_bytes())['display_environment']
    return ('\n'.join(k + '=' + repr(v) for k, v in values.items()) + '\n'
            + 'import os\nos.environ.update(' + repr(env) + ')\n' + remote)
