"""Verify source and public model/config pins; never read gallery data or initialize a runner."""
import hashlib
import json
from pathlib import Path
import stat

boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot=='bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
ops=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
meta=json.loads((ops/'meta.json').read_text())
aura=Path(meta['candidate_root'])/'aura'
config=json.loads((ops/('native-run-'+boot+'-229296')/'config.json').read_text())
native=config['native_execution']
def raw_file(path,limit=2000000):
    path=Path(path);st=path.lstat()
    assert stat.S_ISREG(st.st_mode) and st.st_size<=limit
    return path.read_bytes()
def sha(path,limit=2000000):return hashlib.sha256(raw_file(path,limit)).hexdigest()
source_manifest=Path(native['source_manifest'])
assert sha(source_manifest)==native['source_manifest_sha256']
expected=json.loads(source_manifest.read_text())['files']
actual={str(p.relative_to(aura)):sha(p) for p in aura.rglob('*.py') if not p.is_symlink()}
assert actual==expected
manifests=[ops/'pan-face-edge-v5/face-source-v17/deployment-manifest.json',
    ops/'pan-face-edge-v5/native-operator-v1/runtime-manifest.json']
closures=[]
for path in manifests:
    doc=json.loads(path.read_text());pins=doc.get('pins',doc.get('files'))
    checks=[dict(path=p,matches=sha(p)==h) for p,h in pins.items()]
    assert all(x['matches'] for x in checks)
    closures.append(dict(path=str(path),sha256=sha(path),checked=len(checks),matches=True))
idpath=Path(config['identity']['config']);idraw=raw_file(idpath);identity=json.loads(idraw)
files=[]
for rel in ('board/vision/native_protection.py','board/vision/ui_camera_service.py'):
    path=aura/rel;raw=raw_file(path)
    files.append(dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),content=raw.decode()))
driver=Path('/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c/bench_identity_stop.py')
raw=raw_file(driver);files.append(dict(path=str(driver),sha256=hashlib.sha256(raw).hexdigest(),content=raw.decode()))
feature={}
for key,value in identity.items():
    if 'threshold' in key or 'model' in key or key in ('face','face_detector','feature','sface','yunet','backend'):
        feature[key]=value
checkpoint=Path(native['checkpoint_output'])
checkpoint_raw=raw_file(checkpoint)
document=json.loads(checkpoint_raw)
seed=document.get('seed',{})
print(json.dumps(dict(boot=boot,source_closure_matches=True,source_files=len(actual),
    source_manifest_sha256=native['source_manifest_sha256'],closures=closures,
    native_library_matches=sha(native['library'],4000000)==native['library_sha256'],
    yolo_model_matches=sha(config['yolo']['model'],64000000)==config['yolo']['model_sha256'],
    identity_config_path=str(idpath),identity_config_sha256=hashlib.sha256(idraw).hexdigest(),
    identity_config_keys=sorted(identity),identity_public_settings=feature,
    checkpoint_before=dict(path=str(checkpoint),sha256=hashlib.sha256(checkpoint_raw).hexdigest(),
        schema=document.get('schema'),purpose=seed.get('purpose'),source_pid=seed.get('source_pid'),
        source_boot=seed.get('boot_id'),source_birth=seed.get('source_birth_ticks')),
    files=files,source_imported=False,services_changed=False)))
