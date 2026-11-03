#!/usr/bin/env python3
"""Finish only this offline build's audit/package when its Vivado process exits."""
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
VIVADO = '/home/ghmd/Xilinx_2022.2/Vivado/2022.2/bin/vivado'


def save(value):
    temporary = ROOT / 'FINISH-STATUS.json.tmp'
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(ROOT / 'FINISH-STATUS.json')


def main():
    os.nice(15)
    with (ROOT / '.finalize.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        build = json.loads((ROOT / 'STATUS.json').read_text())
        pid, started = build['active_host_pid'], build['active_process_start_ticks']
        status = {'state': 'waiting_for_own_implementation', 'board_accessed': False,
                  'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'build_pid': pid}
        save(status)
        try:
            while True:
                process = Path('/proc') / str(pid)
                try:
                    fields = (process / 'stat').read_text().split()
                    if fields[21] != started or fields[2] == 'Z':
                        break
                    argv = (process / 'cmdline').read_bytes()
                    if b'/home/ghmd/aura-pan-joint-20261023/implement-resume.tcl' not in argv:
                        break
                except FileNotFoundError:
                    break
                time.sleep(15)
            log = (ROOT / 'implement-host.log').read_text(errors='replace')
            if 'AURA_SOURCE_PLATFORM_IMPLEMENTED\n' not in log:
                raise RuntimeError('Own implementation exited without successful marker')
            require_files = ['source_routed.dcp', 'visual_servo_source.bit', 'visual_servo_source_implemented.xsa']
            if not all((ROOT / 'implementation' / name).is_file() for name in require_files):
                raise RuntimeError('Successful implementation artifacts missing')
            status['state'] = 'independent_audit_running'
            save(status)
            command = [VIVADO, '-mode', 'batch', '-source', str(ROOT / 'audit-final.tcl'),
                       '-log', str(ROOT / 'final-audit/vivado.log'), '-journal', str(ROOT / 'final-audit/vivado.jou')]
            with (ROOT / 'final-audit/console.txt').open('wb') as output:
                rc = subprocess.call(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
            if rc:
                raise RuntimeError('Independent Vivado audit failed: ' + str(rc))
            status['state'] = 'verifying_and_packaging'
            save(status)
            with (ROOT / 'finalize-console.txt').open('wb') as output:
                rc = subprocess.call([sys.executable, '-B', str(ROOT / 'finalize_offline.py')],
                                     cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
            if rc:
                raise RuntimeError('Offline report/metadata/package verification failed: ' + str(rc))
            status.update(state='offline_package_complete', completed_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                manifest_sha256=hashlib.sha256((ROOT / 'bundle/candidate-manifest.json').read_bytes()).hexdigest())
            save(status)
            print(json.dumps(status), flush=True)
        except BaseException as error:
            status.update(state='failed', error_type=type(error).__name__, error=str(error))
            save(status)
            raise


if __name__ == '__main__':
    main()
