"""Package identical public16/24 measurement scripts; never opens a device."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

HERE=Path(__file__).resolve().parent
RATE=HERE.parent


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    script=HERE/'preview_pair_template.py';ast.parse(script.read_text(encoding='utf-8'))
    baseline=json.loads((RATE/'BASELINE.json').read_text(encoding='utf-8'))
    base_library=RATE.parent/'native_build_result/libaura_yuki.so'
    if sha(base_library)!=baseline['native_library_sha256']:raise ValueError('Current v17 native library changed')
    bundles={}
    for fps in (16,24):
        variant=RATE/('paired_'+str(fps));out=HERE/('rate_'+str(fps));out.mkdir(exist_ok=False)
        receipt=json.loads((variant/'PAIRING_RECEIPT.json').read_text(encoding='utf-8'))
        tests=json.loads((variant/'TEST_RESULTS.json').read_text(encoding='utf-8'))
        if not tests['successful'] or tests['files']!=receipt['files']:raise ValueError('Matching local tests required')
        for relative,digest in receipt['files'].items():
            source=variant/'aura'/relative
            if sha(source)!=digest:raise ValueError('Variant source changed')
            destination=out/'paired_overlay/aura'/relative
            destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
        target=out/'paired_overlay/aura/tools/libaura_yuki.so'
        shutil.copyfile(base_library,target)
        pins=dict(receipt['files']);pins['tools/libaura_yuki.so']=sha(target)
        selection=json.loads((variant/'aura/config/yuki_pair.formal.json').read_text(encoding='utf-8'))
        shutil.copyfile(script,out/'preview_public_states.py')
        spec=dict(schema='aura.native-rate-public-perf.v1',script_sha256=sha(script),overlay_pins=pins,
            selection_sha256=receipt['selection_sha256'],target_fps=fps,required_features=1,
            variant='rate_'+str(fps),render_size=[423,516],plan_seconds=24,
            public_runtime_pins={k:v for k,v in selection['runtime_pins'].items()
                if k.startswith('assets/yuki/') or k=='tools/egl_window.py'})
        (out/'PREVIEW_SPEC.json').write_text(json.dumps(spec,indent=2)+'\n',encoding='utf-8')
        archive=HERE/('rate_'+str(fps)+'_public_preview.zip')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
            for path in sorted(out.rglob('*')):
                if path.is_file():output.write(path,path.relative_to(out).as_posix())
        bundles[str(fps)]=dict(archive=archive.name,sha256=sha(archive),bytes=archive.stat().st_size,
            spec_sha256=sha(out/'PREVIEW_SPEC.json'),selection_sha256=receipt['selection_sha256'])
    result=dict(schema='aura.native-rate-perf-packages.v1',status='PUBLIC16_24_PACKAGES_READY_NOT_RUN',
        measurement_script_sha256=sha(script),bundles=bundles,device_access=False,
        unchanged_native_library=baseline['native_library_sha256'],motion_included=False,
        required_order='First diagnose/fix live UI stalls at16, then isolated16/24, then real business audio-safe validation')
    (HERE/'PACKAGES.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':main()
