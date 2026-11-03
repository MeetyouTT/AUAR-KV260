"""Hash and index only public source files used in the read-only audit."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
RUNTIME=HERE.parent/'voice_entry_name_fix_20261102/candidate_runtime'
AURA=HERE.parents[3]/'aura'
if not AURA.is_dir():AURA=Path('E:/Win共享文件/语音共享文件/aura')
FILES={
 'released_public_basis':(RUNTIME,[
  'board/runtime/board_speaker_business.py','board/runtime/audio/board_speaker_onnx.py',
  'tools/board_business_gui.py','tools/speaker_device.py','common/speaker_identity.py',
  'common/speaker_validation.py','tools/progressive_speaker.py','tools/provisional_voice.py',
  'common/identity_links.py','common/speaker_turns.py','tools/identity_resolution.py']),
 'auxiliary_original_checkout':(AURA,[
  'tools/score_speaker_dataset.py','tools/calibrate_speaker_scores.py','tools/speaker_identity.py',
  'tools/verify_speaker_model.py','tools/benchmark_speaker_lengths.py','tools/board_speaker_sampler.py',
  'config/speaker_identity.local.json','tests/framework/test_speaker_identity.py',
  'tests/framework/test_board_speaker_business.py','tests/framework/test_speaker_vad_live.py',
  'common/speaker_identity.py','common/speaker_validation.py'])}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sources={}
for group,(root,names) in FILES.items():
 sources[group]={}
 for name in names:
  path=root/name
  row=dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size)
  if path.suffix=='.py':
   tree=ast.parse(path.read_text(encoding='utf-8'))
   row['definitions']={n.name:n.lineno for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
  sources[group][name]=row
assert sources['released_public_basis']['board/runtime/board_speaker_business.py']['sha256']=='6904267bd016a10a1508b26f372f0db54a71d78eed2eb15b043026218b1b7816'
assert sources['released_public_basis']['tools/speaker_device.py']['sha256']=='da9c199527abdf9e247661d8798f4345cf0b79524f5c2a06394b5dc9c44107de'
for name in ('common/speaker_identity.py','common/speaker_validation.py'):
 assert sources['released_public_basis'][name]['sha256']==sources['auxiliary_original_checkout'][name]['sha256']
audit=dict(status='LOCAL_READONLY_SOURCE_AUDIT_ONLY',sources=sources,
 model_called=False,real_pcm_or_identity_data_accessed=False,board_accessed=False,
 tests_executed=False,production_or_candidate_modified=False,
 field_registration_success='root_reported_not_rechecked_by_this_agent',
 field_accuracy_or_calibration_accepted=False,
 production_calibration_activation_exists=False,
 offline_score_and_candidate_calibration_tools_exist=True,
 direct_unlinked_uncalibrated_named_production_query_exists=False,
 audit_text_sha256=sha(HERE/'AUDIT.txt'))
(HERE/'SOURCE_AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=audit['status'],public_files=sum(map(len,sources.values())),board_accessed=False,tests_executed=False)))
