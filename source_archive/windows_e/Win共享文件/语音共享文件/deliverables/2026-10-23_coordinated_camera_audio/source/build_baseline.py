"""Freeze the reviewed handoff module into a standalone guarded board helper."""
import ast,base64,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
raw=(ROOT/'handoff.py').read_bytes();sha=hashlib.sha256(raw).hexdigest()
code='MODULE_SHA='+repr(sha)+'\nMODULE_DATA='+repr(base64.b64encode(gzip.compress(raw,mtime=0)).decode())+'\n'
code+='''import base64,gzip,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
if sys.flags.optimize:raise RuntimeError('Assertions required')
sys.dont_write_bytecode=True
source=Path(sys._getframe().f_code.co_filename).resolve()
digest=hashlib.sha256(source.read_bytes()).hexdigest()
root=Path('/home/root/aura-coordinated-switch-20261023')/digest[:16]
root.mkdir(parents=True,exist_ok=True,mode=0o700)
assert root.resolve()==root
raw=gzip.decompress(base64.b64decode(MODULE_DATA));assert hashlib.sha256(raw).hexdigest()==MODULE_SHA
module_path=root/'handoff.py';assert not module_path.is_symlink()
if module_path.exists():assert module_path.read_bytes()==raw
else:
 with module_path.open('xb') as f:f.write(raw)
spec=importlib.util.spec_from_file_location('_owned_audio_camera_handoff',module_path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
if len(sys.argv)>1 and sys.argv[1]=='--restore':
 assert len(sys.argv)==3 and Path(sys.argv[2])==root
 result=module.BoardOps(root).restore();print(json.dumps(result))
elif len(sys.argv)>1 and sys.argv[1]=='--run':
 print(json.dumps(module.run_baseline(root,source)))
else:
 assert not (root/'report.json').exists(),'Do not replace an earlier experiment'
 unit='aura-coordinated-baseline-'+digest[:16]
 out=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=540',
  '/usr/bin/python3','-B',str(source),'--run'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10)
 assert out.returncode==0,out.stdout.decode(errors='replace')[-400:]
 print(json.dumps({'started':True,'unit':unit,'report':str(root/'report.json'),'helper_sha256':digest,'module_sha256':MODULE_SHA}))
'''
ast.parse(code)
target=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_coordinated_baseline_r2_20261023.py')
assert not target.exists();target.write_text(code)
result={'helper':str(target),'sha256':hashlib.sha256(code.encode()).hexdigest(),'module_sha256':sha,
        'seconds':120,'runtime_max_s':540,'independent_restore_after_s':600,'software_tests':16,
        'model_or_scheduler_changes':False,'board_verified':False}
(ROOT/'baseline-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
