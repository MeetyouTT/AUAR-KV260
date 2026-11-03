"""Root-only revision preparation against current v12 source receipt."""
import ast,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[4]
INTEGRATION=HERE.parent.parent
if __name__=='__main__':
    old=json.loads((INTEGRATION/'listening_entry_fix/actual_automatic-listening-v12-fixed-status-copy.json').read_text(encoding='utf-8'))
    info=json.loads((HERE/'HANDOFF.json').read_text(encoding='utf-8'))
    assert info['tests']['candidate']['passed']==20 and info['tests']['regression']['passed']==236
    source={}
    for rel,item in info['files'].items():
        path=HERE/item['path'];raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==item['sha256']
        ast.parse(raw,feature_version=(3,9))
        source[rel]=dict(source=path.relative_to(PROJECT).as_posix(),sha256=item['sha256'],before_sha256=item['before_sha256'])
    revision=dict(stage='automatic-listening-v13-memory-generation',before_startup_sha256=old['startup_sha256'],
        before_manifest_sha256=old['source_manifest_sha256'],sources=source,business_options=old['business_options'],
        gui_options=dict(voice_barge_in=False),wake_word_required=False,conversation_mode='half_duplex',queue_frames=8,
        model_or_threshold_changes=False,source_only=True,private_data_replayed=False,
        rollback_requires_retaining_generation_fix=True)
    (HERE/'revision_root.json').write_bytes((json.dumps(revision,indent=2)+'\n').encode())
    print(json.dumps(dict(stage=revision['stage'],files=list(source))))
