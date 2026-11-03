import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPAIR=HERE.parent
PROJECT=REPAIR.parents[3]

if __name__=='__main__':
    old_path=REPAIR.parent/'listening_entry_fix/actual_automatic-listening-v7-scoped-audio-check.json'
    old=json.loads(old_path.read_text(encoding='utf-8'))
    assert old['startup_sha256']=='6301d969e2e0bef9c5337f0e36ea7545cd46c59c4b2e8d9d8ce729797ebc2edf'
    baseline=json.loads((REPAIR/'source_baseline.json').read_text(encoding='utf-8'))
    sources={}
    for rel in ('tools/production_memory_presentation.py','tools/realtime_controller.py'):
        before=(HERE/'before'/rel).read_bytes()
        before_pin=hashlib.sha256(before).hexdigest()
        assert before_pin==baseline['sources'][rel]['sha256']
        source=HERE/'after'/rel;raw=source.read_bytes();ast.parse(raw,feature_version=(3,9))
        sources[rel]=dict(source=source.relative_to(PROJECT).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),before_sha256=before_pin)
    result=dict(stage='automatic-listening-v8-ui-budget',before_startup_sha256=old['startup_sha256'],
        before_manifest_sha256=old['source_manifest_sha256'],sources=sources,
        business_options=old['business_options'],gui_options=dict(voice_barge_in=False),
        wake_word_required=False,conversation_mode='half_duplex',queue_frames=8,
        model_or_threshold_changes=False,source_only=True,private_data_replayed=False)
    (HERE/'revision.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
