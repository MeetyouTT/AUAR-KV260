#!/usr/bin/env python3
"""Host user-service supervisor: resume routing, audit and package, no board I/O."""
import datetime as dt
import fcntl
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VIVADO = '/home/ghmd/Xilinx_2022.2/Vivado/2022.2/bin/vivado'


def main():
    with (ROOT / '.build.lock').open('a') as build_lock, (ROOT / '.finalize.lock').open('a') as finish_lock:
        fcntl.flock(build_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(finish_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        status = json.loads((ROOT / 'STATUS.json').read_text())
        completion = {'state': 'routing_resumed_20261024', 'board_accessed': False,
                      'started_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                      'local_user_service': 'aura-pan-offline-resume-20261024.service'}

        def save():
            (ROOT / 'STATUS.json').write_text(json.dumps(status, indent=2) + '\n')
            (ROOT / 'FINISH-STATUS.json').write_text(json.dumps(completion, indent=2) + '\n')

        def run_vivado(label, script, log):
            status['state'] = label + '_running'
            completion['state'] = label + '_running'
            save()
            with (ROOT / (label + '-console.txt')).open('xb') as console:
                process = subprocess.Popen([VIVADO, '-mode', 'batch', '-source', str(script),
                    '-log', str(log), '-journal', str(log.with_suffix('.jou'))],
                    cwd=ROOT, stdout=console, stderr=subprocess.STDOUT)
                status['active_host_pid'] = process.pid
                save()
                rc = process.wait()
            if rc:
                raise RuntimeError(label + ' failed, rc=' + str(rc))

        try:
            status['implementation_log'] = 'route-resume-20261024.log'
            save()
            run_vivado('route-resume-20261024', ROOT / 'route-resume-20261024.tcl', ROOT / status['implementation_log'])
            if '\nAURA_SOURCE_PLATFORM_IMPLEMENTED\n' not in (ROOT / status['implementation_log']).read_text():
                raise RuntimeError('Route completion marker missing')
            status['joint_implementation_passed'] = True
            save()
            run_vivado('audit-resume-20261024', ROOT / 'audit-final.tcl', ROOT / 'final-audit/vivado.log')
            completion['state'] = 'verifying_and_packaging'
            save()
            with (ROOT / 'finalize-console-20261024.txt').open('xb') as console:
                rc = subprocess.call([sys.executable, '-B', str(ROOT / 'finalize_offline.py')],
                                     cwd=ROOT, stdout=console, stderr=subprocess.STDOUT)
            if rc:
                raise RuntimeError('Offline packaging failed; rc=' + str(rc))
            completion.update(state='offline_package_complete', completed_utc=dt.datetime.now(dt.timezone.utc).isoformat())
            (ROOT / 'FINISH-STATUS.json').write_text(json.dumps(completion, indent=2) + '\n')
        except BaseException as error:
            status['state'] = 'offline_resume_failed'
            completion.update(state='failed', error_type=type(error).__name__, error=str(error))
            save()
            raise


if __name__ == '__main__':
    main()
