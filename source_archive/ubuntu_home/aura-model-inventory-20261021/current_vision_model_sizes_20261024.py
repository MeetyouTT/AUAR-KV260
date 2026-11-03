import hashlib,json,time,urllib.request
from pathlib import Path
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot=='89d53e38-4726-4c94-b958-53f2dfb3bd4e'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as stream:h=json.load(stream)
assert h['pid']==1291 and h['dpu_schedule']['native_critical'] and not h['dpu_schedule']['owner_fenced']
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
cfg=json.loads((root/('native-run-'+boot+'-1291')/'config.json').read_text())
meta=json.loads((root/'meta.json').read_text())
identity=Path(cfg['identity']['config'])
if not identity.is_absolute():identity=Path(meta['candidate_root'])/'aura'/identity
raw=identity.read_bytes();assert hashlib.sha256(raw).hexdigest()=='398ece6a4d5d81076c9a4f9f40a43e97cedd469e0b47e3a835e589a2255ca6e3'
face=json.loads(raw)
assert h['detector']['model_sha256']==cfg['yolo']['model_sha256']
def artifact(task,value,backend):
 p=Path(value['model']);size=p.stat().st_size
 return dict(task=task,backend=backend,artifact_name=p.name,artifact_bytes=size,
  decimal_MB=size/1_000_000,MiB=size/1048576,load_config_sha256=value['model_sha256'])
rows=[artifact('yolo',cfg['yolo'],h['role']),artifact('yunet',face['face_backend'],h['identity']['face_targets']['backend']),
 artifact('sface',face['feature_backend'],h['identity']['feature_inference']['kind'])]
print(json.dumps(dict(scope='READ_ONLY_COMPILED_MODEL_FILE_SIZES_AND_LIVE_BACKENDS_NOT_PARAMETER_OR_RSS_SIZES',
 boot=boot,mono_ns=time.monotonic_ns(),pid=h['pid'],models=rows,
 load_config_matches_live_yolo=True,sface_model_id=h['identity']['feature_inference']['model_id'],
 identity_ready=h['identity']['feature_inference']['ready'],weights_rehashed_this_probe=False,
 model_instances_created=0,services_restarted=0)))
