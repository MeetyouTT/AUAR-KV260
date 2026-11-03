"""Verify one extracted release on a single CPU. The report must be outside the release."""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[2]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',required=True,type=Path)
    args=ap.parse_args()
    out=args.out.resolve()
    if out==ROOT or ROOT in out.parents:
        ap.error('choose a new --out outside the release')
    out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    py=[sys.executable,'-B']
    steps=[
        ('release',ROOT,py+['build/scripts/verify.py']),
        ('fpga_inputs',ROOT,py+['build/scripts/fpga.py','check']),
        ('motion_fixture',ROOT/'sim/motion',py+['run_pure_suite.py']),
        ('skill_a',ROOT/'skill/command_guard_validation',py+['scripts/run_checks.py']),
        ('skill_b',ROOT/'skill/perception_freshness_benchmark',py+['-m','unittest','discover','-s','tests','-v']),
        ('skill_b_measured',ROOT/'skill/perception_freshness_benchmark',py+['scripts/analyze_counters.py','examples/public_counters.json']),
        ('skill_c',ROOT/'skill/llm_voice_runtime_optimization',py+['scripts/check.py']),
        ('pynq_unit',ROOT/'skill/pynq_contract_testgen',py+['-m','unittest','discover','-s','tests','-v']),
        ('pynq_examples',ROOT/'skill/pynq_contract_testgen',py+['scripts/reproduce.py','--out',str(out/'pynq')]),
    ]
    result={'python':platform.python_version(),'platform':platform.platform(),'cpu_affinity_count':len(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,'board_or_gpu_used':False,'steps':[]}
    for name,cwd,cmd in steps:
        t=time.monotonic()
        with (out/(name+'.log')).open('wb') as f:
            r=subprocess.run(cmd,cwd=str(cwd),env=env,stdout=f,stderr=subprocess.STDOUT)
        result['steps'].append(dict(name=name,exit_code=r.returncode,elapsed_seconds=round(time.monotonic()-t,3)))
        result['status']='FAIL' if r.returncode else 'RUNNING'
        (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
        print(name,result['steps'][-1]['exit_code'],flush=True)
        if r.returncode:raise SystemExit('Failed, see '+str(out/(name+'.log')))
    result['status']='PASS'
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS',out/'summary.json')

if __name__=='__main__':main()
