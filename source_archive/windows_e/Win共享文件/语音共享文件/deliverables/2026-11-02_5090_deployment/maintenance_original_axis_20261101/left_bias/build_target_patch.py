"""Add one optional stop target to the original entry, retaining its default."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
original=HERE.parent.parent/'axis_follow_restore/original_sources/9ebf21a1bcbc__run_face_motion.py'
before=original.read_bytes()
assert hashlib.sha256(before).hexdigest()=='9ebf21a1bcbc37992398e8d59f459141d7cc49163dcf400e768ea129f4e8be94'
text=before.decode('utf-8')
changes={
    "p.add_argument('--duration',type=float,default=0.)":
        "p.add_argument('--duration',type=float,default=0.)\n    p.add_argument('--target-center-ratio',type=float,default=.5)",
    'target_center_ratio=.5,center_tolerance_ratio=.03)':
        'target_center_ratio=a.target_center_ratio,center_tolerance_ratio=.03)',
}
for old,new in changes.items():
    assert text.count(old)==1
    text=text.replace(old,new)
after=text.encode('utf-8')
old_tree=ast.parse(before);new_tree=ast.parse(after)
old_main=next(n for n in old_tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
new_main=next(n for n in new_tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
assert len(new_main.body)==len(old_main.body)+1
call=next(n for n in ast.walk(new_main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='EdgeConfig')
target=next(k.value for k in call.keywords if k.arg=='target_center_ratio')
assert ast.dump(target)=='Attribute(value=Name(id=\'a\', ctx=Load()), attr=\'target_center_ratio\', ctx=Load())'
for k in call.keywords:
    if k.arg=='target_center_ratio':k.value=ast.Constant(value=.5)
new_main.body=[n for n in new_main.body if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and any(isinstance(a,ast.Constant) and a.value=='--target-center-ratio' for a in n.value.args))]
assert ast.dump(new_tree,include_attributes=False)==ast.dump(old_tree,include_attributes=False)
path=HERE/'run_face_motion.py';assert not path.exists();path.write_bytes(after)
receipt={'original_sha256':hashlib.sha256(before).hexdigest(),'candidate_sha256':hashlib.sha256(after).hexdigest(),
    'candidate_bytes':len(after),'semantic_changes':['optional --target-center-ratio, default 0.5','pass selected target to existing EdgeConfig'],
    'all_other_ast_nodes_unchanged':True,'white_line_and_zone_settings_changed':False}
(HERE/'PATCH_REVIEW.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt))
