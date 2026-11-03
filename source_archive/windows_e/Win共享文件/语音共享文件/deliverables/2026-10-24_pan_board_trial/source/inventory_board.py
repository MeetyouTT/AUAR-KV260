import base64,hashlib,json
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
ops=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
meta=json.loads((ops/'meta.json').read_text());cfg=json.loads(Path(meta['candidate_config']).read_text())
identity=Path(cfg['identity']['config']);identity_config=json.loads(identity.read_text())
gui=Path('/home/root/aura-video-cpu-20261023/66cde810eb059dce/startup/config.json')
result={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'ops_meta':meta,'camera_native_config':cfg.get('native_execution'),
 'camera_config_sha256':sha(meta['candidate_config']),'identity_config_sha256':sha(identity),
 'database_path':identity_config['database'],'database_sha256':sha(identity_config['database']),
 'gui_startup_config':json.loads(gui.read_text()),'gui_startup_config_sha256':sha(gui),
 'ops_source_base64':base64.b64encode((ops/'boot_ops.py').read_bytes()).decode(),
 'ops_source_sha256':sha(ops/'boot_ops.py'),
 'firmware_files':{},'production_modified':False}
for app in ['kv260-benchmark-b4096','aura-visual-servo-b4096-v1']:
 root=Path('/lib/firmware/xilinx')/app
 result['firmware_files'][app]={str(p):{'sha256':sha(p),'bytes':p.stat().st_size} for p in root.iterdir() if p.is_file()}
print(json.dumps(result))
