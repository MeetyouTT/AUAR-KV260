"""Only append one query synonym in eight existing regex literals."""
import ast,difflib,hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'voice_self_match_probe_20261102'
SOURCE=OLD/'candidate_runtime'
EXPECTED={
 'common/feature_intents.py':'2ad13c7a5a175a85dfb412182fca44a79229962ff742b18691a7b72ea75f15f2',
 'board/runtime/board_speaker_business.py':'f82bc71d00c355c164d43ca0b6a853ea6a32e67c84ffd228791d7070209b907e'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name,pin in EXPECTED.items():assert sha(SOURCE/name)==pin
for mode in ('baseline','candidate'):
 dest=HERE/(mode+'_runtime')
 if not dest.exists():shutil.copytree(SOURCE,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
replacements={
 'common/feature_intents.py':{
  '(?:查询|检查|识别|辨认)':'(?:查询|检查|识别|辨认|辨别)',
  '(?:识别|辨认|认出|认识)':'(?:识别|辨认|认出|认识|辨别)',
  '(?:知道|判断|识别|认出)':'(?:知道|判断|识别|认出|辨别)',
  '(?:识别|认出|辨认)':'(?:识别|认出|辨认|辨别)'},
 'board/runtime/board_speaker_business.py':{
  '(?:识别|辨认)':'(?:识别|辨认|辨别)',
  '(?:识别|辨认|认出|认识)':'(?:识别|辨认|认出|认识|辨别)',
  '(?:知道|判断|识别|认出)':'(?:知道|判断|识别|认出|辨别)',
  '(?:识别|认出|辨认)':'(?:识别|认出|辨认|辨别)'}}
class RevertSynonym(ast.NodeTransformer):
 def visit_Constant(self,node):
  if isinstance(node.value,str):node.value=node.value.replace('|辨别','')
  return node
diff='';files={}
for name,changes in replacements.items():
 before=(SOURCE/name).read_bytes().decode('utf-8');after=before
 for a,b in changes.items():
  assert after.count(a)==1,(name,a)
  after=after.replace(a,b)
 assert after.count('|辨别')==4
 assert after.encode('utf-8').replace('|辨别'.encode('utf-8'),b'')==before.encode('utf-8')
 assert ast.dump(RevertSynonym().visit(ast.parse(after)),include_attributes=False)==ast.dump(ast.parse(before),include_attributes=False)
 (HERE/'candidate_runtime'/name).write_bytes(after.encode('utf-8'))
 files[name]=dict(before_sha256=sha(SOURCE/name),after_sha256=sha(HERE/'candidate_runtime'/name),
  before_bytes=(SOURCE/name).stat().st_size,after_bytes=(HERE/'candidate_runtime'/name).stat().st_size)
 diff+=''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name))
(HERE/'CANDIDATE.diff').write_text(diff,encoding='utf-8')
def tree(root):return {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
base,candidate=tree(HERE/'baseline_runtime'),tree(HERE/'candidate_runtime')
assert base.keys()==candidate.keys() and {n for n in base if base[n]!=candidate[n]}==EXPECTED.keys()
manifest=dict(status='LOCAL_TWO_FILE_LITERAL_ONLY_CANDIDATE',board_accessed=False,
 source_files_checked=len(base),files=files,all_other_public_sources_unchanged=True,
 only_query_regex_constants_changed=True,AST_after_reverting_added_synonym_equals_baseline=True,
 registration_parser_cache_TTL_ledger_authorization_logic_unchanged=True,
 exact_bytes_after_removing_only_eight_added_tokens_equal_baseline=True,
 diff_sha256=sha(HERE/'CANDIDATE.diff'))
(HERE/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for filename in ('BASE_PINS.json','yuki_pair.formal.public.json','test_self_match_probe.py','test_yuki_voice_entry.py','test_original_voice_contract.py'):
 shutil.copyfile(OLD/filename,HERE/filename)
test=(OLD/'composition.py').read_text(encoding='utf-8')
old="PINS['board/runtime/board_speaker_business.py']=('f82bc71d00c355c164d43ca0b6a853ea6a32e67c84ffd228791d7070209b907e' if MODE=='candidate' else '6904267bd016a10a1508b26f372f0db54a71d78eed2eb15b043026218b1b7816')"
new="PINS['board/runtime/board_speaker_business.py']=('"+files['board/runtime/board_speaker_business.py']['after_sha256']+"' if MODE=='candidate' else 'f82bc71d00c355c164d43ca0b6a853ea6a32e67c84ffd228791d7070209b907e')\nPINS['common/feature_intents.py']=('"+files['common/feature_intents.py']['after_sha256']+"' if MODE=='candidate' else '2ad13c7a5a175a85dfb412182fca44a79229962ff742b18691a7b72ea75f15f2')"
assert test.count(old)==1;test=test.replace(old,new)
(HERE/'composition.py').write_text(test,encoding='utf-8')
print(json.dumps(files))
