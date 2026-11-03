#!/usr/bin/env python3
"""Run the offline framework and real Vivado stages. Outputs belong to a fresh external directory."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def hw_sources():
    files=list((ROOT/'src/fpga').rglob('*'))+list((ROOT/'src/third_party/dpu').rglob('*'))
    files += [ROOT/'build/build.tcl',ROOT/'build/rtl_results.py',ROOT/'build/reproduce.py']
    return {p.relative_to(ROOT).as_posix():digest(p) for p in sorted(files) if p.is_file() and p.suffix.lower() in {'.sv','.v','.vh','.xdc','.tcl','.ttcl','.xml','.py'}}

def run(a,stage):
    out=a.out
    rtl=out/'rtl'
    hw=out/'hardware'
    log=out/(stage+'.console.log')
    receipt=out/(stage+'.receipt.json')
    if log.exists() or receipt.exists():
        raise ValueError('Refusing to overwrite a previous stage: '+stage)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',LC_ALL='C',LANG='C')
    pins=hw_sources() if stage in ('prepare','implement') else None
    if stage=='software':
        commands=[[sys.executable,'-B',str(ROOT/'src/tools/aura_project.py'),'--config','config/runtime.sim.json','doctor'],
                  [sys.executable,'-B',str(ROOT/'src/tools/aura_project.py'),'--config','config/runtime.sim.json','demo','--out',str(out/'framework-demo')]]
        work=out
        marker=None
    elif stage=='skill':
        commands=[[sys.executable,'-B',str(ROOT/'skill/pynq-contract-testgen/scripts/reproduce.py'),'--out',str(out/'skill')]]
        work=out;marker=None
    else:
        executable=Path(a.vivado or shutil.which('vivado') or '/nonexistent/vivado').resolve()
        if not executable.is_file():raise ValueError('Select the Vivado 2022.2 executable with --vivado')
        env['XILINX_VIVADO']=str(executable.parent.parent)
        env['PATH']=str(executable.parent)+os.pathsep+env.get('PATH','')
        if stage=='rtl':
            script=ROOT/'sim/rtl/run.tcl'
            args=['--out',str(rtl)]
            work=out;marker='AUAR_RTL_PASS'
        else:
            vitis=Path(a.vitis_root or env.get('XILINX_VITIS','/nonexistent')).resolve()
            if not (vitis/'data/ip').is_dir():raise ValueError('Select Vitis 2022.2 with --vitis-root')
            env['XILINX_VITIS']=str(vitis)
            result=a.rtl_results or rtl/'result.json'
            if stage=='prepare':
                hw.mkdir(exist_ok=False)
            else:
                prepared=json.loads((out/'prepare.receipt.json').read_text())
                if prepared.get('status')!='PASS' or prepared.get('hardware_source_sha256')!=pins:raise ValueError('Prepare receipt does not match the current hardware sources')
            args=['--out',str(hw),'--stage',stage,'--vitis-root',str(vitis),'--rtl-results',str(Path(result).resolve())]
            script=ROOT/'build/build.tcl'
            work=hw;marker='AUAR_'+stage.upper()+'_PASS'
        commands=[[str(executable),'-mode','batch','-source',str(script),'-log',str(out/(stage+'.vivado.log')),'-journal',str(out/(stage+'.jou')),'-tclargs']+args]
    started=time.monotonic()
    invocations=[]
    with log.open('xb') as f:
        for cmd in commands:
            r=subprocess.run(cmd,cwd=work,env=env,stdout=f,stderr=subprocess.STDOUT)
            invocations.append({'command':cmd,'exit_code':r.returncode})
            if r.returncode:break
    ok=len(invocations)==len(commands) and all(c['exit_code']==0 for c in invocations)
    if marker:
        ok=ok and marker in log.read_text(errors='replace').splitlines()
    if pins is not None:ok=ok and hw_sources()==pins
    if stage=='implement':ok=ok and all((hw/n).is_file() and (hw/n).stat().st_size for n in ['auar_source.bit','auar_source.xsa','reports/implementation.json'])
    info={'stage':stage,'status':'PASS' if ok else 'FAIL','commands':invocations,'success_marker':marker,'log_sha256':digest(log),
          'elapsed_seconds':round(time.monotonic()-started,3),'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'board_accessed':False}
    if pins is not None:info['hardware_source_sha256']=pins
    receipt.write_text(json.dumps(info,indent=2)+'\n')
    print(stage,info['status'],str(receipt),flush=True)
    if not ok:raise RuntimeError('Stage failed; see '+str(log))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--stage',choices=['software','skill','rtl','prepare','implement','hardware','all'],default='all')
    p.add_argument('--vivado')
    p.add_argument('--vitis-root')
    p.add_argument('--rtl-results',type=Path)
    a=p.parse_args();a.out=a.out.resolve()
    if a.out==ROOT or ROOT in a.out.parents:raise ValueError('Output must be outside the package')
    if a.stage in ('all','hardware') and a.out.exists():raise ValueError('Choose a new output directory')
    a.out.mkdir(parents=True,exist_ok=True)
    stages={'all':['software','skill','rtl','prepare','implement'],'hardware':['rtl','prepare','implement']}.get(a.stage,[a.stage])
    for stage in stages:run(a,stage)
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,RuntimeError,KeyError) as e:
        print('ERROR:',e,file=sys.stderr);sys.exit(1)

