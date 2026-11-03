"""Prepare the reviewed two-file revision; this script never deploys."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[4]

if __name__=='__main__':
    baseline=json.loads((HERE/'baseline_manifest.json').read_text(encoding='utf-8'))
    handoff=json.loads((HERE/'HANDOFF.json').read_text(encoding='utf-8'))
    assert handoff['tests']['total_passed']==73
    sources={}
    for item in handoff['files']:
        rel=item['path'];path=HERE/'after'/rel;raw=path.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
        assert baseline['component_sha256'][rel]==item['before_sha256']
        ast.parse(raw,feature_version=(3,9))
        sources[rel]=dict(source=path.relative_to(PROJECT).as_posix(),sha256=item['sha256'],before_sha256=item['before_sha256'])
    assert len(sources)==2
    options=dict(baseline['business_options']);options['frontend_optimization']='combined'
    revision=dict(stage='automatic-listening-v11-frontend-buffer-reuse',
        before_startup_sha256=baseline['startup_sha256'],before_manifest_sha256=baseline['source_manifest_sha256'],
        sources=sources,business_options=options,gui_options=dict(voice_barge_in=False),
        wake_word_required=False,conversation_mode='half_duplex',queue_frames=8,
        model_or_threshold_changes=False,source_only=True,private_data_replayed=False)
    (HERE/'revision.json').write_bytes((json.dumps(revision,indent=2)+'\n').encode())
    print(json.dumps(dict(stage=revision['stage'],sources=list(sources),options=options)))
