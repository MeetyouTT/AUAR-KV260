#!/usr/bin/env python3
"""Offline runner; never contacts or programs a board."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = '/home/ghmd/Xilinx_2022.2/Vivado/2022.2/settings64.sh'
BIN = Path('/home/ghmd/Xilinx_2022.2/Vivado/2022.2/bin')
phase = sys.argv[1]
if phase not in ('sim', 'build'):
    raise SystemExit('Usage: python3 scripts/run.py sim|build')
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out = ROOT / 'evidence' / (stamp + '-' + phase)
out.mkdir(parents=True, exist_ok=False)
status = {'phase': phase, 'started_utc': stamp, 'evidence': str(out),
          'complete': False, 'board_accessed': False, 'commands': []}

def save():
    text = json.dumps(status, indent=2) + '\n'
    (out / 'status.json').write_text(text)
    (ROOT / ('CURRENT_' + phase.upper() + '.json')).write_text(text)

def run(label, args, timeout=300, marker=None):
    argv = ['/bin/bash', '--noprofile', '--norc', '-c',
            'aura_pwm_settings=$1; shift; aura_pwm_command=( "$@" ); set --; '
            'source "$aura_pwm_settings" || exit $?; exec "${aura_pwm_command[@]}"',
            'aura-pwm-offline', SETTINGS] + list(map(str, args))
    env = os.environ.copy()
    env['AURA_PWM_ROOT'] = str(ROOT)
    env['AURA_PWM_OUT'] = str(out)
    with (out / (label + '.log')).open('xb') as log:
        completed = subprocess.run(argv, cwd=out, env=env, stdout=log,
                                   stderr=subprocess.STDOUT, timeout=timeout)
    content = (out / (label + '.log')).read_text(errors='replace')
    good = (completed.returncode == 0 and (not marker or marker in content)
            and '\nFatal:' not in content and '\nERROR:' not in content
            and '\nCRITICAL WARNING:' not in content)
    status['commands'].append({'label': label, 'rc': completed.returncode,
                              'marker': marker, 'passed': good,
                              'log_sha256': hashlib.sha256(content.encode()).hexdigest()})
    save()
    print(json.dumps({'command': label, 'passed': good, 'rc': completed.returncode}), flush=True)
    if not good:
        raise RuntimeError(f'{label} failed; inspect {out / (label + ".log")}')

try:
    run('prepare', ['python3', ROOT / 'scripts/prepare.py'])
    status['rtl_sha256'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (ROOT / 'rtl/pwm_burst.sv', ROOT / 'rtl/aura_pwm_probe.sv')}
    status['input_sha256'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (ROOT / 'scripts/run.py', ROOT / 'scripts/build.tcl',
                                        ROOT / 'constraints/j2.xdc', ROOT / 'tests/tb_burst.sv',
                                        ROOT / 'tests/tb_axi.sv')}
    (out / 'source_identity.json').write_bytes((ROOT / 'evidence/source_identity.json').read_bytes())
    save()
    if phase == 'sim':
        run('compile', [BIN / 'xvlog', '--sv', ROOT / 'rtl/pwm_burst.sv',
            ROOT / 'rtl/aura_pwm_probe.sv', ROOT / 'tests/tb_burst.sv', ROOT / 'tests/tb_axi.sv'])
        for top, marker in [('tb_burst', 'AURA_BURST_ALL_PASS'), ('tb_axi', 'AURA_AXI_ALL_PASS')]:
            run(top + '-elaborate', [BIN / 'xelab', top, '-s', top + '_snapshot'])
            run(top + '-run', [BIN / 'xsim', top + '_snapshot', '-runall'], marker=marker)
    else:
        sim = json.loads((ROOT / 'CURRENT_SIM.json').read_text())
        if not sim['complete'] or sim.get('rtl_sha256') != status['rtl_sha256']:
            raise RuntimeError('Build requires passed simulation of the exact same RTL')
        run('vivado', [BIN / 'vivado', '-mode', 'batch', '-source',
            ROOT / 'scripts/build.tcl', '-log', out / 'vivado.log',
            '-journal', out / 'vivado.jou'], timeout=2400,
            marker='AURA_PWM_OFFLINE_BUILD_PASS')
        status['simulation_evidence'] = sim['evidence']
    status['complete'] = True
except Exception as exc:
    status['error'] = f'{type(exc).__name__}: {exc}'
finally:
    status['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save()
print(json.dumps({'phase': phase, 'complete': status['complete'],
                  'error': status.get('error'), 'evidence': str(out)}), flush=True)
raise SystemExit(0 if status['complete'] else 1)
