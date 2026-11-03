#!/usr/bin/env python3
"""Offline exact-source HDL verification. Never accesses the board."""
import datetime
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--nominal',action='store_true')
options=parser.parse_args()
top='tb_nominal' if options.nominal else 'tb_servo'
marker='AURA_NOMINAL_TEST_PASS' if options.nominal else 'AURA_SERVO_TEST_PASS'
out = ROOT/'evidence'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-sim')
out.mkdir()
sources = [ROOT/'rtl/visual_servo.sv', ROOT/'tests'/(top+'.sv')]
hashes = {}
for path in sources:
    data = path.read_bytes()
    (out/path.name).write_bytes(data)
    hashes[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
steps = [['xvlog', '-sv', 'visual_servo.sv', top+'.sv'],
         ['xelab', top, '-s', 'servo_snapshot'],
         ['xsim', 'servo_snapshot', '-runall']]
results = []
for args in steps:
    command = ['bash', '--noprofile', '--norc', '-c',
               'source /home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh; exec "$@"', 'aura-servo-sim']+args
    result = subprocess.run(command, cwd=out, capture_output=True, text=True, timeout=180)
    log = result.stdout+result.stderr
    (out/(args[0]+'.txt')).write_text(log)
    results.append({'command': args, 'rc': result.returncode})
    print(log[-2500:], flush=True)
    if result.returncode:
        break
passed = (len(results)==3 and all(r['rc']==0 for r in results)
          and marker in (out/'xsim.txt').read_text()
          and all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==value for name,value in hashes.items()))
status = {'passed': passed, 'evidence': str(out), 'source_sha256': hashes,
          'commands': results, 'board_accessed': False}
(out/'status.json').write_text(json.dumps(status, indent=2)+'\n')
(ROOT/('CURRENT_NOMINAL_SIM.json' if options.nominal else 'CURRENT_SIM.json')).write_text(json.dumps(status, indent=2)+'\n')
print(json.dumps(status), flush=True)
raise SystemExit(0 if passed else 1)
