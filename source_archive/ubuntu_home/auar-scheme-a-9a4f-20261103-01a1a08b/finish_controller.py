"""One-shot continuation of the authorized Ubuntu build, export and release verification."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

base = Path(sys.argv[1])
vivado, vitis = sys.argv[2:4]
qa = base / 'verification'
package = base / 'auar_xuefei'
delivery = Path('/home/ghmd/下载/AUAR_源码工程_9a4f_20261103')
status_file = qa / 'finish-controller.json'
lock = qa / 'finish-controller.lock'
with lock.open('x') as stream:
    stream.write(str(os.getpid()) + '\n')
phase = 'waiting_for_implementation'


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def inventory():
    return {p.relative_to(package).as_posix(): sha(p) for p in package.rglob('*') if p.is_file()}


def status(value, **extra):
    data = dict(status=value, phase=phase, time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), **extra)
    temp = status_file.with_suffix('.writing')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    os.replace(str(temp), str(status_file))
    print(json.dumps(data, ensure_ascii=False), flush=True)


def run(name, command, env=None):
    global phase
    phase = name
    status('RUNNING')
    log = qa / ('finish-' + name + '.log')
    with log.open('xb') as output:
        subprocess.run([str(word) for word in command], cwd=str(base), env=env,
                       stdout=output, stderr=subprocess.STDOUT, check=True)


try:
    frozen = inventory()
    (qa / 'pre-final-source.json').write_text(json.dumps(frozen, sort_keys=True, indent=2))
    status('RUNNING')
    receipt_file = qa / 'run01/implement.receipt.json'
    while not receipt_file.is_file():
        time.sleep(30)
    receipt = json.loads(receipt_file.read_text())
    if receipt.get('status') != 'PASS':
        raise RuntimeError('Implementation failed. Review run01/implement.console.log')
    source_pins = receipt['hardware_source_sha256']
    if not source_pins or any(sha(package / name) != digest for name, digest in source_pins.items()):
        raise RuntimeError('Hardware source differs from the completed run')
    hardware = qa / 'run01/hardware'
    tool = qa / 'dtc-source-check/dtc-1.7.2'
    env = os.environ.copy()
    env.update(LD_LIBRARY_PATH=str(tool / 'libfdt'), XILINX_VITIS=vitis,
               XILINX_VIVADO=vivado, PYTHONDONTWRITEBYTECODE='1', LC_ALL='C')
    run('firmware', [
        sys.executable, '-B', package / 'build/export_firmware.py',
        '--out', qa / 'firmware-fresh01', '--bit', hardware / 'auar_source.bit',
        '--xsa', hardware / 'auar_source.xsa',
        '--base-dtb', '/home/ghmd/aura-system-pan-20261028/fresh-base.dtb',
        '--dtc', Path(vitis) / 'bin/dtc', '--fdtoverlay', tool / 'fdtoverlay',
        '--xclbinutil', Path(vitis) / 'bin/xclbinutil', '--bootgen', Path(vitis) / 'bin/bootgen'
    ], env)
    run('report', [sys.executable, '-B', base / 'final_report_ubuntu.py'])
    generated = {
        'report/validation_summary.md',
        'report/evidence/model_build.json',
        'report/evidence/implementation_receipt.json',
        'report/evidence/hardware_results.json',
        'report/evidence/firmware_fresh.json',
        'checksums.sha256'
    }
    actual = inventory()
    if {k: v for k, v in frozen.items() if k not in generated} != {k: v for k, v in actual.items() if k not in generated}:
        raise RuntimeError('Unexpected source or document mutation after the release snapshot')
    rar = Path('/home/ghmd/auar-engineering-delivery-XpV7MC/rar-tool/usr/bin/rar')
    run('archive', [sys.executable, '-B', base / 'final_roundtrip.py',
                    package, qa, delivery, rar, vivado, vitis])
    result = json.loads((delivery / 'archive_verification.json').read_text())
    if result.get('status') != 'PASS':
        raise RuntimeError('Archive qualification failed')
    phase = 'complete'
    status('PASS', delivery=str(delivery), archive_sha256=result['sha256'], archive_bytes=result['bytes'])
except Exception as exc:
    status('FAIL', error=str(exc))
    raise

