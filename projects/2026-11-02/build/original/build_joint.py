"""Build the wide-pulse platform in its own directory; no board IO."""
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
VIVADO = '/home/ghmd/Xilinx_2022.2/Vivado/2022.2/bin/vivado'
REFERENCE = Path('/home/ghmd/aura-pan-joint-20261023/implementation/source_routed.dcp')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    validation = json.loads((ROOT / 'validation/rtl/result.json').read_text())
    assert {row['test'] for row in validation if row['passed']} == {'tb_wide','tb_servo','tb_pulse_guard','tb_nominal'}
    if (ROOT / 'USER_PAUSED.json').exists():
        raise RuntimeError('User paused wide-range changes; do not build or deploy for the current demonstration')
    lock = (ROOT / '.build.lock').open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert sha(REFERENCE) == 'ac5f85a14eee133b56e06a514f37e3e8db30b2ae4d16a5490b79b926a07bb77e'
    inputs = [ROOT / n for n in ('candidate/rtl/visual_servo.sv', 'platform/visual_servo.sv',
                                'platform/pin.xdc', 'prepare.tcl', 'implement.tcl')]
    pins = {str(p): sha(p) for p in inputs}
    assert sha(inputs[0]) == sha(inputs[1])
    state = dict(status='PREPARED', build_id='0x10282601', center_us=1500,
                 pulse_capability_us=[500, 2500], measured_angle_endpoints=False,
                 source_sha256=pins, started_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                 board_accessed=False, motion_commands=0, deployable=False)
    def save():
        p = ROOT / 'BUILD_STATUS.json'
        t = p.with_suffix('.tmp');t.write_text(json.dumps(state, indent=2) + '\n');t.replace(p)
    env = dict(os.environ, AURA_PLATFORM_OUT=str(ROOT / 'platform'),
               AURA_PLATFORM_BUILD_ID=str(0x10282601),
               AURA_SOURCE_IMPL_OUT=str(ROOT / 'implementation'),
               AURA_SOURCE_IMPL_REFERENCE=str(REFERENCE), OMP_NUM_THREADS='1')
    os.nice(10)
    for stage, marker in (('prepare', 'AURA_SOURCE_PLATFORM_GENERATED'),
                          ('implement', 'AURA_SOURCE_PLATFORM_IMPLEMENTED')):
        state['status'] = stage.upper() + '_RUNNING';save()
        print(state['status'], flush=True)
        with (ROOT / (stage + '-console.txt')).open('wb') as output:
            process = subprocess.Popen([VIVADO, '-mode', 'batch', '-source', str(ROOT / (stage + '.tcl')),
                                        '-log', str(ROOT / (stage + '.log')),
                                        '-journal', str(ROOT / (stage + '.jou'))],
                                       cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT)
            state['pid'] = process.pid;save()
            rc = process.wait()
        state[stage + '_exit_code'] = rc
        changed = [p for p, value in pins.items() if sha(Path(p)) != value]
        if rc or changed or marker not in (ROOT / (stage + '-console.txt')).read_text(errors='replace'):
            state.update(status=stage.upper() + '_FAILED', changed_inputs=changed);save()
            raise RuntimeError('Build stage failed: ' + stage)
        state[stage + '_passed'] = True;save()
        print(stage.upper() + '_PASS', flush=True)
    state.update(status='IMPLEMENTED_PENDING_PAIRING_AND_BOARD',
                 finished_utc=dt.datetime.now(dt.timezone.utc).isoformat());save()


if __name__ == '__main__':
    main()
