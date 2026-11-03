"""Freeze only explicit source files for a synthetic ARM memory/model probe."""
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
FILES = (
    'common/board_memory.py', 'common/board_timeline_clock.py',
    'common/memory_commands.py', 'common/model_inference_wire.py', 'common/spoken_input.py',
    'common/timeline.py', 'common/fact_answers.py',
    'common/reply_quality.py', 'common/profile_memory.py', 'common/conversation_store.py',
    'common/profile_access.py', 'board/runtime/character.py', 'board/runtime/board_dialogue.py',
    'board/runtime/board_dialogue_client.py', 'board/runtime/board_memory_policy.py',
    'board/visual_timeline.py',
)


def main():
    entries = []
    frozen = {}
    for relative in FILES:
        source = PROJECT/'aura'/relative
        data = source.read_bytes()
        frozen[relative] = data
        entries.append(dict(name='code/'+relative, source=str(source), bytes=len(data),
                            sha256=hashlib.sha256(data).hexdigest(), provenance='candidate_source_only'))
    digest = hashlib.sha256(json.dumps([(e['name'],e['sha256']) for e in entries]).encode()).hexdigest()[:16]
    for entry, relative in zip(entries, FILES):
        target = HERE/'source'/digest/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            assert target.read_bytes() == frozen[relative]
        else:
            with target.open('xb') as stream:
                stream.write(frozen[relative])
        entry['source'] = str(target)
    manifest = dict(version=1, purpose='synthetic_arm_semantic_memory',
                    candidate_root='/home/root/aura-board-owner-candidate-20261030/semantic-'+digest,
                    entries=entries, total_bytes=sum(e['bytes'] for e in entries))
    path = HERE/'semantic_asset_manifest.local.json'
    frozen_manifest = HERE/'source'/digest/'semantic_asset_manifest.local.json'
    serialized = json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'
    if frozen_manifest.exists():
        assert frozen_manifest.read_text(encoding='utf-8') == serialized
    else:
        with frozen_manifest.open('x',encoding='utf-8') as stream:
            stream.write(serialized)
    path.write_text(serialized,encoding='utf-8')
    public = dict(manifest, entries=[{k:v for k,v in e.items() if k!='source'} for e in entries])
    print(json.dumps(dict(candidate_root=manifest['candidate_root'],
                         manifest_sha256=hashlib.sha256(json.dumps(public,separators=(',',':')).encode()).hexdigest(),
                         total_bytes=manifest['total_bytes'])))


if __name__ == '__main__':
    main()
