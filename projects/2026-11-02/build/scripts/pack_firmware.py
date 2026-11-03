"""Make the board payload from a checked XSA. Runs offline and only writes --out."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'build/original'))
from bitstream_pairing import check_pairing
APP='aura-visual-servo-b4096-wide-v1'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xsa',required=True,type=Path)
    parser.add_argument('--bit',required=True,type=Path,help='companion bitstream from the same routed design')
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    dest=args.out.resolve()
    if dest==ROOT or ROOT in dest.parents:
        parser.error('use a new output outside the package')
    with zipfile.ZipFile(args.xsa) as z:
        bits=[n for n in z.namelist() if n.endswith('.bit')]
        if len(bits)!=1 or not any(n.endswith('.hwh') for n in z.namelist()):
            raise SystemExit('XSA must contain one bitstream and a hardware handoff')
        raw=z.read(bits[0])
    paired=check_pairing(args.bit.read_bytes(),raw)
    dest.mkdir(parents=True,exist_ok=False)
    stage=dest/APP
    stage.mkdir()
    (dest/'visual_servo_paired.bit').write_bytes(raw)
    (dest/'full_pl.bif').write_text('all:\n{\n [destination_device=pl] visual_servo_paired.bit\n}\n')
    bootgen=os.environ.get('BOOTGEN','bootgen')
    subprocess.run([bootgen,'-arch','zynqmp','-image','full_pl.bif','-o',str(stage/(APP+'.bit.bin'))],cwd=str(dest),check=True)
    # The DPU ABI and fixed overlay are frozen to the released wide platform.
    # Require matching register/IP layouts before pairing existing XCLBIN/DTBO.
    with zipfile.ZipFile(ROOT/'board/handoff/wide.xsa') as az, zipfile.ZipFile(args.xsa) as bz:
        def hwh(z):
            names=[n for n in z.namelist() if n.rsplit('/',1)[-1]=='kv260_ispMipiRx_vcu_DP.hwh']
            if len(names)!=1:
                raise ValueError('expected a single KV260 handoff')
            return z.read(names[0])
        if hwh(az)!=hwh(bz):
            raise SystemExit('HWH differs from audited platform; review ABI and regenerate companion artifacts')
    source=ROOT/'board/firmware'/APP
    manifest=json.loads((ROOT/'board/firmware_pairing.json').read_text())
    for n in [APP+'.dtbo',APP+'.xclbin','shell.json']:
        payload=(source/n).read_bytes()
        key='/lib/firmware/xilinx/'+APP+'/'+n
        if hashlib.sha256(payload).hexdigest()!=manifest['runtime_files'][key]:
            raise SystemExit('Reference payload hash mismatch: '+n)
        (stage/n).write_bytes(payload)
    (dest/'pairing.json').write_text(json.dumps(paired,indent=2)+'\n')
    print('Verified firmware set:',stage)

if __name__=='__main__':
    main()
