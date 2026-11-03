"""Local source/config replay snapshot only; no environment, model or DB copy."""
import hashlib
import json
from pathlib import Path
import shutil
D=Path(__file__).resolve().parent;H=D.parent;PROJECT=H.parents[4]
mapping_path=H.parent/'release_v18_candidate/v18_evidence/source_mapping.json'
raw=mapping_path.read_bytes();mapping=json.loads(raw)
manifest=json.loads((D/'SOURCE_MANIFEST.json').read_bytes())
assert hashlib.sha256(raw).hexdigest()==manifest['baseline_mapping_sha256']
configs={'config/character_profile.local.json','config/persona.xuefei.candidate.json',
    'config/yuki_pair.formal.json','config/yuki_accepted_prompt.baseline.txt'}
pins={p:s for p,s in mapping['component_pins'].items() if p.endswith('.py') or p in configs}
roots=[H/'candidate_h01/after',H/'candidate_speaker_close/after',
    H.parent/'memory_observation_candidate_r2/after',
    H.parent/'animation_thinking_collaboration/frame_rate_24_candidate/ui_timing_probe/candidate/aura',
    H/'board_integration_v17/local_runtime_v17',PROJECT/'aura']
found={}
for relative,digest in pins.items():
    for root in roots:
        path=root/relative
        if path.is_file() and not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest()==digest:
            found[relative]=path;break
    else:raise ValueError('No exact saved public v18 source: '+relative)
target=D/'public_v18_snapshot'
for relative,path in found.items():
    dest=target/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
(D/'source_mapping.v18.json').write_bytes(raw)
print(json.dumps(dict(status='SAVED_PUBLIC_V18_SOURCE_SNAPSHOT_NOT_LIVE',files=len(found),model_or_database_copied=False)))
