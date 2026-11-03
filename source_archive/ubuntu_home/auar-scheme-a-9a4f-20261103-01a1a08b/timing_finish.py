"""Finish and verify the Ubuntu release only after the requested timing margins pass."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess
import sys
import time

base = Path(sys.argv[1])
vivado, vitis, implementation_run = sys.argv[2:5]
qa = base / 'verification'
package = base / 'auar_xuefei'
delivery = Path('/home/ghmd/下载/AUAR_源码工程_9a4f_20261103')
tag = Path(implementation_run).name
firmware_name = 'firmware-' + tag
roundtrip_name = 'final-roundtrip-' + tag
status_file = qa / (tag + '-finish.json')
with (qa / (tag + '-finish.lock')).open('x') as stream:
    stream.write(str(os.getpid()) + '\n')
phase = 'waiting_for_requested_timing_margins'


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def inventory():
    return {p.relative_to(package).as_posix(): sha(p)
            for p in package.rglob('*') if p.is_file()}


def status(value, **extra):
    data = dict(status=value, phase=phase,
                time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), **extra)
    temp = status_file.with_suffix('.writing')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    os.replace(str(temp), str(status_file))
    print(json.dumps(data, ensure_ascii=False), flush=True)


def run(name, command, env=None):
    global phase
    phase = name
    status('RUNNING')
    log = qa / (tag + '-finish-' + name + '.log')
    with log.open('xb') as output:
        subprocess.run([str(word) for word in command], cwd=str(base), env=env,
                       stdout=output, stderr=subprocess.STDOUT, check=True)


try:
    frozen = inventory()
    (qa / (tag + '-pre-final-source.json')).write_text(json.dumps(frozen, sort_keys=True, indent=2))
    status('RUNNING')
    receipt_file = qa / implementation_run / 'implement.receipt.json'
    while not receipt_file.is_file():
        time.sleep(30)
    receipt = json.loads(receipt_file.read_text())
    metrics = receipt.get('metrics') or {}
    if (receipt.get('status') != 'PASS' or receipt.get('stage') != 'margin_refinement'
            or metrics.get('wns_ns', -1) < 0.020 or metrics.get('whs_ns', -1) < 0.030
            or metrics.get('drc_errors', -1) != 0 or metrics.get('routing_errors', -1) != 0
            or metrics.get('routable_nets', 0) < 1
            or metrics.get('routed_nets') != metrics.get('routable_nets')
            or metrics.get('original_clock_periods_preserved') is not True
            or metrics.get('original_user_uncertainty_restored') is not True):
        raise RuntimeError('The requested original-budget timing margins have not passed: ' + str(receipt_file))
    pins = receipt['hardware_source_sha256']
    if not pins or any(sha(package / name) != digest for name, digest in pins.items()):
        raise RuntimeError('Hardware sources differ from the completed run')
    hardware = qa / implementation_run / 'hardware'
    tool = qa / 'dtc-source-check/dtc-1.7.2'
    env = os.environ.copy()
    env.update(LD_LIBRARY_PATH=str(tool / 'libfdt'), XILINX_VITIS=vitis,
               XILINX_VIVADO=vivado, PYTHONDONTWRITEBYTECODE='1', LC_ALL='C')
    run('firmware', [
        sys.executable, '-B', package / 'build/export_firmware.py',
        '--out', qa / firmware_name, '--bit', hardware / 'auar_source.bit',
        '--xsa', hardware / 'auar_source.xsa',
        '--base-dtb', '/home/ghmd/aura-system-pan-20261028/fresh-base.dtb',
        '--dtc', Path(vitis) / 'bin/dtc', '--fdtoverlay', tool / 'fdtoverlay',
        '--xclbinutil', Path(vitis) / 'bin/xclbinutil', '--bootgen', Path(vitis) / 'bin/bootgen'
    ], env)
    run('report', [sys.executable, '-B', base / 'final_report_ubuntu.py',
                   '--run', implementation_run, '--firmware', firmware_name])
    generated = {
        'report/validation_summary.md', 'report/evidence/model_build.json',
        'report/evidence/implementation_receipt.json',
        'report/evidence/hardware_results.json',
        'report/evidence/firmware_fresh.json', 'checksums.sha256'
    }
    actual = inventory()
    if ({k: v for k, v in frozen.items() if k not in generated}
            != {k: v for k, v in actual.items() if k not in generated}):
        raise RuntimeError('Unexpected source mutation after the release snapshot')
    rar = Path('/home/ghmd/auar-engineering-delivery-XpV7MC/rar-tool/usr/bin/rar')
    run('archive', [sys.executable, '-B', base / 'final_roundtrip.py',
                    package, qa, delivery, rar, vivado, vitis, implementation_run, roundtrip_name])
    result = json.loads((delivery / 'archive_verification.json').read_text())
    if result.get('status') != 'PASS':
        raise RuntimeError('Archive qualification failed')
    phase = 'complete'
    status('PASS', delivery=str(delivery), archive_sha256=result['sha256'],
           archive_bytes=result['bytes'], timing=metrics)
except Exception as exc:
    status('FAIL', error=str(exc))
    raise
