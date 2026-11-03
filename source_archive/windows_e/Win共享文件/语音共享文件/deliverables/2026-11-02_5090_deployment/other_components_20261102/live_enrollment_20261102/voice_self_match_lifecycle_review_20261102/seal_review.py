"""Seal immutable public sources and synthetic integration evidence."""
import hashlib,json
from pathlib import Path
import xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'voice_self_match_query_alias_20261102'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files(root):return {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
base=files(OLD/'candidate_runtime');integrated=files(HERE/'integration_runtime')
extra={
 'tools/board_recording.py':'e70a9f4ca4768b3a1fabfc33145e39edbcb8cf20e0c76f269cc0b032fb54ce26',
 'tools/production_memory_presentation.py':'de04c6cd22e3672ff17c2cfb71f5539f6908c98daf74e8d94d154c8fd280d4c2',
 'board/runtime/history_delete.py':'647b5cf85ad5595305067bcced2b118f83e89ca79ba45b7ad91090fd9515023f'}
assert all(integrated[n]==pin for n,pin in base.items())
assert set(integrated)-set(base)==set(extra)
assert all(integrated[n]==pin for n,pin in extra.items())
xml=ET.parse(HERE/'RECORDING_INTEGRATION_FINAL.xml').getroot()
suite=xml if xml.tag=='testsuite' else xml.find('testsuite')
counts={k:int(suite.attrib[k]) for k in ('tests','failures','errors','skipped')}
assert counts==dict(tests=7,failures=0,errors=0,skipped=0)
report=dict(status='LOCAL_INTEGRATION_REVIEW_COMPLETE_NO_PRODUCT_FIX',**counts,
 full_Runtime_init_and_start_executed=True,actual_recording_streaming_ACK_components=True,
 normal_three_query_reset_count=0,normal_query_encoder_calls=3,
 synthetic_store_data_origin='synthetic',UI_production_policy_branch_adapter_used=True,
 production_bootstrap_or_GPU_tested=False,exact_live_reset_cause_proven=False,
 products_modified=False,board_accessed=False,real_audio_or_database_accessed=False,
 original_public_sources_unchanged=len(base),added_pinned_public_modules=extra,
 integration_public_source_sha256=integrated,
 evidence_sha256={n:sha(HERE/n) for n in ('REVIEW.txt','test_recording_integration.py','base_composition.py',
  'RECORDING_INTEGRATION_FINAL.xml','NORMAL_CHAIN_METADATA.json','SILENCE_RESET_METADATA.json')})
(HERE/'REVIEW_VERDICT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ('status','tests','failures','errors','normal_three_query_reset_count','products_modified')}))
