"""Prepare an activation helper; it refuses to run without a qualified 1800s report."""
import ast,base64,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
control=(ROOT/'release_control.py').read_bytes();entry=(ROOT/'runtime_entry.py').read_bytes()
for data in (control,entry):ast.parse(data.decode())
code='CONTROL_SHA='+repr(hashlib.sha256(control).hexdigest())+'\nCONTROL_DATA='+repr(base64.b64encode(gzip.compress(control,mtime=0)).decode())+'\n'
code+='ENTRY_SHA='+repr(hashlib.sha256(entry).hexdigest())+'\nENTRY_DATA='+repr(base64.b64encode(gzip.compress(entry,mtime=0)).decode())+'\n'
code+='''import ast,base64,gzip,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
if sys.flags.optimize:raise RuntimeError('Assertions required')
sys.dont_write_bytecode=True
source=Path(sys._getframe().f_code.co_filename).resolve();digest=hashlib.sha256(source.read_bytes()).hexdigest()
root=Path('/home/root/aura-release-acceptance-20261023')/digest[:16]
root.mkdir(parents=True,exist_ok=True,mode=0o700);assert root.resolve()==root
raw=gzip.decompress(base64.b64decode(CONTROL_DATA));assert hashlib.sha256(raw).hexdigest()==CONTROL_SHA
entry=gzip.decompress(base64.b64decode(ENTRY_DATA));assert hashlib.sha256(entry).hexdigest()==ENTRY_SHA
ast.parse(entry.decode())
path=root/'release_control.py';assert not path.is_symlink()
if path.exists():assert path.read_bytes()==raw
else:
 with path.open('xb') as f:f.write(raw)
if len(sys.argv)>1 and sys.argv[1]=='--run':
 spec=importlib.util.spec_from_file_location('_owned_qualified_release_control',path)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 print(json.dumps(module.run_release(root,source,entry)))
else:
 assert not (root/'report.json').exists(),'Do not overwrite earlier activation evidence'
 unit='aura-qualified-recovery50-release-'+digest[:16]
 value=subprocess.run(['systemd-run','--unit='+unit,'--property=RuntimeMaxSec=720',
  '/usr/bin/python3','-B',str(source),'--run'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10)
 assert value.returncode==0,value.stdout.decode(errors='replace')[-400:]
 print(json.dumps({'started':True,'unit':unit,'report':str(root/'report.json'),'helper_sha256':digest}))
'''
ast.parse(code)
target=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_activate_qualified_recovery50_r2_20261023.py')
assert not target.exists();target.write_text(code)
result={'helper':str(target),'sha256':hashlib.sha256(code.encode()).hexdigest(),
        'control_sha256':hashlib.sha256(control).hexdigest(),'runtime_entry_sha256':hashlib.sha256(entry).hexdigest(),
        'requires_completed_qualified_1800s':True,'activation_observation_s':120,
        'runtime_max_s':720,'independent_restore_s':900,'default_action_on_failure':'restore_original',
        'executed':False,'qualification_tests':10,'runtime_entry_tests':4}
(ROOT/'activation-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
