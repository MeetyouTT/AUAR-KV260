"""Bind fresh XSim commands, exit codes, output markers and current sources to one receipt."""
import argparse
import datetime
import hashlib
import json
import re
from pathlib import Path

MARKERS = {
    'tb_nominal': 'AURA_NOMINAL_TEST_PASS',
    'tb_wide': 'AURA_WIDE_TEST_PASS',
    'tb_pulse_guard': 'AURA_V2_PULSE_GUARD_OFFLINE_PASS_NOT_BOARD_RELEASE',
    'tb_servo': 'AURA_SERVO_TEST_PASS',
}
STAGES = ('xvlog', 'xelab', 'xsim')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def pins(root):
    files = ['src/fpga/rtl/visual_servo.sv','sim/rtl/run.tcl','build/rtl_results.py']
    files.extend('sim/rtl/'+name+'.sv' for name in MARKERS)
    return {p:sha(root/p) for p in files}

def outside(root, out):
    if root == out or root in out.parents:
        raise ValueError('RTL output must be outside the source tree')

def items(out):
    rows=[]
    for name,marker in MARKERS.items():
        work=out/name
        stages=[]
        for stage in STAGES:
            rc=work/(stage+'.exitcode')
            cmd=work/(stage+'.argv')
            log=work/(stage+'.console.log')
            if not (rc.is_file() and cmd.is_file() and log.is_file()):
                stages.append({'stage':stage,'status':'NOT_RUN'})
                continue
            argv=cmd.read_text().splitlines()
            code=int(rc.read_text().strip())
            contents=log.read_text(errors='replace')
            success=bool(argv) and Path(argv[0]).name==stage and code==0 and bool(contents.strip())
            if stage=='xsim':
                success=success and marker in contents and not re.search(r'(?im)^\s*(?:Fatal:|ERROR:|FATAL_ERROR:)',contents)
            stages.append({'stage':stage,'argv':argv,'exit_code':code,'log':log.relative_to(out).as_posix(),
                           'log_sha256':sha(log),'status':'PASS' if success else 'FAIL'})
        row_status='PASS' if all(s['status']=='PASS' for s in stages) else ('FAIL' if any(s['status']=='FAIL' for s in stages) else 'NOT_RUN')
        rows.append({'test':name,'expected_marker':marker,'stages':stages,'status':row_status})
    return rows

def record(root,out):
    before=json.loads((out/'inputs.before.json').read_text())
    source=pins(root)
    rows=items(out)
    version=(out/'tool_version.txt').read_text().strip()
    status='PASS' if before==source and '2022.2' in version and all(r['status']=='PASS' for r in rows) else 'FAIL'
    return {'schema':'auar.xsim.1','status':status,'tool_version':version,'source_sha256':source,
            'source_unchanged':before==source,'tests':rows,'board_verified':False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['snapshot','finalize','verify'])
    p.add_argument('--root',required=True,type=Path)
    p.add_argument('--out',type=Path)
    p.add_argument('--result',type=Path)
    a=p.parse_args()
    root=a.root.resolve()
    if a.action=='verify':
        if a.result is None or a.result.name!='result.json':p.error('specify --result /path/to/rtl/result.json')
        out=a.result.resolve().parent
        outside(root,out)
        saved=json.loads(a.result.read_text())
        current=record(root,out)
        if any(saved.get(k)!=v for k,v in current.items()) or current['status']!='PASS':
            raise ValueError('missing, failed, stale or inconsistent RTL evidence')
    else:
        if a.out is None:p.error('--out required')
        out=a.out.resolve()
        outside(root,out)
        if a.action=='snapshot':
            with (out/'inputs.before.json').open('x') as f:json.dump(pins(root),f,sort_keys=True,indent=2)
            return
        current=record(root,out)
        current['completed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        with (out/'result.json').open('x') as f:json.dump(current,f,sort_keys=True,indent=2)
        if current['status']!='PASS':raise ValueError('see result.json and individual logs')
    print('PASS four XSim benches with matching sources, stage exits and logs')
if __name__=='__main__':main()

