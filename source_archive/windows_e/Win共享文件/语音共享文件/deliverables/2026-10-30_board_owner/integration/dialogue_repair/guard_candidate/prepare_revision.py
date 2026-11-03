import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPAIR=HERE.parent
PROJECT=REPAIR.parents[3]

if __name__=='__main__':
    old=json.loads((REPAIR/'actual_installed.json').read_text(encoding='utf-8'))
    assert old['startup_sha256']=='192861de11e3431736f306168230e63b087b81f05c5d20122d37f72d70698d48'
    source=HERE/'after/common/board_memory.py';raw=source.read_bytes();ast.parse(raw,feature_version=(3,9))
    pin=hashlib.sha256(raw).hexdigest();assert pin=='33cb8cedd191382967884850a31e8d106dc41a20b5deee493e23168c8c13b3b0'
    before=hashlib.sha256((REPAIR/'before/common/board_memory.py').read_bytes()).hexdigest()
    result=dict(stage='automatic-listening-v6-prepared-guard',before_startup_sha256=old['startup_sha256'],
        before_manifest_sha256=old['source_manifest_sha256'],sources={
        'common/board_memory.py':dict(source=source.relative_to(PROJECT).as_posix(),sha256=pin,before_sha256=before)},
        business_options=old['business_options'],gui_options=dict(voice_barge_in=False),
        wake_word_required=False,conversation_mode='half_duplex',queue_frames=8,
        model_or_threshold_changes=False,source_only=True,private_data_replayed=False)
    (HERE/'revision.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
