from pathlib import Path
import json
import os
import subprocess
import shutil
import time

root = Path('/home/root/aura-yuki-validation-20261030').resolve()
assert str(root) == '/home/root/aura-yuki-validation-20261030'
integration = root / 'native_integration'
build = integration / 'build_mesh'
evidence = integration / 'mesh_evidence'
build.mkdir(exist_ok=True)
evidence.mkdir(exist_ok=True)
if (evidence / 'execution.json').exists():
    saved = evidence / ('attempt-' + str(len(list(evidence.glob('attempt-*'))) + 1).zfill(2))
    saved.mkdir()
    for previous in evidence.iterdir():
        if previous.is_file():
            shutil.copy2(previous, saved / previous.name)
lock = build / '.mesh-agent-lock'
descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
os.write(descriptor, str(os.getpid()).encode())
os.close(descriptor)
record = {'start_unix': time.time(), 'jobs': [], 'ok': False, 'scope': 'isolated CPU build/tests'}
try:
    def run(name, command):
        print(name, 'started', flush=True)
        started = time.time()
        with (evidence / (name + '.log')).open('w') as log:
            result = subprocess.run(['nice', '-n', '15'] + command, stdin=subprocess.DEVNULL,
                                    stdout=log, stderr=subprocess.STDOUT, timeout=900)
        record['jobs'].append({'name': name, 'argv': command, 'returncode': result.returncode,
                               'seconds': time.time() - started})
        (evidence / 'execution.json').write_text(json.dumps(record, indent=2))
        print(name, 'exit', result.returncode, flush=True)
        if result.returncode:
            print('\n'.join((evidence / (name + '.log')).read_text(errors='replace').splitlines()[-35:]),
                  flush=True)
            raise RuntimeError(name + ' failed')
    run('configure', ['cmake', '-S', str(integration / 'candidate_core/tools/mesh_combinator_probe/standalone'),
                     '-B', str(build), '-DCMAKE_BUILD_TYPE=Release',
                     '-DCMAKE_CXX_FLAGS_RELEASE=-O2 -DNDEBUG'])
    run('build', ['cmake', '--build', str(build), '--parallel', '1'])
    run('self-tests', [str(build / 'mesh_combinator_probe'), '--self-test',
                      str(build / 'generated-fixtures'), str(evidence / 'self-test.json')])
    run('real-grids', [str(build / 'mesh_combinator_probe'), '--model',
                      str(root / 'inputs/ems/yuk_0.ems.json'),
                      str(root / 'inputs/ems/yuk_0.ems.resx.json'),
                      str(root / 'inputs/ems'), str(evidence / 'real-grids.json')])
    run('runtime-audit', [str(build / 'mesh_runtime_audit'),
                         str(root / 'inputs/ems/yuk_0.ems.json'),
                         str(root / 'inputs/ems/yuk_0.ems.resx.json'),
                         '--resource-root', str(root / 'inputs/ems'), '--steps', '120',
                         '--output', str(evidence / 'runtime-audit.json')])
    record['ok'] = True
except Exception as error:
    record['error'] = str(error)
finally:
    record['end_unix'] = time.time()
    (evidence / 'execution.json').write_text(json.dumps(record, indent=2))
    lock.unlink()
print(json.dumps(record), flush=True)
