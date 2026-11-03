from common import *
f=ROOT/'build/scripts'
f.mkdir(parents=True,exist_ok=True)
def put(n,s):
    (f/n).write_text(s,encoding='utf8',newline='\n')
orig=ROOT/'build/original'
t=(orig/'implement.tcl').read_text()
assert t.count('write_hw_platform')==1
put('implement.tcl',t[:t.index('write_bitstream -bin_file')]+'puts "AURA_ROUTED_CHECKPOINT_READY"\nclose_project\nexit\n')
t=(orig/'export_resume.tcl').read_text().replace('set root /home/ghmd/aura-pan-wide-20261028','set root [file normalize $::env(AURA_BUILD_ROOT)]')
put('export.tcl',t)
put('fpga.py',r'''"""Recreate the KV260 wide platform. Each output directory belongs to one build."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src/fpga'
HERE = Path(__file__).resolve().parent

def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def inputs():
    records = json.loads((ROOT/'build/reports/ubuntu_inputs.json').read_text())
    relevant = [r for r in records if r['path'].startswith('src/fpga/') or r['path']=='build/original/prepare.tcl']
    for r in relevant:
        p = ROOT/r['path']
        if not p.is_file() or digest(p)!=r['sha256']:
            raise SystemExit('Missing or changed FPGA input: '+str(p))
    return len(relevant)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['check','prepare','build','implement','export'])
    p.add_argument('--out',type=Path,help='new writable directory, outside release')
    p.add_argument('--checkpoint',type=Path,help='export only: independent routed DCP')
    args = p.parse_args()
    print('Verified FPGA source inputs:', inputs(),flush=True)
    if args.action=='check':
        return
    if args.out is None:
        p.error('--out required')
    work=args.out.resolve()
    if work == ROOT or ROOT in work.parents:
        p.error('--out must be outside the release')
    v = os.environ.get('VIVADO_BIN') or shutil.which('vivado')
    if not v:
        p.error('source Vivado 2022.2 settings64.sh or set VIVADO_BIN')
    version = subprocess.check_output([v,'-version'], text=True)
    if 'Vivado v2022.2' not in version:
        p.error('expected Vivado v2022.2')
    plat=work/'platform'
    impl=work/'implementation'
    env=dict(os.environ,AURA_PLATFORM_OUT=str(plat),AURA_SOURCE_IMPL_OUT=str(impl),
             AURA_SOURCE_IMPL_REFERENCE=str(SRC/'reference/incremental.dcp'),
             AURA_PLATFORM_BUILD_ID=str(0x10282601),AURA_BUILD_ROOT=str(work),OMP_NUM_THREADS='1')
    def run(stage,script,marker):
        log = work/(stage+'.stdout')
        with log.open('xb') as out:
            subprocess.run([v,'-mode','batch','-log',stage+'.log','-journal',stage+'.jou','-source',str(script)],
                       cwd=str(work),env=env,stdout=out,stderr=subprocess.STDOUT,check=True)
        if marker not in log.read_text(errors='replace'):
            raise RuntimeError('Missing success marker in '+str(log))
        print(stage, 'PASS',flush=True)
    if args.action in ('build','prepare'):
        vitis = os.environ.get('XILINX_VITIS')
        if not vitis:
            p.error('set XILINX_VITIS to the Vitis 2022.2 installation')
        ip=Path(vitis).resolve()/'data/ip'
        if not ip.is_dir():
            p.error('missing Vitis data/ip')
        work.mkdir(parents=True,exist_ok=False)
        plat.mkdir()
        shutil.copytree(str(SRC/'inputs'),str(plat/'inputs'))
        for n in ('visual_servo.sv','disabled_audio.sv','pin.xdc'):
            shutil.copyfile(str(SRC/n),str(plat/n))
        repos=[SRC/'vendor'/s for s in ('dpu_ip','platform_ip','platform_cache')]+[ip]
        (plat/'repos.txt').write_text(''.join(str(x)+'\n' for x in repos))
        run('prepare',ROOT/'build/original/prepare.tcl','AURA_SOURCE_PLATFORM_GENERATED')
    if args.action in ('build','implement'):
        if not (plat/'platform/platform.xpr').is_file():
            p.error('run prepare first for this output directory')
        impl.mkdir()
        run('implement',HERE/'implement.tcl','AURA_ROUTED_CHECKPOINT_READY')
    if args.action in ('build','implement','export'):
        if args.checkpoint:
            if args.action!='export' or not args.checkpoint.resolve().is_file():
                p.error('--checkpoint is for exporting a routed DCP to a fresh directory')
            work.mkdir(parents=True,exist_ok=False)
            impl.mkdir()
            shutil.copyfile(str(args.checkpoint.resolve()),str(impl/'source_routed.dcp'))
        if not (impl/'source_routed.dcp').is_file():
            p.error('missing implementation/source_routed.dcp')
        run('export',HERE/'export.tcl','AURA_WIDE_EXPORT_RESUMED_FROM_ROUTED_CHECKPOINT')
        if not (impl/'visual_servo_source_implemented.xsa').is_file():
            raise RuntimeError('XSA missing after export')

if __name__=='__main__':
    main()
''')
