"""Bind the frozen complete-capture overlay to the exact current board revision."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
CANDIDATE=HERE.parent/'production_frontend_process_capture_candidate'
BEFORE={
    'aura/board/runtime/audio/board_frontend_process.py':'8b5db6681e7ae1dd7040ab9aa2247ba59efb515286feebed5956034a6993dd63',
    'aura/board/runtime/audio/board_frontend_auto.py':None,
    'aura/tools/production_board_business_gui.py':'911ee09873a84d4c4c176e3798749a1813bee4d42dd05c6fc0ed108c6c7cfe2a',
    'aura/tools/production_frontend_selection.py':'bfef18d9ccd06e39357f5f375e6dc4c1d5d187bed51787e78206018658bb1a1b',
}

def main():
    manifest=json.loads((CANDIDATE/'overlay_manifest.json').read_text(encoding='utf-8'))
    assert set(manifest['files'])==set(BEFORE)
    sources={}
    for rel,item in manifest['files'].items():
        assert item['before_sha256']==BEFORE[rel]
        path=CANDIDATE/'after'/rel;raw=path.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
        ast.parse(raw,feature_version=(3,9))
        sources[rel.removeprefix('aura/')]=dict(source=path.relative_to(PROJECT).as_posix(),sha256=item['sha256'],before_sha256=item['before_sha256'])
    revision=dict(stage='automatic-listening-v3-complete-capture',
        before_startup_sha256='b81fff59527c11323f9f869c647e0563f393a01c7f59bc39fde23391eb4f4275',
        before_manifest_sha256='b363b88f6e01c3ddd94bc27d731abe5f228fb60ef0cec602f7d7d3dcba89af11',
        business_options=dict(frontend_process=True,frontend_capture_process=True,frontend_optimization='baseline',capture_priority_nice=-10,frontend_threads=1),
        sources=sources,queue_frames=8,model_or_threshold_changes=False,source_only=True)
    (HERE/'complete_capture_revision.json').write_text(json.dumps(revision,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='COMPLETE_CAPTURE_SOURCE_REVISION_PREPARED',files={r:x['sha256'] for r,x in sources.items()})))

if __name__=='__main__':main()
