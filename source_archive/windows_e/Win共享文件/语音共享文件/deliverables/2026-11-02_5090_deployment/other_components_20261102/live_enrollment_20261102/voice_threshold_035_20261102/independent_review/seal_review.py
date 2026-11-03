"""Hash immutable root candidate and completed independent synthetic tests."""
import ast,hashlib,json
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
manifest=json.loads((ROOT/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
sources={name:sha(ROOT/'candidate_runtime'/name) for name in manifest['files']}
assert sources=={name:row['after_sha256'] for name,row in manifest['files'].items()}
def files(root):return {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
before,after=files(ROOT/'baseline_runtime'),files(ROOT/'candidate_runtime')
assert before.keys()==after.keys()
assert {n for n in before if before[n]!=after[n]}==sources.keys()
xml=ET.parse(HERE/'THRESHOLD035_INDEPENDENT_FINAL.xml').getroot()
suite=xml if xml.tag=='testsuite' else xml.find('testsuite')
counts={k:int(suite.attrib[k]) for k in ('tests','failures','errors','skipped')}
assert counts==dict(tests=18,failures=0,errors=0,skipped=0)
provisional_before=ast.parse((ROOT/'baseline_runtime/tools/provisional_voice.py').read_text(encoding='utf-8'))
provisional_after=ast.parse((ROOT/'candidate_runtime/tools/provisional_voice.py').read_text(encoding='utf-8'))
nodes=[node for node in ast.walk(provisional_after) if isinstance(node,ast.Constant) and type(node.value) is float and node.value==.35]
assert len(nodes)==1;nodes[0].value=.8
assert ast.dump(provisional_before,include_attributes=False)==ast.dump(provisional_after,include_attributes=False)
verdict=dict(status='INDEPENDENT_LOCAL_REVIEW_PASS_NO_BLOCKER',reviewed_sources=sources,
 tests=dict(total=18,passed=18,failed=0,errors=0),
 selected_GUI='CandidateGuiBoardBusiness._attach_speaker',actual_GUI_to_Device_Store_threshold=.35,
 public_values=dict(identity_match_threshold=.35,identity_ambiguity_margin=.1,enrollment_consistency=.6),
 field_calibrated=False,anonymous_threshold_default=.9,anonymous_floor=.8,
 actual_full_recording_stream_ACK_rearm_tested_with_synthetic_score=.5,
 duplicate_enrollment_shared_threshold_effect_tested=True,
 changed_public_source_files=len(sources),other_public_sources_byte_identical=True,
 provisional_only_floor_literal_changed=True,
 product_modified_by_reviewer=False,board_or_network_accessed=False,real_voice_or_database_accessed=False,
 real_model_initialized=False,field_accuracy_accepted=False,
 evidence_sha256={n:sha(HERE/n) for n in ('REVIEW.txt','test_threshold035.py','base_composition.py',
  'recording_helpers.py','THRESHOLD035_INDEPENDENT_FINAL.xml','LOADED_SOURCE_PINS.json')})
(HERE/'REVIEW_VERDICT.json').write_text(json.dumps(verdict,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=verdict['status'],passed=18,actual_GUI_to_Device_Store_threshold=.35,product_modified=False)))
