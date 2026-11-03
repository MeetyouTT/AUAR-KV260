"""Prepare private candidate files/config and prove same-boot refusal only.

Never installs a unit, starts/stops services, creates a model or reboots.
"""
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import urllib.request

sys.dont_write_bytecode=True
boot='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
bundle=Path('/home/root/aura-dpu-vision-20261021/staging/751288cac1c6e307/bundle.tar.gz')
assert hashlib.sha256(bundle.read_bytes()).hexdigest()=='751288cac1c6e307019bbaa3802e4e38341a92741de9da8ff7083d8351c3a266'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def camera():
    with op.open('http://127.0.0.1:8790/health',timeout=4) as stream:h=json.load(stream)
    s=h['dpu_schedule']
    return {'pid':h['pid'],'faults':{k:v['overruns'] for k,v in s['optional'].items()},
            'owner_fenced':s['owner_fenced'],'primary_overruns':s['primary_period_overruns']}
before=camera();assert before['pid']==29563 and not before['owner_fenced']
target=Path('/home/root/aura-native-critical-20261024/candidates/native-v2-d7256b06808509c9')
target.mkdir(parents=True,exist_ok=False,mode=0o700)
with tarfile.open(bundle,'r:gz') as archive:
    members=archive.getmembers()
    assert len(members)==224 and len({m.name for m in members})==224
    for member in members:
        assert member.isfile() and member.size<2000000
        name=Path(member.name)
        assert not name.is_absolute() and '..' not in name.parts
        assert (member.name.startswith('aura/') and name.suffix=='.py') or member.name in ('candidate.json','camera-python-manifest.json')
        path=target/name
        assert path.resolve().is_relative_to(target)
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as output:output.write(archive.extractfile(member).read())
manifest=target/'camera-python-manifest.json'
files=json.loads(manifest.read_text())['files']
assert len(files)==222
for name,pin in files.items():assert hashlib.sha256((target/'aura'/name).read_bytes()).hexdigest()==pin
actual={str(p.relative_to(target/'aura')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (target/'aura').rglob('*.py')}
assert actual==files
library=Path('/home/root/aura-native-critical-20261024/link-only/5cae51cf9d22e5f7/libaura_native_v2_candidate.so')
library_sha='c675ba698d45acd8742e52403e6186f43dc56d7d313d0e740896b19412bde656'
assert hashlib.sha256(library.read_bytes()).hexdigest()==library_sha
prefix=Path('/home/root/aura-native-critical-20261024/legacy-prefix/ecda1d52dbc4d3a0/legacy-boot-archive.json')
prefix_sha='ecda1d52dbc4d3a0005f55c6a85d489c92293076661403c1d834666adae4e2c7'
assert hashlib.sha256(prefix.read_bytes()).hexdigest()==prefix_sha
old=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-vision-recovery-c76110abefc304bb')
config=json.loads((old/'board_camera_ui.json').read_text())
identity=Path(config['identity']['config'])
if not identity.is_absolute():identity=(old/'aura'/identity).resolve()
assert hashlib.sha256(identity.read_bytes()).hexdigest()=='398ece6a4d5d81076c9a4f9f40a43e97cedd469e0b47e3a835e589a2255ca6e3'
config['identity']['config']=str(identity)
state=target/'state';state.mkdir(mode=0o700)
config.pop('dpu_protection_seed',None)
config.pop('dpu_protection_allow_new_boot',None)
config['native_execution']={
    'library':str(library),'library_sha256':library_sha,
    'seed':{'path':str(prefix),'sha256':prefix_sha},
    'source_manifest':str(manifest),'source_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
    'source_unit_sha256':'29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512',
    'checkpoint_output':str(state/'native-protection-checkpoint.json'),
    'allow_new_kernel_boot':True,'allow_legacy_new_kernel_boot':True,
    'new_boot_marker_directory':str(state/'kernel-history')}
config_path=target/'board_camera_ui.proposed.json'
raw=(json.dumps(config,indent=2)+'\n').encode()
with config_path.open('xb') as stream:stream.write(raw)
sys.path.insert(0,str(target/'aura'))
from board.vision import native_startup
calls=[]
def forbidden(*args,**kwargs):
    calls.append('unexpected_factory')
    raise AssertionError('Candidate preparation must not create a model owner')
native_startup.NativeContext=forbidden
refusal=None
try:native_startup.preflight(config,boot_id=boot,root=target/'aura')
except ValueError as exc:refusal=str(exc)
assert refusal and 'Legacy health-only' in refusal and not calls
after=camera()
report={'scope':'SOURCE_PREPARATION_AND_CURRENT_BOOT_REFUSAL_NO_ACTIVATION',
    'candidate_id':'native-v2-d7256b06808509c9','source_files':222,
    'candidate_path':str(target),'proposed_config_path':str(config_path),
    'proposed_config_sha256':hashlib.sha256(raw).hexdigest(),
    'library_sha256':library_sha,'prefix_sha256':prefix_sha,
    'current_boot_correctly_refused':True,'refusal':refusal,
    'model_factories_called':0,'candidate_jobs':0,'service_changes':0,'reboots':0,
    'before':before,'after':after,'passed':before==after}
with (target/'preparation-report.json').open('x') as stream:json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps(report))
