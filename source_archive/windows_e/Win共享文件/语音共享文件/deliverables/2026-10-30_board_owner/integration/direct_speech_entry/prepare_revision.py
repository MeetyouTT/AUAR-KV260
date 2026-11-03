"""Freeze the three source-only changes against freshly read formal pins."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]

if __name__=='__main__':
    before=json.loads((HERE/'baseline.json').read_text(encoding='utf-8'))
    previous=json.loads((HERE.parent/'response_latency/revision_v2.json').read_text(encoding='utf-8'))
    sources={}
    for name in ('voice_first_recording.py','production_listening.py','production_business_ui.py'):
        rel='tools/'+name;path=HERE/'after'/rel;raw=path.read_bytes()
        ast.parse(raw,feature_version=(3,9))
        original=(HERE/'before'/rel).read_bytes()
        assert hashlib.sha256(original).hexdigest()==before['sources'][rel]['sha256']
        sources[rel]=dict(source=path.relative_to(PROJECT).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),
                          before_sha256=before['sources'][rel]['sha256'])
    value=dict(stage='automatic-listening-v4-direct-speech',
        before_startup_sha256=before['startup_sha256'],before_manifest_sha256=before['source_manifest_sha256'],
        business_options=previous['business_options'],wake_word_required=False,sources=sources,
        source_only=True,queue_frames=8,model_or_threshold_changes=False,private_data_replayed=False)
    (HERE/'revision.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value))
