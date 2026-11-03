"""Prepare reviewed source/config merge only; no hardware or model action."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[4]
MEMORY=HERE.parent/'memory_health_collaboration/v14_validation_candidate'

if __name__=='__main__':
    baseline=json.loads((HERE/'baseline_manifest.json').read_text(encoding='utf-8'))
    installed=json.loads((HERE.parent.parent/'listening_entry_fix/actual_automatic-listening-v13-memory-generation.json').read_text(encoding='utf-8'))
    assert baseline['startup_sha256']==installed['startup_sha256']
    bridge=json.loads((HERE/'HANDOFF.json').read_text(encoding='utf-8'))
    memory=json.loads((MEMORY/'HANDOFF.json').read_text(encoding='utf-8'))
    assert bridge['combined_tests']['main_tests_passed']==68
    assert memory['tests']['targeted']['passed']==34 and memory['tests']['regression']['passed']==270
    sources={}
    for folder,entries in ((HERE,bridge['sources']),(MEMORY,memory['files'])):
        for rel,item in entries.items():
            assert rel not in sources
            path=folder/item.get('path','after/'+rel);raw=path.read_bytes()
            assert hashlib.sha256(raw).hexdigest()==item['sha256']
            assert baseline['component_sha256'].get(rel)==item['before_sha256']
            ast.parse(raw,feature_version=(3,9))
            sources[rel]=dict(source=path.relative_to(PROJECT).as_posix(),sha256=item['sha256'],before_sha256=item['before_sha256'])
    assert len(sources)==8
    options=dict(installed['business_options'],dialogue_output_format='dialogue_abc_v1')
    revision=dict(stage='automatic-listening-v14-compact-dialogue-memory',
        before_startup_sha256=baseline['startup_sha256'],before_manifest_sha256=baseline['source_manifest_sha256'],
        sources=sources,business_options=options,gui_options=dict(voice_barge_in=False),
        wake_word_required=False,conversation_mode='half_duplex',queue_frames=8,
        model_or_threshold_changes=False,private_data_replayed=False,
        source_only=True,rollback_requires_retaining_generation_fix=True)
    (HERE/'revision.json').write_text(json.dumps(revision,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(stage=revision['stage'],source_count=len(sources),selected_format=options['dialogue_output_format'])))
