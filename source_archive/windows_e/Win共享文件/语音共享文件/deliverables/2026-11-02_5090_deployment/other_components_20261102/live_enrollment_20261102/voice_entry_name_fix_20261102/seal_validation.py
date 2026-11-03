"""Seal completed local synthetic evidence without altering payloads."""
import ast
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def counts(path):
 root=ET.parse(path).getroot()
 suites=[root] if root.tag=='testsuite' else root.findall('testsuite')
 result={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
 result['passed']=result['tests']-result['failures']-result['errors']-result['skipped']
 result['sha256']=sha(path)
 return result
source=json.loads((HERE/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
assert all(sha(HERE/'candidate_runtime'/n)==r['after_sha256'] for n,r in source['files'].items())
assert all(sha(HERE/'baseline_runtime'/n)==r['before_sha256'] for n,r in source['files'].items())
results={name:counts(HERE/(name+'.xml')) for name in (
 'CANDIDATE_YUKI_FINAL','BASELINE_YUKI_FINAL','ORIGINAL_VOICE_CONTRACT_FINAL')}
assert results['CANDIDATE_YUKI_FINAL']['passed']==66 and results['CANDIDATE_YUKI_FINAL']['tests']==66
assert results['BASELINE_YUKI_FINAL']['passed']==41 and results['BASELINE_YUKI_FINAL']['failures']==25
assert results['ORIGINAL_VOICE_CONTRACT_FINAL']['passed']==24
assert results['ORIGINAL_VOICE_CONTRACT_FINAL']['tests']==24
original_contract=HERE.parent/'split_commands_20261102/independent_voice_review/test_original_voice_contract.py'
original=original_contract.read_text(encoding='utf-8').replace("RUNTIME=LIVE/'start_sync_fix/candidate_runtime'","RUNTIME=HERE/'candidate_runtime'")
assert original==(HERE/'test_original_voice_contract.py').read_text(encoding='utf-8')
verdict=dict(status='LOCAL_CANDIDATE_FROZEN_NOT_DEPLOYED_BY_THIS_AGENT',
 files=source['files'],results=results,
 has_actual_instance_bound_yuki_route=True,uses_fake_business=False,
 full_Runtime_init_tested=False,real_audio_or_biometrics_tested=False,
 live_exact_transcript_root_cause_proven=False,board_accessed=False,
 unchanged_BoardBusinessRuntime_AST=True,only_three_public_files_changed=True,
 formal_pair_chain_update_required=False,formal_pair_sha256=source['formal_pair_sha256'],
 fixture_corrections_preserved_in_V1_XML=True,
 evidence_sha256={n:sha(HERE/n) for n in (
 'SOURCE_MANIFEST.json','CANDIDATE.diff','HANDOFF.txt','composition.py','test_yuki_voice_entry.py',
 'test_original_voice_contract.py','yuki_pair.formal.public.json')},
 limitations=[
  'Grammar/formatting failure class addressed; exact live text is unavailable',
  'Unrelated original SERVICE_ERROR/InterruptedError/reset causes are not claimed solved',
  'Only synthetic ASR/LLM/TTS/VAD/encoder/PCM, controlled clock and renderer readiness',
  'Real GUI/player/acoustics and final user acceptance require root-managed field observation',
  'Multiword Latin names are not guessed or concatenated; original FSM name slot remains in force'])
independent_path=HERE/'independent_review/REVIEW_VERDICT.json'
if independent_path.exists():
 independent=json.loads(independent_path.read_text(encoding='utf-8'))
 assert independent['reviewed_sources']=={n:r['after_sha256'] for n,r in source['files'].items()}
 assert independent['tests']==dict(total=43,passed=43,failed=0,errors=0)
 verdict['independent_review']=dict(path='independent_review/REVIEW_VERDICT.json',
  sha256=sha(independent_path),tests=independent['tests'],status=independent['status'])
(HERE/'VALIDATION_FINAL.json').write_text(json.dumps(verdict,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:verdict[k] for k in ('status','has_actual_instance_bound_yuki_route','board_accessed')}))
