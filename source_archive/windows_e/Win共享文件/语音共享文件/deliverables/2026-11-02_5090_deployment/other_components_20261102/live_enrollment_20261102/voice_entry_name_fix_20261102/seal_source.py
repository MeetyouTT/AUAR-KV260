"""Seal exactly three local candidate files and verify preserved public components."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE/'baseline_runtime'
CAND=HERE/'candidate_runtime'
EXPECTED={
 'common/feature_intents.py':('1bb807ed88a84515942cca7e0dadab92dac99e2fd39b163b2e5d20a0194d8945',
  '2ad13c7a5a175a85dfb412182fca44a79229962ff742b18691a7b72ea75f15f2'),
 'board/runtime/board_business.py':('d034227118063dc4dbfb69f4bc735000980bd166e91262b4953f0db4b1baf5cc',
  'bf185a86dfd1f94924759c194b0246b51e64cb0a09654c935e8e1310f7bbea51'),
 'tools/yuki_jobs_candidate.py':('18d4bcbc6d3a32b3a2edd64103d634493e2fbd00f88ab0809fa600144d26508d',
  'd7bade70cf15cd5c7dd9bb17be702f86c5f2d1a32ad5c5809dddffde7a71d200'),
}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def files(root):return {
 p.relative_to(root).as_posix():sha(p) for p in root.rglob('*')
 if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
before,after=files(BASE),files(CAND)
assert before.keys()==after.keys()
changed={name for name in before if before[name]!=after[name]}
assert changed==EXPECTED.keys()
assert all((before[name],after[name])==pins for name,pins in EXPECTED.items())
business_before=ast.parse((BASE/'board/runtime/board_business.py').read_text(encoding='utf-8'))
business_after=ast.parse((CAND/'board/runtime/board_business.py').read_text(encoding='utf-8'))
def classes(tree):return {n.name:n for n in tree.body if isinstance(n,ast.ClassDef)}
def dump(n):return ast.dump(n,include_attributes=False)
assert dump(classes(business_before)['BoardBusinessRuntime'])==dump(classes(business_after)['BoardBusinessRuntime'])
old_lir,new_lir=(classes(tree)['LocalIdentityReplies'] for tree in (business_before,business_after))
old_methods={n.name:dump(n) for n in old_lir.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
new_methods={n.name:dump(n) for n in new_lir.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
assert {k for k in old_methods if old_methods[k]!=new_methods[k]}=={'__call__'}
yuki_before=ast.parse((BASE/'tools/yuki_jobs_candidate.py').read_text(encoding='utf-8'))
yuki_after=ast.parse((CAND/'tools/yuki_jobs_candidate.py').read_text(encoding='utf-8'))
tuples=[n for n in ast.walk(yuki_before) if isinstance(n,ast.Tuple)
 and tuple(e.value if isinstance(e,ast.Constant) else None for e in n.elts)==('remember_self','name_hint','invalid_name')]
assert len(tuples)==2
tuples[0].elts.extend([ast.Constant(value='face_only'),ast.Constant(value='voice_only')])
tuples[1].elts.append(ast.Constant(value='face_only'))
assert dump(yuki_before)==dump(yuki_after),'Yuki changes must be exactly two existing kind tuples'
pair_path=HERE/'yuki_pair.formal.public.json'
assert sha(pair_path)=='998710fc12bf442d6baea501bab0234665b666caa29f4be8f685741d50d82099'
pair=json.loads(pair_path.read_text(encoding='utf-8'))
assert len(pair['runtime_pins'])==10 and not set(pair['runtime_pins']).intersection(changed)
diff=''.join(''.join(difflib.unified_diff(
 (BASE/name).read_text(encoding='utf-8').splitlines(keepends=True),
 (CAND/name).read_text(encoding='utf-8').splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name))
 for name in EXPECTED)
(HERE/'CANDIDATE.diff').write_text(diff,encoding='utf-8')
manifest=dict(status='LOCAL_THREE_FILE_CANDIDATE',board_accessed=False,source_files_checked=len(before),
 candidate_directory=str(CAND),files={name:dict(before_sha256=pins[0],after_sha256=pins[1],
 before_bytes=(BASE/name).stat().st_size,after_bytes=(CAND/name).stat().st_size) for name,pins in EXPECTED.items()},
 unchanged_all_other_files=True,entire_BoardBusinessRuntime_AST_unchanged=True,
 LIR_changed_methods=['__call__'],Yuki_changes='exactly two existing intent kind tuples',
 formal_pair_sha256=sha(pair_path),formal_pair_runtime_pins=10,
 formal_pair_pins_include_changed_files=False,formal_pair_chain_update_required=False,
 diff_sha256=sha(HERE/'CANDIDATE.diff'),
 preserved_sha256={name:after[name] for name in (
 'common/binding_intent.py','board/runtime/audio/board_dialogue_jobs.py',
 'board/identity/voice_enrollment.py','board/runtime/board_speaker_business.py',
 'tools/binding_hub_runtime.py','tools/speaker_device.py','tools/formal_yuki.py')})
(HERE/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(changed=sorted(changed),AST_preserved=True,formal_pair_chain_update_required=False)))
