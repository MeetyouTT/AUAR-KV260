#!/usr/bin/env python3
"""Small helpers for isolated, logged host builds."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

PACKAGE = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def lock():
    return json.loads((PACKAGE / 'config/source_lock.json').read_text())


def clean_env():
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(('PETALINUX', 'XILINX', 'OECORE', 'SDKTARGET', 'KBUILD_')) or key in (
                'LD_LIBRARY_PATH', 'LIBRARY_PATH', 'CPATH', 'C_INCLUDE_PATH',
                'CPLUS_INCLUDE_PATH', 'CFLAGS', 'CPPFLAGS', 'LDFLAGS', 'MAKEFLAGS',
                'MFLAGS', 'CC', 'CXX', 'KCFLAGS', 'LOCALVERSION', 'ARCH', 'CROSS_COMPILE'):
            env.pop(key, None)
    env.update(PATH='/usr/bin:/bin', LC_ALL='C')
    return env


class Run:
    def __init__(self, directory, scope):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.state = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      'scope': scope, 'commands': [], 'passed': False, 'board_verified_this_run': False}
        self.state['runner_sources'] = {
            p.name:sha(p) for p in sorted((PACKAGE/'scripts').glob('*.py'))}
        self.save()

    def save(self):
        write_json(self.directory / 'status.json', self.state)

    def command(self, name, argv, cwd, env=None):
        log = self.directory / (name + '.log')
        require(not log.exists(), 'Refusing to replace log: ' + str(log))
        start = time.monotonic()
        print('START ' + name, flush=True)
        with log.open('xb') as stream:
            process = subprocess.run(list(map(str, argv)), cwd=str(cwd), env=env,
                                     stdout=stream, stderr=subprocess.STDOUT)
        self.state['commands'].append({'name': name, 'argv': list(map(str, argv)),
                                      'cwd': str(cwd), 'exit_code': process.returncode,
                                      'log': str(log), 'sha256': sha(log),
                                      'elapsed_seconds': round(time.monotonic() - start, 3)})
        self.save()
        print('END {} exit={}'.format(name, process.returncode), flush=True)
        require(process.returncode == 0, '{} failed; see {}'.format(name, log))
        return log.read_text(errors='replace')

    def finish(self, passed, error=None):
        self.state['passed'] = passed
        self.state['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if error is not None:
            self.state['error'] = str(error)
        self.save()


def verify_fixed_sources(work, component):
    if component == 'dfx_mgr':
        expected = {str(p.relative_to(PACKAGE/'sources/dfx_mgr_patched')):sha(p)
                    for p in (PACKAGE/'sources/dfx_mgr_patched').rglob('*') if p.is_file()}
    else:
        manifest = json.loads((PACKAGE/'sources/xrt_tree.json').read_text())
        expected = {name:record['sha256'] for name,record in manifest.items()}
        for name in lock()['zocl_changed_files']:
            expected[name] = sha(PACKAGE/'sources/zocl_patched_files'/name)
    directory = Path(work)/'sources'/component
    for name, digest in expected.items():
        require((directory/name).is_file() and sha(directory/name)==digest,
                'Fixed source changed: '+str(directory/name))
    for path in directory.rglob('*'):
        if path.is_file() and str(path.relative_to(directory)) not in expected:
            require(path.suffix not in ('.c','.h','.cpp','.hpp','.mk') and path.name!='Makefile',
                    'Unexpected build source: '+str(path))
