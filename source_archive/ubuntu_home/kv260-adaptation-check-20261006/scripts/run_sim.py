#!/usr/bin/env python3
import argparse,datetime,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--timebase',action='store_true')
parser.add_argument('--audio',action='store_true')
args=parser.parse_args()
assert not (args.timebase and args.audio)
top='tb_audio' if args.audio else ('tb_timebase' if args.timebase else 'tb_fit')
marker='AURA_AUDIO_TEST_PASS' if args.audio else ('AURA_TIMEBASE_TEST_PASS' if args.timebase else 'AURA_FIT_TEST_PASS')
pointer='CURRENT_AUDIO_SIM.json' if args.audio else ('CURRENT_TIMEBASE_SIM.json' if args.timebase else 'CURRENT_SIM.json')
out=ROOT/'evidence'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-'+top+'-sim')
out.mkdir()
rtl=ROOT/'fpga/rtl'/('audio_decerr.sv' if args.audio else 'motion_fit.sv')
tb=ROOT/'fpga/tests'/(top+'.sv')
snapshots=[]
for p in (rtl,tb):
    data=p.read_bytes();(out/p.name).write_bytes(data)
    snapshots.append({'source':str(p),'snapshot':p.name,'sha256':hashlib.sha256(data).hexdigest()})
(out/'source_manifest.json').write_text(json.dumps(snapshots,indent=2)+'\n')
results=[]
steps=[['xvlog','-sv',str(out/rtl.name),str(out/tb.name)],
       ['xelab',top,'-s','fit_snapshot'],['xsim','fit_snapshot','-runall']]
for index,args in enumerate(steps):
    argv=['bash','--noprofile','--norc','-c','source /home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh; exec "$@"','aura-fit-sim']+args
    p=subprocess.run(argv,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
    (out/(args[0]+'.log')).write_text(p.stdout)
    results.append({'command':args,'rc':p.returncode})
    print(p.stdout[-3500:],flush=True)
    if p.returncode:break
passed=len(results)==3 and all(x['rc']==0 for x in results) and marker in (out/'xsim.log').read_text()
status={'evidence':str(out),'passed':passed,'results':results}
(out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
(ROOT/pointer).write_text(json.dumps(status,indent=2)+'\n')
print(json.dumps(status),flush=True)
raise SystemExit(0 if passed else 1)
