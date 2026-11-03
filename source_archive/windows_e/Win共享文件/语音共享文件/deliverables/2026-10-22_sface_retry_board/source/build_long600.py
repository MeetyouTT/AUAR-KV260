"""Extend only observation/orchestration, preserving pinned B inference sources."""
import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
old=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_sface_b_only_20261022_v2.py')
assert hashlib.sha256(old.read_bytes()).hexdigest()=='a9dfd6aff4f15cf67a69b19ae9b328262de2ec2a1644d764f54e21b7c9ef13a4'
s=old.read_text()
marker="    run.name='run_b_only';ast.fix_missing_locations(run)"
assert s.count(marker)==1
code=r'''
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
'''+marker
s=s.replace(marker,code)
s=s.replace('b-only-v2-launch-result.json','b-long-600-launch-result.json')
s=s.replace("report['scope']='B_ONLY_60S_AFTER_A_FACE_COVERAGE_FAILED'",
    "report['scope']='B_ONLY_600S_STABILITY_AFTER_SUCCESSFUL_SHORT_WINDOW'")
s=s.replace('B_ONLY_TARGET_MET_NO_VALID_AB_RATIO','B_600S_TARGET_MET_NOT_30MIN_OR_FORMAL_IDENTITY')
s=s.replace('B_ONLY_TARGET_NOT_MET_OR_COVERAGE_INSUFFICIENT','B_600S_TARGET_NOT_MET_OR_COVERAGE_INSUFFICIENT')
s=s.replace("assert report.get('error')=='RuntimeError: Insufficient eligible face coverage in A'",
    "assert report['passed'] and report['variants']['B']['stage_targets_met']\n    assert report['scope']=='B_ONLY_60S_AFTER_A_FACE_COVERAGE_FAILED'")
s=s.replace("unit='aura-sface-b-only-'+digest[:16]","unit='aura-sface-b-600-'+digest[:16]")
s=s.replace('--property=RuntimeMaxSec=270','--property=RuntimeMaxSec=900')
s=s.replace("'scope':'B_ONLY_NOT_VALID_PAIRED_COMPARISON'","'scope':'B_ONLY_600S_STABILITY'")
ast.parse(s)
target=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_sface_b_long600_20261022.py')
if target.exists():assert target.read_text()==s
else:target.write_text(s)
v={'path':str(target),'sha256':hashlib.sha256(s.encode()).hexdigest(),
    'observation_seconds':600,'samples':121,'sample_period_seconds':5,
    'same_b_native_sources':True,'same_budget_and_guard':True,
    'same_finalizer_ast':True,'runtime_max_seconds':900,'independent_timer_seconds':1200}
(ROOT/'long600-manifest.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(v))
