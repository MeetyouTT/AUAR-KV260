"""Assemble code-only test baseline from the root's verified public source pins.

Only Python sources and the selected public character config are copied. No
model resource, private configuration, template or runtime database is read.
"""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[4]
MAPPING=HERE.parent/'paraformer_small_validation/v16_evidence/source_mapping.json'


def main():
    receipt=json.loads(MAPPING.read_text(encoding='utf-8'))
    desired={rel:digest for rel,digest in receipt['component_pins'].items()
             if rel.endswith('.py') or rel=='config/character_profile.local.json'}
    found={}
    for rel,digest in desired.items():
        path=PROJECT/'aura'/rel
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==digest:
            found[rel]=path
    wanted={Path(rel).name for rel in desired if rel not in found}
    for path in (PROJECT/'deliverables/2026-10-30_board_owner/integration').rglob('*'):
        if path.name not in wanted or not path.is_file() or HERE in path.parents:
            continue
        raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
        for rel,expected in desired.items():
            if rel not in found and path.name==Path(rel).name and digest==expected:
                found[rel]=path
        wanted={Path(rel).name for rel in desired if rel not in found}
        if not wanted:
            break
    missing=sorted(set(desired)-set(found))
    rows={}
    for rel,path in found.items():
        destination=HERE/'runtime_v16'/rel
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=desired[rel]:
            raise ValueError('Source changed during resolution')
        if destination.exists() and destination.read_bytes()!=raw:
            raise ValueError('Frozen runtime baseline changed')
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(raw)
        rows[rel]=dict(sha256=desired[rel],source=str(path),bytes=len(raw))
    baseline=json.loads((HERE/'candidate/SOURCE_BASELINE.json').read_text(encoding='utf-8'))
    for rel,row in baseline['files'].items():
        if row['sha256']!=receipt['component_pins'][rel]:
            raise ValueError('Candidate before-source does not match v16: '+rel)
    out=dict(schema='aura.feature-v16-sources.v1',startup_sha256=receipt['startup_sha256'],
             source_manifest_sha256=receipt['source_manifest_sha256'],
             source_mapping_sha256=hashlib.sha256(MAPPING.read_bytes()).hexdigest(),
             candidate_before_sources_match_v16=True,files=rows,missing=missing,
             source_only=True,private_data_read=False)
    (HERE/'V16_SOURCE_VERIFICATION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(matched=len(rows),missing=missing,candidate_before_sources_match_v16=True)))
    if missing:
        raise SystemExit(1)


if __name__=='__main__':
    main()
