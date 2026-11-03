#!/usr/bin/env python3
"""Build the exact simulated core in a new joint output; no board access."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PARENT = Path('/home/ghmd/kv260-adaptation-check-20261006')
source = ROOT/'rtl/visual_servo.sv'
script = ROOT/'scripts/build_joint.tcl'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
sim = json.loads((ROOT/'CURRENT_SIM.json').read_text())
assert sim['passed'] and sim['source_sha256']['rtl/visual_servo.sv']==sha(source)
old = json.loads((PARENT/'CURRENT_FPGA.json').read_text())
assert old['state']=='finished' and old['rc']==0 and old['source_files_changed_during_run']==[]
assert old['usb_audio_profile'] and old['resume_stage']=='optimized'
original = Path(old['resume_checkpoint'])
assert sha(original)==old['resume_sha256']
reference = Path(old['evidence'])/'joint_routed.dcp'
assert reference.is_file()
out = ROOT/'evidence'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-joint-build')
out.mkdir()
source_hashes = {str(p.relative_to(ROOT)): sha(p) for p in [source,script,Path(__file__).resolve()]}
build_id = int(hashlib.sha256(json.dumps(source_hashes,sort_keys=True).encode()).hexdigest()[:8],16)
(out/source.name).write_bytes(source.read_bytes())
(out/script.name).write_bytes(script.read_bytes())
env = dict(os.environ, AURA_VISUAL_SERVO_ROOT=str(ROOT), AURA_VISUAL_SERVO_OUT=str(out),
           AURA_VISUAL_SERVO_INPUT=str(original), AURA_VISUAL_SERVO_REFERENCE=str(reference),
           AURA_VISUAL_SERVO_BUILD_ID=str(build_id))
status = {'state':'running','evidence':str(out),'build_id':hex(build_id),
          'source_sha256':source_hashes,'input_checkpoint':str(original),'input_sha256':sha(original),
          'incremental_reference':str(reference),'reference_sha256':sha(reference),
          'simulation_evidence':sim['evidence'],'board_accessed':False,'deployable':False}
def save():
    data=json.dumps(status,indent=2)+'\n'
    (out/'status.json').write_text(data)
    (ROOT/'CURRENT_BUILD.json').write_text(data)
save()
argv=['bash','--noprofile','--norc','-c',
      'source /home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh; exec vivado -mode batch -source "$1" -log "$2" -journal "$3"',
      'aura-visual-servo-build',str(out/script.name),str(out/'vivado.log'),str(out/'vivado.jou')]
print(json.dumps(status),flush=True)
with (out/'console.txt').open('wb') as log:
    process=subprocess.Popen(argv,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT)
    status['pid']=process.pid;save()
    rc=process.wait()
changed=[name for name,value in source_hashes.items() if sha(ROOT/name)!=value]
status.update(state='finished',rc=rc,source_files_changed_during_run=changed,
              finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
text=(out/'console.txt').read_text(errors='replace')
status['implementation_complete']=rc==0 and not changed and 'AURA_VISUAL_SERVO_JOINT_IMPLEMENTED' in text
save()
print(json.dumps(status),flush=True)
raise SystemExit(0 if status['implementation_complete'] else 1)
