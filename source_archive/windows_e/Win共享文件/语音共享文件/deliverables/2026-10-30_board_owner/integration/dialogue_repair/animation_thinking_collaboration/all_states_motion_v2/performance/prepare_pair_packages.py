"""After native seal, make matched baseline/candidate public preview packages."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

HERE=Path(__file__).resolve().parent
MOTION=HERE.parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    script=HERE/'preview_pair_template.py'
    ast.parse(script.read_text(encoding='utf-8'))
    before=json.loads((MOTION/'BASELINE_V17.json').read_text(encoding='utf-8'))
    after=json.loads((MOTION/'motion_overlay/PAIRING_RECEIPT.json').read_text(encoding='utf-8'))
    if after['status']!='MOTION_PAIRED_READY_NOT_DEPLOYED':raise ValueError('Verified motion overlay required')
    bundles={}
    for variant,root,pins,features in (
        ('v17_baseline',MOTION/'before/aura',before['renderer_pins'],1),
        ('motion_candidate',MOTION/'motion_overlay/aura',after['files'],3)):
        out=HERE/variant;out.mkdir(exist_ok=False)
        selection=json.loads((root/'config/yuki_pair.formal.json').read_text(encoding='utf-8'))
        for relative,expected in pins.items():
            source=root/relative
            if sha(source)!=expected:raise ValueError('Paired source mismatch: '+relative)
            destination=out/'paired_overlay/aura'/relative
            destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
        shutil.copyfile(script,out/'preview_public_states.py')
        spec=dict(schema='aura.all-state-motion-paired-perf-preview.v1',
            script_sha256=sha(script),overlay_pins=pins,
            selection_sha256=pins['config/yuki_pair.formal.json'],
            public_runtime_pins={key:digest for key,digest in selection['runtime_pins'].items()
                if key.startswith('assets/yuki/') or key=='tools/egl_window.py'},
            required_features=features,variant=variant,target_fps=16,render_size=[423,516],
            plan_seconds=24,capture_scope='Native character framebuffer only')
        save(out/'PREVIEW_SPEC.json',spec)
        archive=HERE/(variant+'_public_pair.zip')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
            for path in sorted(out.rglob('*')):
                if path.is_file():output.write(path,path.relative_to(out).as_posix())
        bundles[variant]=dict(archive=archive.name,sha256=sha(archive),bytes=archive.stat().st_size,
            spec_sha256=sha(out/'PREVIEW_SPEC.json'),selection_sha256=spec['selection_sha256'])
    result=dict(schema='aura.all-state-motion-perf-packages.v1',
        status='READY_FOR_OWNER_SCHEDULED_MUTUALLY_EXCLUSIVE_ABBA',
        measurement_script_sha256=sha(script),bundles=bundles,
        order=['A1:v17_baseline','B1:motion_candidate','B2:motion_candidate','A2:v17_baseline'],
        run_seconds=24,display_size=[423,516],target_fps=16,
        devices_started=False,production_modified=False)
    save(HERE/'PAIRED_PACKAGES.json',result);print(json.dumps(result))


if __name__=='__main__':main()
