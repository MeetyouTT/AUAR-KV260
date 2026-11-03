"""Seal the single changed public worker source as a reviewable local draft."""
import ast,difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files(root):return {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
base=HERE/'baseline_runtime';candidate=HERE/'candidate_runtime'
a,b=files(base),files(candidate)
changed={name for name in a if a[name]!=b[name]}
name='board/runtime/board_speaker_business.py'
assert a.keys()==b.keys() and changed=={name}
assert a[name]=='6904267bd016a10a1508b26f372f0db54a71d78eed2eb15b043026218b1b7816'
assert b[name]=='f82bc71d00c355c164d43ca0b6a853ea6a32e67c84ffd228791d7070209b907e'
def methods(path):
 tree=ast.parse(path.read_text(encoding='utf-8'))
 cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BoardSpeakerBusiness')
 return {n.name:ast.dump(n,include_attributes=False) for n in cls.body if isinstance(n,ast.FunctionDef)}
old,new=methods(base/name),methods(candidate/name)
expected={'__init__','_refresh_public','public','_call','turn','_cancel_actor','reset','health'}
assert {n for n in old if old[n]!=new[n]}==expected
diff=''.join(difflib.unified_diff((base/name).read_text(encoding='utf-8').splitlines(keepends=True),
 (candidate/name).read_text(encoding='utf-8').splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name))
(HERE/'CANDIDATE.diff').write_text(diff,encoding='utf-8')
manifest=dict(status='LOCAL_SINGLE_FILE_FROZEN',board_accessed=False,source_files_checked=len(a),
 files={name:dict(before_sha256=a[name],after_sha256=b[name],before_bytes=(base/name).stat().st_size,after_bytes=(candidate/name).stat().st_size)},
 all_other_public_source_files_unchanged=True,changed_original_methods=sorted(expected),
 original_submit_run_initialize_quality_guard_AST_unchanged=True,
 diff_sha256=sha(HERE/'CANDIDATE.diff'))
(HERE/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(manifest['files']))
