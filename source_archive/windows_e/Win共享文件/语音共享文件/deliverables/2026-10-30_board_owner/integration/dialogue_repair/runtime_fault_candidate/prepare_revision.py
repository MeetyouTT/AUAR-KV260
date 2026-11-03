import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
PROJECT = REPAIR.parents[3]

if __name__ == '__main__':
    old = json.loads((REPAIR.parent/'listening_entry_fix/actual_automatic-listening-v8-ui-budget.json').read_text(encoding='utf-8'))
    before = json.loads((HERE/'before_manifest.json').read_text(encoding='utf-8'))
    assert old['startup_sha256'] == before['startup_sha256']
    rel = 'tools/board_avatar_gtk.py'
    assert hashlib.sha256((HERE/'before'/rel).read_bytes()).hexdigest() == before['sha256']
    path = HERE/'after'/rel
    raw = path.read_bytes()
    ast.parse(raw, feature_version=(3, 9))
    result = dict(stage='automatic-listening-v9-ui-fault-diagnostics',
        before_startup_sha256=old['startup_sha256'], before_manifest_sha256=old['source_manifest_sha256'],
        sources={rel:dict(source=path.relative_to(PROJECT).as_posix(),
            sha256=hashlib.sha256(raw).hexdigest(), before_sha256=before['sha256'])},
        business_options=old['business_options'], gui_options=dict(voice_barge_in=False),
        wake_word_required=False, conversation_mode='half_duplex', queue_frames=8,
        model_or_threshold_changes=False, source_only=True, private_data_replayed=False)
    (HERE/'revision.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
