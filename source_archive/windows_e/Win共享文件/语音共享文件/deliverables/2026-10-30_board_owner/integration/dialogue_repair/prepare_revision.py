import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]

if __name__=='__main__':
    baseline=json.loads((HERE/'source_baseline.json').read_text(encoding='utf-8'))
    old=json.loads((HERE.parent/'direct_speech_entry/revision.json').read_text(encoding='utf-8'))
    sources={}
    for rel,folder in (
        ('tools/production_listening.py','after'),('tools/voice_first_recording.py','after'),
        ('tools/board_recording.py','instrumentation_candidate/after'),
        ('board/runtime/audio/board_dialogue_jobs.py','instrumentation_candidate/after')):
        path=HERE/folder/rel;raw=path.read_bytes();ast.parse(raw,feature_version=(3,9))
        before=(HERE/'before'/rel).read_bytes()
        assert hashlib.sha256(before).hexdigest()==baseline['sources'][rel]['sha256']
        sources[rel]=dict(source=path.relative_to(PROJECT).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),
                          before_sha256=baseline['sources'][rel]['sha256'])
    result=dict(stage='automatic-listening-v5-half-duplex',before_startup_sha256=baseline['startup_sha256'],
        before_manifest_sha256=baseline['source_manifest_sha256'],sources=sources,
        business_options=old['business_options'],gui_options=dict(voice_barge_in=False),
        wake_word_required=False,conversation_mode='half_duplex',queue_frames=8,
        model_or_threshold_changes=False,source_only=True,private_data_replayed=False)
    (HERE/'revision.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
