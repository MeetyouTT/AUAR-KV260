"""Independent structural proof for the narrow preview projection. Local only."""
import ast
import copy
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
GTK=HERE.parent/'gtk/v2'
paths={
    'original_services':GTK/'original/board/interaction/ui_services.py',
    'candidate_services':GTK/'candidate/board/interaction/ui_services.py',
    'original_preview':GTK/'original/tools/board_camera_preview.py',
    'candidate_preview':GTK/'candidate/tools/board_camera_preview.py',
    'contract':GTK/'original/board/interaction/ui_contract.py'}
expected={
    'original_services':'b55ee295e2cb5494f387fbaa4aa081fd1d6bffd57588c018c5f31daae56bd711',
    'candidate_services':'e4dedf9b3d56d22d9eb93de1e96ad1a69870d553ea50f7dd5082b21e19f381c9',
    'original_preview':'6e697c16f7ae264dff56b6b35f38da4b531ea13026b69a7c8bdbfb1960a6afcd',
    'candidate_preview':'67d6c0f2b24ea97e20fdcc7b3383b6444269a6e26f5deb566f2b88746b7daf9b',
    'contract':'7f67e4bdfe4a95396fbe6445759c80f8ea79cf51d2d991269213409a83daec86'}
source={}
for label,path in paths.items():
    raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==expected[label],label
    source[label]=raw.decode()

def methods(text,name):
    klass=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name==name)
    return {n.name:n for n in klass.body if isinstance(n,ast.FunctionDef)}

before=methods(source['original_services'],'UiServiceClient')
after=methods(source['candidate_services'],'UiServiceClient')
assert set(after)-set(before)=={'read_preview'}
assert all(ast.dump(before[name])==ast.dump(after[name]) for name in before)
checks=['all existing UiServiceClient methods identical; only read_preview added']
new_method=after['read_preview']
condition=next(n for n in new_method.body if isinstance(n,ast.With))
assert ast.dump(condition.items[0].context_expr)==ast.dump(ast.parse('self.condition',mode='eval').body)
gate=methods(source['contract'],'SnapshotGate')['read']
gate_expiry=next(n for n in gate.body if isinstance(n,ast.If)).test
projection_expiry=next(n for n in condition.body if isinstance(n,ast.If)).test
assert ast.dump(gate_expiry)==ast.dump(projection_expiry)
checks.append('SnapshotGate source expiry predicate identical under original condition lock')

preview_before=methods(source['original_preview'],'CameraPreviewWorker')
preview_after=methods(source['candidate_preview'],'CameraPreviewWorker')
assert set(preview_before)==set(preview_after)
assert all(ast.dump(preview_before[name])==ast.dump(preview_after[name]) for name in preview_before if name!='work')
checks.append('Gst attach, push, stale drop, clear, lifecycle and all non-work methods unchanged')
work=copy.deepcopy(preview_after['work'])
loop=next(n for n in work.body if isinstance(n,ast.While))
body=next(n for n in loop.body if isinstance(n,ast.Try)).body
index=next(i for i,n in enumerate(body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='read_preview' for t in n.targets))
body.pop(index)
read_assign=body[index]
assert isinstance(read_assign,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='view' for t in read_assign.targets)
assert isinstance(read_assign.value,ast.IfExp)
read_assign.value=ast.parse('self.services.read()',mode='eval').body
assert ast.dump(work)==ast.dump(preview_before['work'])
checks.append('normalizing only the added read selector makes entire original worker work AST equal')

view_keys=set()
for n in ast.walk(preview_after['work']):
    if isinstance(n,ast.Subscript) and isinstance(n.value,ast.Name) and n.value.id=='view' and isinstance(n.slice,ast.Constant):view_keys.add(n.slice.value)
    if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='view' and n.func.attr=='get' and n.args and isinstance(n.args[0],ast.Constant):view_keys.add(n.args[0].value)
assert view_keys=={'snapshot','preview','raw_preview'}
checks.append('all worker view keys are exactly the three returned by new method')
checks.append('manual source review: cancellation mask changes only interaction fields; camera/preview are disjoint')
checks.append('manual source review: minimal snapshot and JPEG mutable values copied; original use_raw and 1500ms guard reused')
result={'status':'PASS_STATIC_REVIEW_NO_CODE_BLOCKERS_RUNTIME_AB_PENDING',
    'component_sha256':expected,'checks':checks,'checks_count':len(checks),
    'existing_agent_pure_test_result_reused':{'tests':11,'passed':True,'concurrent_configure_cancel_loss_iterations':350},
    'production_or_board_or_network_accessed':False,'new_load_tests_executed':False,
    'fresh_baseline_required_after_boot_change':True,
    'runtime_gain_claimed':False,
    'deployment_condition':'Verify current original component and contract SHAs and fresh startup/owners after identity handoff; preserve other new voice/axis/source pins.'}
(HERE/'GTK_PROJECTION_INDEPENDENT_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
