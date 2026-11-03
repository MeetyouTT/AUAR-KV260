#!/usr/bin/env python3
"""Offline final-checkpoint audit with immutable inputs and explicit release gaps."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
build = json.loads((ROOT/'CURRENT_BUILD.json').read_text())
assert build['state']=='finished' and build['implementation_complete'] and build['rc']==0
assert build['source_files_changed_during_run']==[]
implementation = Path(build['evidence']).resolve()
assert ROOT in implementation.parents
for name, digest in build['source_sha256'].items():
    assert sha(ROOT/name)==digest, 'Build source changed: '+name
for name in ['visual_servo.sv','build_joint.tcl']:
    source = 'rtl/'+name if name.endswith('.sv') else 'scripts/'+name
    assert sha(implementation/name)==build['source_sha256'][source]
checkpoint = implementation/'joint_routed.dcp'
stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
out = ROOT/'evidence'/(stamp+'-final-audit')
out.mkdir()
inputs = {str(p):sha(p) for p in [checkpoint,implementation/'visual_servo_joint.bit',implementation/'visual_servo_joint.bin',ROOT/'scripts/audit_joint.tcl',Path(__file__).resolve()]}
for name in ['audit_joint.tcl','audit_joint.py']:
    (out/name).write_bytes((ROOT/'scripts'/name).read_bytes())
status = dict(state='running',evidence=str(out),implementation=str(implementation),
              build_id=build['build_id'],input_sha256=inputs,board_accessed=False,
              design_modified=False,deployable=False)
def save():
    data = json.dumps(status,indent=2)+'\n'
    (out/'status.json').write_text(data)
    (ROOT/'CURRENT_AUDIT.json').write_text(data)
save()
env = dict(os.environ,AURA_AUDIT_OUT=str(out),AURA_AUDIT_DCP=str(checkpoint))
argv = ['bash','--noprofile','--norc','-c',
        'source /home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh; exec vivado -mode batch -source "$1" -log "$2" -journal "$3"',
        'aura-final-audit',str(out/'audit_joint.tcl'),str(out/'vivado.log'),str(out/'vivado.jou')]
print(json.dumps(status),flush=True)
with (out/'console.txt').open('wb') as log:
    try:
        rc = subprocess.call(argv,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
    except subprocess.TimeoutExpired:
        rc = 124
status.update(state='finished',rc=rc,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              input_files_changed=[name for name,digest in inputs.items() if sha(Path(name))!=digest])
console = (out/'console.txt').read_text(errors='replace')
errors = re.findall(r'^AURA_VISUAL_SERVO_AUDIT_ERROR=(.*)$',console,re.M)
if errors:status['tool_error'] = errors[-1]
passed = rc==0 and not status['input_files_changed'] and bool(re.search(r'^AURA_VISUAL_SERVO_FINAL_PROPERTIES_VERIFIED$',console,re.M))
try:
    timing = (out/'timing.rpt').read_text()
    summary = re.search(r'WNS\(ns\).*?\n\s*[- ]+\n\s*([^\n]+)',timing,re.S)
    assert summary
    values = summary.group(1).split();assert len(values)==12
    keys = ['wns_ns','tns_ns','setup_failing','setup_total','whs_ns','ths_ns','hold_failing','hold_total','wpws_ns','tpws_ns','pulse_failing','pulse_total']
    metrics = {k:float(v) if k.endswith('_ns') else int(v) for k,v in zip(keys,values)}
    assert all(metrics[k]>=0 for k in ['wns_ns','whs_ns','wpws_ns'])
    assert all(metrics[k]==0 for k in ['setup_failing','hold_failing','pulse_failing'])
    assert metrics['setup_total']>0 and metrics['hold_total']>0
    status['timing'] = metrics
    route = (out/'route.rpt').read_text()
    nets = {}
    for name in ['# of routable nets','# of fully routed nets','# of nets with routing errors']:
        match = re.search(re.escape(name)+r'\.*\s*:\s*(\d+)',route);assert match
        nets[name] = int(match.group(1))
    assert nets['# of routable nets']==nets['# of fully routed nets']>0 and nets['# of nets with routing errors']==0
    status['route'] = nets
    drc = (out/'drc.rpt').read_text()
    rows = re.findall(r'^\|\s*([\w-]+)\s*\|\s*(Warning|Error|Critical Warning)\s*\|([^|]+)\|\s*(\d+)\s*\|',drc,re.M)
    total = re.search(r'Violations found:\s*(\d+)',drc);assert total
    assert sum(int(row[3]) for row in rows)==int(total.group(1))
    assert not any(row[1]!='Warning' for row in rows)
    status['drc_rule_counts'] = {r[0]:dict(severity=r[1],count=int(r[3])) for r in rows}
    bus = (out/'bus_skew.rpt').read_text()
    slacks = [float(x) for x in re.findall(r'Slack\s*\((?:MET|VIOLATED)\)\s*:\s*([-+\d.]+)ns',bus)]
    assert slacks and min(slacks)>=0 and 'VIOLATED' not in bus
    status['bus_skew_worst_slack_ns'] = min(slacks)
    checks = (out/'check_timing.rpt').read_text()
    gaps = {k:int(v) for k,v in re.findall(r'checking (\w+) \((\d+)\)',checks)}
    assert all(gaps.get(k,-1)==0 for k in ['no_clock','constant_clock','pulse_width_clock','unconstrained_internal_endpoints','multiple_clock','generated_clocks','loops','partial_input_delay','partial_output_delay','latch_loops'])
    status['timing_check_counts'] = gaps
    status['external_timing_gaps'] = {k:gaps[k] for k in ['no_input_delay','no_output_delay']}
    status['properties'] = (out/'properties.tsv').read_text()
    pad = (out/'pwm_timing.rpt').read_text()
    assert 'servo_pwm_reg/C' in pad and 'period=10.000ns' in pad and 'Destination:            servo_pwm' in pad
    match = re.search(r'Slack\s*\(MET\)\s*:\s*([-+\d.]+)ns',pad);assert match and float(match.group(1))>=0
    status['pwm_pad_slack_ns'] = float(match.group(1))
except (AssertionError,FileNotFoundError,KeyError,ValueError) as error:
    passed = False
    status['verification_error'] = type(error).__name__+': '+str(error)
status['offline_checkpoint_passed'] = passed
status['reports_sha256'] = {p.name:sha(p) for p in out.iterdir() if p.suffix in ['.rpt','.tsv']}
status['implementation_critical_warnings'] = re.findall(r'^CRITICAL WARNING:.*$',(implementation/'console.txt').read_text(),re.M)
status['remaining'] = ['Matching BD/XSA/HWH and retired audio DT nodes',
                       'DT/XCLBIN provenance and runtime identity',
                       'Single-writer transport and measured submission budget',
                       'Board coexistence, electrical PWM and stop/expiry tests',
                       'Physical reference and fixed-camera measured mapping']
save()
print(json.dumps({k:v for k,v in status.items() if k not in ['input_sha256','properties','implementation_critical_warnings']}),flush=True)
raise SystemExit(0 if passed else 1)
