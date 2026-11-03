#!/usr/bin/env python3
"""Build the audited source project. No board connection or deployment."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    stage=json.loads((ROOT/'CURRENT_SOURCE_PLATFORM.json').read_text())
    audit=json.loads((ROOT/'CURRENT_SOURCE_PLATFORM_AUDIT.json').read_text())
    build=json.loads((ROOT/'CURRENT_BUILD.json').read_text())
    assert stage['generation_passed'] and audit['generated_handoff_checks_passed']
    out=ROOT/'evidence'/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-source-implementation');out.mkdir()
    platform=Path(stage['evidence'])
    # Reuse existing vendor synthesis cache through an isolated copy.
    cache=Path('/home/ghmd/kv260-m3-axilite-20261002/src/kv260/overlays/examples/benchmark/binary_container_1/ip_cache')
    shutil.copytree(cache,platform/'ip_cache',dirs_exist_ok=True)
    script=ROOT/'scripts/implement_source_platform.tcl'
    (out/script.name).write_bytes(script.read_bytes())
    protected=[script,Path(__file__).resolve(),ROOT/'rtl/visual_servo.sv',Path(audit['generated_bd']),Path(audit['generated_hwh']),platform/'pin.xdc']
    hashes={str(p):sha(p) for p in protected}
    reference=Path(build['evidence'])/'joint_routed.dcp'
    env=dict(os.environ,AURA_SOURCE_IMPL_OUT=str(out),AURA_PLATFORM_OUT=str(platform),AURA_SOURCE_IMPL_REFERENCE=str(reference))
    status=dict(state='running',evidence=str(out),platform_evidence=str(platform),build_id=stage['build_id'],
                source_sha256=hashes,incremental_reference=str(reference),reference_sha256=sha(reference),
                board_accessed=False,deployable=False)
    def save():
        text=json.dumps(status,indent=2)+'\n'
        (out/'status.json').write_text(text);(ROOT/'CURRENT_SOURCE_IMPLEMENTATION.json').write_text(text)
    save();print(json.dumps(status),flush=True)
    argv=['bash','--noprofile','--norc','-c',
          'source /home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh; exec vivado -mode batch -source "$1" -log "$2" -journal "$3"',
          'aura-source-implementation',str(out/script.name),str(out/'vivado.log'),str(out/'vivado.jou')]
    with (out/'console.txt').open('wb') as log:
        process=subprocess.Popen(argv,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT)
        status['pid']=process.pid;save();rc=process.wait()
    changed=[name for name,value in hashes.items() if sha(Path(name)) != value]
    status.update(state='finished',rc=rc,input_files_changed=changed,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    status['implementation_passed']=rc==0 and not changed and 'AURA_SOURCE_PLATFORM_IMPLEMENTED' in (out/'console.txt').read_text(errors='replace')
    save();print(json.dumps(status),flush=True)
    return 0 if status['implementation_passed'] else 1

if __name__=='__main__':
    raise SystemExit(main())
