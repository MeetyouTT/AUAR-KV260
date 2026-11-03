"""Seal public source hashes and synthetic local evidence, no product changes."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

here=Path(__file__).resolve().parent
release=here.parent/'actual_release/runtime'
source_names=[
 'board/runtime/board_business.py',
 'board/runtime/board_speaker_business.py',
 'board/runtime/audio/board_dialogue_jobs.py',
 'board/runtime/board_dialogue.py',
 'board/identity/voice_enrollment.py',
 'common/binding_intent.py',
 'common/feature_intents.py',
 'common/speaker_identity.py',
 'common/identity_links.py',
 'common/anonymous_voice.py',
 'common/board_memory.py',
 'tools/speaker_device.py',
 'tools/binding_hub_runtime.py',
]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
xml=ET.parse(here/'REAL_COMPOSITION_V5.xml').getroot()
suite=xml if xml.tag=='testsuite' else xml.find('testsuite')
manifest={
 'review':'actual_released_target_composition',
 'scope':'local_public_source_and_fresh_synthetic_stores_only',
 'product_files_modified':False,
 'board_operations':False,
 'uses_fake_business':False,
 'real_target_classes':['BoardDialogueJobs','BoardDialogueController','LocalIdentityReplies',
                       'BoardSpeakerBusiness','SpeakerDevice','BindingHubRuntime'],
 'original_constructor_skipped_reason':'public_snapshot_missing_unrelated_history_delete_module',
 'actual_runtime_methods':['attach_speaker_business','_submit_speaker_analysis'],
 'test_doubles':['ASR','LLM','TTS','monotonic_and_wall_time','192D_encoder','WebRTC_VAD'],
 'fresh_synthetic_store_root':'E:/aura_synthetic_composition_20261102_05',
 'cases':int(suite.attrib['tests']),
 'failures':int(suite.attrib['failures']),
 'errors':int(suite.attrib['errors']),
 'field_root_cause_proven':False,
 'field_outcome_accepted':False,
 'source_sha256':{name:sha(release/name) for name in source_names},
 'evidence_sha256':{name:sha(here/name) for name in [
   'test_real_composition.py','REAL_COMPOSITION_V5.xml','REVIEW.txt','ALIAS_TEST_SUGGESTIONS.txt']},
}
assert manifest['cases']==11 and manifest['failures']==manifest['errors']==0
(here/'REVIEW_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:manifest[k] for k in ('cases','failures','errors','field_root_cause_proven','product_files_modified')},ensure_ascii=False))
