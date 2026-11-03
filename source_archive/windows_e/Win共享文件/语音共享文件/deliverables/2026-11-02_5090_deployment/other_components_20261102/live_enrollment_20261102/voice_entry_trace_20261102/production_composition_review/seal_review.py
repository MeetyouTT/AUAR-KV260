"""Check local evidence/source immutability and seal the synthetic regression."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
LIVE=HERE.parent.parent
BASE=LIVE/'split_commands_20261102/actual_release/runtime'
DEST=HERE/'runtime'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def paths(root):return {
 p.relative_to(root).as_posix():sha(p) for p in root.rglob('*')
 if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}

overlay=json.loads((HERE/'OVERLAY_MANIFEST.json').read_text(encoding='utf-8'))
assert paths(BASE)==overlay['original_release_sha256']
assert paths(DEST)==overlay['overlay_sha256']
assert sha(HERE/'test_real_composition.py')==overlay['overlay_test_sha256']
for name,row in overlay['overlay_changed_files'].items():
 assert sha(HERE.parent/'candidate'/name)==row['after_sha256']
xml=ET.parse(HERE/'TRACE_REAL_COMPOSITION.xml').getroot()
suite=xml if xml.tag=='testsuite' else xml.find('testsuite')
counts={k:int(suite.attrib[k]) for k in ('tests','failures','errors','skipped')}
assert counts==dict(tests=11,failures=0,errors=0,skipped=0)
result=dict(status='LOCAL_SYNTHETIC_OVERLAY_NO_REGRESSION_OBSERVED',
 **counts,baseline_same_cases_passed=11,
 source_snapshot_files_checked=len(overlay['original_release_sha256']),
 changed_files=overlay['overlay_changed_files'],original_release_unchanged=True,
 candidate_payload_unchanged=True,board_accessed=False,product_deployed=False,
 actual_runtime_constructor_tested=False,actual_target_components_tested=True,
 actual_board_model_or_identity_data_tested=False,live_root_cause_proven=False,
 evidence_sha256={name:sha(HERE/name) for name in (
  'test_real_composition.py','TRACE_REAL_COMPOSITION.xml','REVIEW.txt','OVERLAY_MANIFEST.json',
  'prepare_overlay.py')})
(HERE/'SEALED_REVIEW.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:result[k] for k in ('status','tests','failures','errors','original_release_unchanged','candidate_payload_unchanged')}))
