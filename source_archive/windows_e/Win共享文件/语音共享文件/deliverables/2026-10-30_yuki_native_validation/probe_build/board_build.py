from pathlib import Path
import hashlib
import json
import os
import platform
import subprocess
import sys
import time

ROOT = Path('/home/root/aura-yuki-validation-20261030')


def snapshot():
    fields = subprocess.run(['systemctl', 'show', 'aura-avatar-ui.service',
                             '-p', 'MainPID', '-p', 'ActiveState', '-p', 'ExecStart',
                             '-p', 'FragmentPath', '-p', 'DropInPaths'],
                            capture_output=True, text=True, check=True).stdout
    return {'ui_service': fields,
            'boot': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'machine': platform.machine(), 'kernel': platform.release(),
            'memory': [s for s in Path('/proc/meminfo').read_text().splitlines()
                       if s.startswith(('MemTotal:', 'MemAvailable:'))]}


def run():
    result = {'before': snapshot(), 'started_unix': time.time(), 'steps': []}
    with (ROOT / 'build.log').open('w') as log:
        commands = [
            ['cmake', '--version'], ['g++', '--version'],
            ['nice', '-n', '15', 'cmake', '-S', str(ROOT / 'probe_build'),
             '-B', str(ROOT / 'build'), '-DCMAKE_BUILD_TYPE=Release'],
            ['nice', '-n', '15', 'cmake', '--build', str(ROOT / 'build'), '-j', '1'],
            ['nice', '-n', '15', str(ROOT / 'build/yuki_runtime_audit'),
             str(ROOT / 'inputs/ems/yuk_0.ems.json'),
             str(ROOT / 'inputs/ems/yuk_0.ems.resx.json'),
             '--resource-root', str(ROOT / 'inputs/ems'),
             '--output', str(ROOT / 'cpu-audit.json'), '--steps', '180']]
        for command in commands:
            started = time.monotonic()
            log.write(json.dumps({'command': command}) + '\n'); log.flush()
            value = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL, timeout=300)
            result['steps'].append({'command': command, 'returncode': value.returncode,
                                    'elapsed_seconds': time.monotonic() - started})
            if value.returncode:
                break
    result['after'] = snapshot()
    result['completed_unix'] = time.time()
    result['production_ui_pid_unchanged'] = (
        result['before']['ui_service'] == result['after']['ui_service'])
    binary = ROOT / 'build/yuki_runtime_audit'
    if binary.exists():
        result['binary_sha256'] = hashlib.sha256(binary.read_bytes()).hexdigest()
    (ROOT / 'build-result.json').write_text(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        run()
    except Exception as error:
        (ROOT / 'build-exception.json').write_text(json.dumps({'error': str(error)}))
        raise
