"""Seal only public source/assets; no production data or execution."""
import ast
import hashlib
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent


def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    merged=json.loads((HERE/'candidate_manifest.json').read_text(encoding='utf8'))
    fresh=json.loads((HERE/'current_formal_snapshot.json').read_text(encoding='utf8'))['files']
    memory=json.loads((HERE/'memory_dependency_pins.json').read_text(encoding='utf8'))
    files={};delta={}
    for relative,row in merged['files'].items():
        path=HERE/'candidate/aura'/relative;raw=path.read_bytes();assert sha(raw)==row['sha256']
        if relative.endswith('.py'):ast.parse(raw,feature_version=(3,9))
        name='aura/'+relative;files[name]=dict(sha256=sha(raw),bytes=len(raw),provider=row['provider'])
        if relative not in fresh or row['sha256']!=fresh[relative]['sha256']:delta[name]=raw
    for relative,expected in memory['files'].items():assert files['aura/'+relative]['sha256']==expected
    assert files['aura/tools/libaura_yuki.so']['sha256']=='887546c09eb1897845c8d7f55a9e3f9b9c761448c7410f2b599259ae0b51efd2'
    assert files['aura/ui/ui_tokens.json']['sha256']=='8ad5382b9154a8d39241ed8e158339a207e47613634b33a344af2a838f1ab2c8'
    archive=HERE/'production_business.overlay.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,raw in sorted(delta.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,30,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100600<<16;z.writestr(info,raw)
    value=dict(schema='aura.production-business.overlay.v1',status='SOURCE_FROZEN_ROOT_MIGRATION_AND_PRESENTATION_REQUIRED',
        basis_startup_sha256=merged['basis_startup_sha256'],basis_component_count=304,
        overlay_sha256=sha(archive.read_bytes()),overlay_files={name:{'sha256':sha(raw),'bytes':len(raw)} for name,raw in sorted(delta.items())},
        files=files,memory_dependency_handoff_sha256=memory['handoff_sha256'],
        existing_appearance_preserved=True,initial_retention_enabled=False,bootstrap_receipt_required=True,
        models_copied=False,real_databases_or_identities_copied=False,unit_or_device_action=False,
        remaining_before_live_voice=['Root private import/committed receipt','Root presentation-cache/metadata-only evidence overlay',
                                    'Root normal source/worker handoff and public silent audio acceptance'])
    raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode();(HERE/'production_business.manifest.json').write_bytes(raw)
    print(json.dumps({'files':len(files),'overlay_files':len(delta),'overlay_bytes':archive.stat().st_size,
        'overlay_sha256':value['overlay_sha256'],'manifest_sha256':sha(raw),
        'assembler_sha256':sha((HERE/'assemble_production.py').read_bytes())}))


if __name__=='__main__':main()
