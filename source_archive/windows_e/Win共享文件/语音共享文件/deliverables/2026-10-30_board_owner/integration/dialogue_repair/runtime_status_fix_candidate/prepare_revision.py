import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
PROJECT = REPAIR.parents[3]

if __name__ == '__main__':
    old = json.loads((REPAIR.parent/'listening_entry_fix/actual_automatic-listening-v9-ui-fault-diagnostics.json').read_text(encoding='utf-8'))
    rel = 'tools/board_avatar_gtk.py'
    before = REPAIR/'runtime_fault_candidate/after'/rel
    pin = hashlib.sha256(before.read_bytes()).hexdigest()
    assert pin == old['source_files'][rel] == '4fa8b74b71c89f08fdf9b5d376fd065b02e02baea01603ed03299a9971552e61'
    path = HERE/'after'/rel
    raw = path.read_bytes()
    ast.parse(raw, feature_version=(3, 9))
    result = dict(stage='automatic-listening-v10-null-status-fix',
        before_startup_sha256=old['startup_sha256'], before_manifest_sha256=old['source_manifest_sha256'],
        sources={rel:dict(source=path.relative_to(PROJECT).as_posix(),
            sha256=hashlib.sha256(raw).hexdigest(), before_sha256=pin)},
        business_options=old['business_options'], gui_options=dict(voice_barge_in=False),
        wake_word_required=False, conversation_mode='half_duplex', queue_frames=8,
        model_or_threshold_changes=False, source_only=True, private_data_replayed=False)
    (HERE/'revision.json').write_bytes((json.dumps(result,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(result))
