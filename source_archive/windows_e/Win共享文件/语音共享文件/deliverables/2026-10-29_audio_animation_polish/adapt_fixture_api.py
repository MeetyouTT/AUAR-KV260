"""Add a native appsrc property to the fake, preserving every assertion."""
import ast,hashlib,json
from pathlib import Path
H=Path(__file__).resolve().parent
path=H/'effective_tests/tests/framework/test_persistent_audio.py'
before=path.read_text(encoding='utf-8')
needle="source=SimpleNamespace(emit=lambda name,buffer:self.pushes.append(buffer) or 1)"
assert before.count(needle)==1
after=before.replace(needle,"source=SimpleNamespace(emit=lambda name,buffer:self.pushes.append(buffer) or 1,\n                get_property=lambda name:0)")
def assertions(source):
 return [ast.dump(node) for node in ast.walk(ast.parse(source)) if isinstance(node,ast.Assert) or isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr.startswith('assert')]
assert assertions(before)==assertions(after)
path.write_text(after,encoding='utf-8')
(H/'fixture_adaptation.json').write_text(json.dumps({'file':str(path.relative_to(H)),
 'original_sha256':hashlib.sha256(before.encode()).hexdigest(),'adapted_sha256':hashlib.sha256(after.encode()).hexdigest(),
 'only_fake_change':'appsrc.get_property(current-level-bytes) returns 0 for ideal drained fake',
 'all_assertions_ast_identical':True,'production_backpressure_guard_unchanged':True},indent=2),encoding='utf-8')
print('Fake native queue API added; all assertions unchanged')
