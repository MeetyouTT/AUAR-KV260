"""Run the prepared B variant; preserve the incomplete A/B report as evidence.

Only orchestration is specialized. Native source hashes, rollback finalizer,
budgets, validation and all measurement statements come from the pinned helper.
"""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ORIGINAL=Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/helpers/331f485bd54678ae/source.py')
EXPECTED='331f485bd54678aea972fb09078573eaf45ff08fab82a931fd17709c2e203bf9'
ROOT=Path('/home/root/aura-dpu-vision-20261021/sface-retry-ab/331f485bd54678ae')
source=Path(sys._getframe().f_code.co_filename).resolve()
digest=hashlib.sha256(source.read_bytes()).hexdigest()
assert hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()==EXPECTED

if os.environ.get('AURA_SFACE_B_ONLY_RUN')=='1':
    spec=importlib.util.spec_from_file_location('_pinned_ab',ORIGINAL)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    tree=ast.parse(ORIGINAL.read_text())
    run=copy.deepcopy(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_ab'))
    final_try=next(n for n in run.body if isinstance(n,ast.Try) and n.finalbody)
    original_finalizer=ast.dump(ast.Module(body=copy.deepcopy(final_try.finalbody),type_ignores=[]))
    assert isinstance(final_try.body[0],ast.For)
    measure=final_try.body[0]
    assert ast.literal_eval(measure.iter)==('A','B')
    measure.iter=ast.Tuple(elts=[ast.Constant(value='B')],ctx=ast.Load())
    # Keep the exact B measurement and cleanup code; replace the A/B ratio.
    final_try.body=[measure]+ast.parse("""
b=report['variants']['B']
report['source_coverage_comparable']=False
report['retry_target_met']=b['stage_targets_met']
report['passed']=b['stage_targets_met']
report['conclusion']='B_600S_TARGET_MET_NOT_30MIN_OR_FORMAL_IDENTITY' if report['passed'] else 'B_600S_TARGET_NOT_MET_OR_COVERAGE_INSUFFICIENT'
""").body
    assignment=next(n for n in run.body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='report' for t in n.targets))
    index=run.body.index(assignment)+1
    run.body[index:index]=ast.parse("""
report['scope']='B_ONLY_600S_STABILITY_AFTER_SUCCESSFUL_SHORT_WINDOW'
report['orchestration_wrapper_sha256']=WRAPPER_SHA
report['a_reference_report']=A_REFERENCE
""").body
    assert ast.dump(ast.Module(body=final_try.finalbody,type_ignores=[]))==original_finalizer
    # A single no-face snapshot is a data gate, not a device protection.
    # Wait at most 30 seconds here; retain the post-start face wait and all
    # per-window coverage flags. Native budgets and finalizer stay identical.
    instant=next(n for n in run.body if isinstance(n,ast.Assert)
        and isinstance(n.msg,ast.Constant) and n.msg.value=='One actual face is required before A/B start')
    i=run.body.index(instant)
    run.body[i:i+1]=ast.parse("""
face_deadline=time.monotonic()+30
while face_count()!=1:
    if time.monotonic()>=face_deadline:raise RuntimeError('No face within bounded pre-start wait')
    time.sleep(.3)
""").body

    class LongObservation(ast.NodeTransformer):
        def visit_Constant(self,node):
            if type(node.value) is int:
                if node.value==13:node.value=121
                elif node.value==60:node.value=600
            return node
    # Change sample count, elapsed threshold, face coverage and crop count only
    # in the observation block. The native code and rollback are untouched.
    LongObservation().visit(measure)
    timer_calls=0
    for node in ast.walk(run):
        if isinstance(node,ast.Constant) and node.value=='--on-active=420s':
            node.value='--on-active=1200s';timer_calls+=1
        elif isinstance(node,ast.Dict):
            for key,value in zip(node.keys,node.values):
                if isinstance(key,ast.Constant) and key.value=='independent_rollback_seconds':
                    assert value.value==420;value.value=1200
    assert timer_calls==1
    assert ast.dump(ast.Module(body=final_try.finalbody,type_ignores=[]))==original_finalizer
    run.name='run_b_only';ast.fix_missing_locations(run)
    namespace=module.__dict__
    prior=json.loads((ROOT/'latest-run.json').read_text())
    namespace.update(WRAPPER_SHA=digest,A_REFERENCE=prior['report'])
    exec(compile(ast.Module(body=[run],type_ignores=[]),str(source),'exec'),namespace)
    try:
        namespace['run_b_only'](ORIGINAL,EXPECTED[:16],ROOT)
        outcome={'finished':True}
    except Exception as exc:outcome={'finished':True,'error':type(exc).__name__+': '+str(exc)[:500]}
    (ROOT/'b-long-600-launch-result.json').write_text(json.dumps(outcome,indent=2)+'\n')
else:
    assert not (ROOT/'b-long-600-launch-result.json').exists()
    prior=json.loads((ROOT/'latest-run.json').read_text())
    report=json.loads(Path(prior['report']).read_text())
    assert report['complete'] and report['rollback_verified']
    assert report['passed'] and report['variants']['B']['stage_targets_met']
    assert report['scope']=='B_ONLY_60S_AFTER_A_FACE_COVERAGE_FAILED'
    unit='aura-sface-b-600-'+digest[:16]
    result=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=900',
        '--setenv=AURA_SFACE_B_ONLY_RUN=1','/usr/bin/python3','-B',str(source)],
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10)
    assert result.returncode==0,result.stdout.decode(errors='replace')
    print(json.dumps({'started':True,'unit':unit,'scope':'B_ONLY_600S_STABILITY',
        'original_helper_sha256':EXPECTED,'wrapper_sha256':digest}),flush=True)
