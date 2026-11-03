"""Copy two verified new-boot sources for local UI follow-up work."""
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
ANIM=HERE.parent
REPAIR=ANIM.parent


def main():
    path=REPAIR/'release_v18_newboot_candidate/newboot_evidence/source_mapping.json'
    mapping=json.loads(path.read_text(encoding='utf-8'))
    if mapping['startup_sha256']!='70a2f7fa5440f2b65004d66d5c4984b664ccc2b60131a0abd9a8351591c8d4e6':
        raise ValueError('Baseline entry requires review')
    files={'tools/board_avatar_gtk.py':ANIM/'ui_responsiveness_v18/candidate/aura/tools/board_avatar_gtk.py',
        'tools/production_business_ui.py':ANIM/'runtime_v16/tools/production_business_ui.py'}
    pins={}
    for relative,source in files.items():
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        if digest!=mapping['component_pins'][relative]:raise ValueError(relative)
        pins[relative]=digest
        for directory in ('before','candidate'):
            target=HERE/directory/'aura'/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():raise FileExistsError(target)
            shutil.copyfile(source,target)
    result=dict(schema='aura.ui-final-values-baseline.v1',startup_sha256=mapping['startup_sha256'],
        boot_id=mapping['boot_id'],source_manifest_sha256=mapping['source_manifest_sha256'],
        source_mapping_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),before_pins=pins,
        target_fps=16,device_access=False,production_modified=False)
    (HERE/'BASELINE.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
