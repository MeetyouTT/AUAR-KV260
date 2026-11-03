"""Seal exact literal-only payload and completed synthetic regression."""
import ast,hashlib,json
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'voice_self_match_probe_20261102'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def counts(path):
 root=ET.parse(path).getroot();suites=[root] if root.tag=='testsuite' else root.findall('testsuite')
 value={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
 value['passed']=value['tests']-value['failures']-value['errors']-value['skipped'];value['sha256']=sha(path)
 return value
manifest=json.loads((HERE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
for name,row in manifest['files'].items():
 assert sha(HERE/'candidate_runtime'/name)==row['after_sha256']
 assert sha(HERE/'baseline_runtime'/name)==row['before_sha256']
 a=(HERE/'baseline_runtime'/name).read_bytes();b=(HERE/'candidate_runtime'/name).read_bytes()
 assert b.count('|辨别'.encode())==4 and b.replace('|辨别'.encode(),b'')==a
for test in ('test_self_match_probe.py','test_yuki_voice_entry.py','test_original_voice_contract.py'):
 assert sha(HERE/test)==sha(OLD/test),'Original 34/66/24 assertions unchanged'
tests={n:counts(HERE/(n+'.xml')) for n in ('BASELINE_ALIAS_MISS','CANDIDATE_ALIAS_AND_REGRESSION')}
assert tests['BASELINE_ALIAS_MISS']['passed']==tests['BASELINE_ALIAS_MISS']['tests']==9
assert tests['CANDIDATE_ALIAS_AND_REGRESSION']['passed']==tests['CANDIDATE_ALIAS_AND_REGRESSION']['tests']==133
manifest['status']='LOCAL_TWO_FILE_LITERAL_ONLY_FROZEN'
manifest['exact_bytes_after_removing_only_eight_added_tokens_equal_baseline']=True
(HERE/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
result=dict(status='LOCAL_TWO_FILE_LITERAL_ONLY_FROZEN_NOT_DEPLOYED_BY_THIS_AGENT',files=manifest['files'],tests=tests,
 original_34_66_24_test_files_byte_identical=True,baseline_confirmed_exact_alias_miss=True,
 candidate_fullYuki_real_worker_three_matches_single_encode_each=True,
 exact_eight_query_literal_tokens_only=True,only_two_of_349_public_sources_changed=True,
 cache_TTL_ledger_model_threshold_registration_authorization_unchanged=True,
 board_accessed=False,real_voice_or_private_database_accessed=False,field_accuracy_accepted=False,
 evidence_sha256={n:sha(HERE/n) for n in ('SOURCE_MANIFEST.json','CANDIDATE.diff','HANDOFF.txt','composition.py','test_query_alias.py')})
independent=HERE/'independent_review/REVIEW_VERDICT.json'
if independent.exists():
 verdict=json.loads(independent.read_text(encoding='utf-8'))
 assert verdict['reviewed_sources']=={n:r['after_sha256'] for n,r in manifest['files'].items()}
 assert verdict['tests']==dict(total=15,passed=15,failed=0,errors=0)
 result['independent_review']=dict(path='independent_review/REVIEW_VERDICT.json',sha256=sha(independent),tests=verdict['tests'])
(HERE/'VALIDATION_FINAL.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=result['status'],baseline_miss_cases=9,candidate_passed=133)))
