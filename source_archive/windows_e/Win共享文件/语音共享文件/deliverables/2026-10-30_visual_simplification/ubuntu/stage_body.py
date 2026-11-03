"""Isolated one-component candidate, using fresh runtime-owned log pointers."""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types

for name in ('board_state','workflow_common','runtime_clone'):
    module = types.ModuleType(name)
    module.__file__ = name+'.py'
    sys.modules[name] = module
    exec(compile(SOURCES[name+'.py'],module.__file__,'exec'),module.__dict__)

from board_state import capture, digest
from runtime_clone import clone_runtime
from workflow_common import atomic_json, require_idle

lock = Path('/run/aura-visual-simplification.lock').open('a')
fcntl.flock(lock.fileno(),fcntl.LOCK_EX | fcntl.LOCK_NB)
b = capture()
require_idle(b,EXPECTED_SIGNATURE)
time.sleep(.7)
require_idle(capture(),EXPECTED_SIGNATURE)
stage = Path(STAGE)
assert stage.parent.resolve() == Path('/home/root/aura-board-vision-20261030').resolve()
assert not stage.exists() and not stage.is_symlink(), 'Candidate already exists; do not replay'
stage.mkdir()
root = clone_runtime(b['actual_runtime'],stage/'runtime')
startup = stage/'startup'
startup.mkdir()
launcher = Path(b['pending_launcher']).read_bytes()
assert hashlib.sha256(launcher).hexdigest() == b['pending_launcher_sha256']
(startup/'launcher.py').write_bytes(launcher)
target = root/'aura/board/runtime/device_observer.py'
assert not target.is_symlink()
target.resolve().relative_to(root.resolve())
old_sha = digest(target)
target.write_text(SOURCES['device_observer.py'])
pins = dict(b['pins'])
pins['board/runtime/device_observer.py'] = digest(target)
assert old_sha != pins['board/runtime/device_observer.py']
config = dict(b['pending'],runtime=str(root),component_sha256=pins)
atomic_json(startup/'config.json',config)
for name,sha in pins.items():
    assert digest(root/'aura'/name) == sha, name
assert [n for n in pins if pins[n] != b['pins'][n]] == ['board/runtime/device_observer.py']
assert {k:v for k,v in config.items() if k not in ('runtime','component_sha256')} == {
    k:v for k,v in b['pending'].items() if k not in ('runtime','component_sha256')}
ops = stage/'ops'
ops.mkdir()
for name in ('board_state.py','workflow_common.py','runtime_clone.py'):
    (ops/name).write_text(SOURCES[name])
validation = stage/'validation'
(validation/'source_before').mkdir(parents=True)
(validation/'source_before/launcher.py').write_bytes(launcher)
(validation/'runtime_clone.py').write_text(SOURCES['runtime_clone.py'])
(validation/'test_runtime_clone.py').write_text(SOURCES['test_runtime_clone.py'])
(stage/'board').mkdir()
(stage/'board/device_observer.py').write_text(SOURCES['device_observer.py'])
env = dict(os.environ,PATH='/usr/sbin:/usr/bin:/sbin:/bin',PYTHONDONTWRITEBYTECODE='1')
tests = subprocess.run(['/usr/bin/python3','-B','-m','unittest','-v','test_runtime_clone'],
                       cwd=str(validation),env=env,stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT,text=True,timeout=30)
(stage/'arm_tests.log').write_text(tests.stdout)
assert tests.returncode == 0, tests.stdout
preflight = subprocess.run(['/usr/bin/python3','-B',str(startup/'launcher.py'),
                            '--config',str(startup/'config.json'),'--preflight'],
                           env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                           text=True,timeout=45)
(stage/'preflight.log').write_text(preflight.stdout)
assert preflight.returncode == 0, preflight.stdout
require_idle(capture(),EXPECTED_SIGNATURE)
atomic_json(stage/'baseline.json',b)
report = dict(status='STAGED',stage=str(stage),runtime=str(root),startup=str(startup),
              pins=len(pins),changed=['board/runtime/device_observer.py'],
              baseline_signature=EXPECTED_SIGNATURE,config_sha256=digest(startup/'config.json'),
              launcher_sha256=digest(startup/'launcher.py'),
              observer_sha256=digest(target),arm_tests=9,arm_test_log=tests.stdout,
              preflight=preflight.stdout,optimized_launcher_preserved=True,
              mutable_run_artifacts_copied=False,old_failed_candidates_preserved=True,
              microphone_opened=False,physical_playback=False,motion_command_sent=False)
atomic_json(stage/'candidate.json',report)
print(json.dumps(report))
