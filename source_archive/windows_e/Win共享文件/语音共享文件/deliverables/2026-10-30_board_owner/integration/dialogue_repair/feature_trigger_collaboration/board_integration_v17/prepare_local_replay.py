"""Copy only exact v17 public Python/config bytes for local synthetic replay.
No SSH, model, environment or private state is read or copied.
"""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
H = HERE.parent
PROJECT = H.parents[4]
MAPPING_PATH = H.parent/'release_v17_candidate/v17_evidence/source_mapping.json'
PUBLIC_CONFIGS = {'config/character_profile.local.json', 'config/persona.xuefei.candidate.json',
                  'config/yuki_pair.formal.json', 'config/yuki_accepted_prompt.baseline.txt'}


def main():
    raw = MAPPING_PATH.read_bytes()
    mapping = json.loads(raw)
    pins = {r:d for r,d in mapping['component_pins'].items() if r.endswith('.py') or r in PUBLIC_CONFIGS}
    roots = [H/'candidate_v3/after', H.parent/'animation_thinking_collaboration/paired_overlay/aura',
             H/'runtime_v16', PROJECT/'aura',
             PROJECT/'deliverables/2026-10-30_board_owner/integration/resume_yuki_business_candidate_v2/candidate/aura']
    found, missing = {}, []
    for rel,digest in pins.items():
        for root in roots:
            path = root/rel
            if path.is_file() and not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest() == digest:
                found[rel] = path
                break
        else:
            missing.append(rel)
    if missing:
        raise ValueError('Missing exact public sources: '+repr(missing))
    target = HERE/'local_runtime_v17'
    target.mkdir(exist_ok=True)
    for rel,path in found.items():
        dest = target/rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    (HERE/'source_mapping.json').write_bytes(raw)
    receipt = dict(status='LOCAL_PUBLIC_SOURCE_REPLAY_ONLY', copied_files=len(found),
        target=str(target), mapping_sha256=hashlib.sha256(raw).hexdigest(),
        files={r:dict(source=str(path), sha256=pins[r]) for r,path in found.items()},
        excluded=['model_weights','environments','private_databases','PCM','biometric_templates'])
    (HERE/'LOCAL_SOURCE_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'],copied_files=len(found))))


if __name__ == '__main__':
    main()
