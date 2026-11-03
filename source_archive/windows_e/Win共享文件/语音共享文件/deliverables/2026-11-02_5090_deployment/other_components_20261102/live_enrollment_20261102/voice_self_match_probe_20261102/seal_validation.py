"""Freeze final public payload and local synthetic evidence only."""
import hashlib,json
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def counts(path):
 root=ET.parse(path).getroot();suites=[root] if root.tag=='testsuite' else root.findall('testsuite')
 value={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
 value['passed']=value['tests']-value['failures']-value['errors']-value['skipped'];value['sha256']=sha(path)
 return value
source=json.loads((HERE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
name='board/runtime/board_speaker_business.py'
assert sha(HERE/'candidate_runtime'/name)==source['files'][name]['after_sha256']=='f82bc71d00c355c164d43ca0b6a853ea6a32e67c84ffd228791d7070209b907e'
assert sha(HERE/'baseline_runtime'/name)==source['files'][name]['before_sha256']
tests={n:counts(HERE/(n+'.xml')) for n in ('SELF_MATCH_FINAL_F82','ORIGINAL_66_24_FINAL_F82')}
assert tests['SELF_MATCH_FINAL_F82']['passed']==tests['SELF_MATCH_FINAL_F82']['tests']==34
assert tests['ORIGINAL_66_24_FINAL_F82']['passed']==tests['ORIGINAL_66_24_FINAL_F82']['tests']==90
old=HERE.parent/'voice_entry_name_fix_20261102'
for test in ('test_yuki_voice_entry.py','test_original_voice_contract.py'):
 assert sha(HERE/test)==sha(old/test),'Old 66/24 assertions must stay unchanged'
result=dict(status='LOCAL_SINGLE_FILE_FROZEN_NOT_DEPLOYED_BY_THIS_AGENT',files=source['files'],
 source_files_checked=source['source_files_checked'],only_one_public_source_changed=True,tests=tests,
 board_accessed=False,actual_model_or_private_data_accessed=False,
 actual_formal_pair_yuki_worker_matcher_used=True,full_Runtime_init_tested=False,
 field_calibrated=False,identity_authorization_granted=False,links_created=False,
 scope='single_person_matching_probe_only_no_cross_modal_linking',
 current_candidate_TTL_seconds=2,candidate_completed_is_historical_not_current_or_playback_proof=True,
 evidence_sha256={n:sha(HERE/n) for n in ('SOURCE_MANIFEST.json','CANDIDATE.diff','HANDOFF.txt','composition.py',
  'test_self_match_probe.py','test_yuki_voice_entry.py','test_original_voice_contract.py')})
independent=HERE/'independent_review/REVIEW_VERDICT.json'
if independent.exists():
 verdict=json.loads(independent.read_text(encoding='utf-8'))
 assert verdict['candidate_sha256']==source['files'][name]['after_sha256']
 assert verdict['tests']==dict(total=15,passed=15,failed=0,errors=0)
 result['independent_review']=dict(path='independent_review/REVIEW_VERDICT.json',sha256=sha(independent),verdict=verdict)
(HERE/'VALIDATION_FINAL.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=result['status'],probe_passed=34,regression_passed=90,board_accessed=False)))
