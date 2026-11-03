"""Adapt only an old mock to the existing native social-cache API."""
import ast,hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura'
source=(A/'tests/framework/test_channel_jobs.py').read_text(encoding='utf-8')
old="def cache(config,root):calls.append(config['port']);return {'thinking':{'path':'fixture'}}"
new="def cache(config,root,*,social=False):\n        if social:return {}\n        calls.append(config['port']);return {'thinking':{'path':'fixture'}}"
assert source.count(old)==1;adapted=source.replace(old,new)
assertions=lambda text:[ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(text)) if isinstance(n,ast.Assert)]
assert assertions(source)==assertions(adapted)
def function(path):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    return next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='prepare_feedback')
assert ast.dump(function(H/'board_source/board/runtime/audio/channel_jobs.py'),include_attributes=False)==ast.dump(function(H/'candidate/board/runtime/audio/channel_jobs.py'),include_attributes=False)
(H/'test_native_channel_jobs.py').write_text(adapted,encoding='utf-8')
v=dict(status='PASS',original_assertions_unchanged=True,assertions=len(assertions(source)),
 production_prepare_feedback_unchanged=True,scope='Only add social keyword to test cache fake; return empty social fixture',
 original_sha256=hashlib.sha256(source.encode()).hexdigest(),adapted_sha256=hashlib.sha256(adapted.encode()).hexdigest())
(H/'fixture_adaptation.json').write_text(json.dumps(v,indent=2),encoding='utf-8');print(json.dumps(v))
