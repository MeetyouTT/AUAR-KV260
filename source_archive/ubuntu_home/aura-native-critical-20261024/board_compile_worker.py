"""Sealed-helper body. Only compile and fake callbacks; no DSO/model loading."""
import base64
import fcntl
import gzip
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == '008f3e1b-c627-4b98-b120-d2a460cdbcbe'
source = Path(sys._getframe().f_code.co_filename).resolve()
digest = hashlib.sha256(source.read_bytes()).hexdigest()
root = Path('/home/root/aura-native-critical-20261024/bridge-compile') / digest[:16]
root.mkdir(parents=True, exist_ok=True, mode=0o700)
assert not (root/'report.json').exists()

if sys.argv[1:] != ['--worker']:
    assert not sys.argv[1:]
    unit = 'aura-native-compile-' + digest[:16]
    with (root/'launch.json').open('x') as stream:
        json.dump({'unit': unit, 'source_sha256': digest, 'report': str(root/'report.json')}, stream)
    # Return promptly to the framed UART command. The compiler may need more
    # than its 35-second response budget; it must not own the UART transport.
    launch = subprocess.run(['systemd-run', '--quiet', '--unit='+unit,
        '--property=Type=oneshot', '--property=RuntimeMaxSec=180',
        '--property=Nice=19', '--property=CPUWeight=1',
        '/usr/bin/python3', '-B', str(source), '--worker'],
        capture_output=True, text=True, timeout=10)
    assert launch.returncode == 0, launch.stderr[-1000:]
    print(json.dumps({'launched': True, 'unit': unit, 'report_path': str(root/'report.json'),
                      'source_sha256': digest, 'real_dpu_jobs': 0}))
    raise SystemExit(0)

lock = (root/'worker.lock').open('a+')
fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def camera():
    with opener.open('http://127.0.0.1:8790/health', timeout=4) as stream:
        value = json.load(stream)
    schedule = value['dpu_schedule']
    return {'pid': value['pid'], 'yolo_hz': value['detection_hz'],
            'faults': {k: v['overruns'] for k, v in schedule['optional'].items()},
            'owner_fenced': schedule['owner_fenced']}


report = {'scope': 'KV260_COMPILE_LINK_AND_FAKE_CALLBACKS_ONLY', 'source_sha256': digest,
          'dpu_jobs_submitted_by_check': 0, 'production_source_changed': False,
          'library_loaded': False, 'isolation_passed': False, 'passed': False}


def run(label, argv, timeout):
    began = time.monotonic()
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    report[label] = {'exit_code': result.returncode, 'stderr': result.stderr[-4000:],
                     'seconds': time.monotonic() - began}
    assert result.returncode == 0, label + ' failed'
    return result.stdout


try:
    report['before'] = camera()
    assert report['before']['pid'] == 29563 and not report['before']['owner_fenced']
    raw = gzip.decompress(base64.b64decode(PAYLOAD))
    assert hashlib.sha256(raw).hexdigest() == PAYLOAD_SHA
    files = json.loads(raw)
    report['files_sha256'] = {n: m['sha256'] for n, m in files.items()}
    for name, meta in files.items():
        path = root/name
        assert path.parent == root
        data = base64.b64decode(meta['base64'])
        assert hashlib.sha256(data).hexdigest() == meta['sha256']
        with path.open('xb') as stream:
            stream.write(data)
    flags = ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror', '-pthread']
    run('gate_compile', flags + [str(root/'test_native_lease.cpp'), '-o', str(root/'test_native_lease')], 30)
    report['gate_result'] = json.loads(run('gate_test', [str(root/'test_native_lease')], 10))
    run('bridge_compile', flags + ['-fPIC', '-shared', '-Wl,-z,defs', str(root/'native_bridge.cpp'),
        '-o', str(root/'libaura_native_candidate.so'), '-lvart-runner', '-lxir', '-ldl'], 60)
    run('layout_compile', flags + [str(root/'test_tensor_layout.cpp'), '-o', str(root/'test_tensor_layout')], 30)
    report['layout_result'] = json.loads(run('layout_test', [str(root/'test_tensor_layout')], 10))
    report['library_sha256'] = hashlib.sha256((root/'libaura_native_candidate.so').read_bytes()).hexdigest()
    report['library_needed'] = run('readelf', ['readelf', '-d', str(root/'libaura_native_candidate.so')], 5)
    report['isolation_passed'] = report['gate_result']['passed'] and report['layout_result']['passed']
except BaseException as exc:
    report['failure'] = type(exc).__name__ + ': ' + str(exc)[-1000:]
finally:
    try:
        report['after'] = camera()
        if 'before' in report:
            before, after = report['before'], report['after']
            report['same_production_process_preserved'] = before['pid'] == after['pid']
            report['production_fault_deltas'] = {k: after['faults'][k] - before['faults'][k]
                                                for k in before['faults']}
            report['production_observation_clean'] = (report['same_production_process_preserved']
                and not after['owner_fenced'] and not any(report['production_fault_deltas'].values()))
            report['passed'] = report['isolation_passed'] and report['production_observation_clean']
    except BaseException as exc:
        report['after_failure'] = type(exc).__name__ + ': ' + str(exc)[-500:]
    temporary = root/'report.partial'
    with temporary.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    temporary.replace(root/'report.json')
    print(json.dumps({'report_path': str(root/'report.json'), 'passed': report['passed']}))
