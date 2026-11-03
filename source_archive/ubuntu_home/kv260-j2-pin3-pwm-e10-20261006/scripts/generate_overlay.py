#!/usr/bin/env python3
"""Generate DT from this verified XSA using the preserved vendor 2022.2 repo."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
build = json.loads((ROOT/'CURRENT_BUILD.json').read_text())
assert build['complete'] and json.loads((ROOT/'FINAL_VERIFICATION.json').read_text())['passed']
xsa = Path(build['evidence'])/'artifacts/aura_pwm_probe.xsa'
repo = Path('/home/ghmd/kv260-j2-pwm-20261004/dependencies/device-tree-xlnx-2022.2')
out = ROOT/'evidence/linux-overlay-generated'
out.mkdir(exist_ok=False)
command = ['/bin/bash','--noprofile','--norc','-c',
    'aura_pwm_settings=$1; shift; aura_pwm_command=( "$@" ); set --; '
    'source "$aura_pwm_settings" || exit $?; exec "${aura_pwm_command[@]}"',
    'aura-pwm-dt','/home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh',
    '/home/ghmd/Xilinx_2022.2/Vitis/2022.2/bin/xsct',
    str(ROOT/'scripts/gen_device_tree.tcl'),str(xsa),str(repo),str(out)]
p = subprocess.run(command,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
    text=True,timeout=180)
(out/'generation.log').write_text(p.stdout)
assert p.returncode == 0 and 'AURA_PWM_DT_GENERATED' in p.stdout,p.stdout[-3000:]
report = {'complete':True,'source_xsa':str(xsa),
    'xsa_sha256':hashlib.sha256(xsa.read_bytes()).hexdigest(),
    'repository':str(repo),'repository_commit':(repo/'.git/HEAD').read_text().strip(),
    'pl_dtsi_sha256':hashlib.sha256((out/'pl.dtsi').read_bytes()).hexdigest(),
    'board_accessed':False}
(out/'generation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
