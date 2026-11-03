"""Reuse the original isolated preflight body with pinned lightweight inputs."""
import ast
import base64
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
TOOLS=Path('/home/ghmd/aura-freshness-light-validation-20261022')
previous=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_postpower_synthetic_20261022.py')
assert hashlib.sha256(previous.read_bytes()).hexdigest()=='fae37bfe9b09507799ab4122106c5e8ea6704df7edbf7aae66b84261e45f5ef7'
tree=ast.parse(previous.read_text())
old={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
    and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('PAYLOAD','HASHES')}
oldfiles=json.loads(gzip.decompress(base64.b64decode(old['PAYLOAD'])))
names=['prepare_sources.py','evaluate_preflight.py','run_preflight.py','test_evaluator.py',
 'reference/face_targets.py','candidate/aura/board/identity/face_targets.py',
 'candidate/aura/board/identity/face_freshness_metrics.py','tests/test_light.py','tests/test_service.py']
files={name:(TOOLS/name).read_bytes() for name in names}
hashes={name:hashlib.sha256(data).hexdigest() for name,data in files.items()}
for name,data in files.items():ast.parse(data.decode(),filename=name)
keep=[name for name in names if name in oldfiles and base64.b64decode(oldfiles[name])==files[name]]
replacement={name:base64.b64encode(gzip.compress(data,mtime=0)).decode() for name,data in files.items() if name not in keep}
source='KEEP='+repr(keep)+'\nREPLACEMENTS='+repr(replacement)+'\n'
source+='''import ast,base64,gzip,hashlib,json,sys
from pathlib import Path
p=Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/helpers/fae37bfe9b095077/source.py')
raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()=='fae37bfe9b09507799ab4122106c5e8ea6704df7edbf7aae66b84261e45f5ef7'
tree=ast.parse(raw)
constants={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('PAYLOAD','HASHES','EXPECTED_BOOT')}
old=json.loads(gzip.decompress(base64.b64decode(constants['PAYLOAD'])))
payload={name:old[name] for name in KEEP}
for name,value in REPLACEMENTS.items():payload[name]=base64.b64encode(gzip.decompress(base64.b64decode(value))).decode()
constants['HASHES']={name:hashlib.sha256(base64.b64decode(data)).hexdigest() for name,data in payload.items()}
constants['PAYLOAD']=base64.b64encode(gzip.compress(json.dumps(payload,separators=(',',':')).encode(),mtime=0)).decode()
body=[n for n in tree.body if not(isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name)
 and n.targets[0].id in ('PAYLOAD','HASHES','EXPECTED_BOOT'))]
globals().update(constants)
source=Path(sys._getframe().f_code.co_filename).resolve()
exec(compile(ast.Module(body=body,type_ignores=[]),str(source),'exec'),globals())
'''
ast.parse(source)
target=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_postpower_light_preflight_20261022.py')
if target.exists():assert target.read_text()==source
else:target.write_text(source)
result={'helper':str(target),'sha256':hashlib.sha256(source.encode()).hexdigest(),'sources':hashes,
 'boot':'7924ac9f-311d-4fcd-98be-57bf023cf1aa','expected_functional_tests':32,
 'new_native_jobs':0,'mean_added_limit_ms':.5}
(ROOT/'light-preflight-manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
