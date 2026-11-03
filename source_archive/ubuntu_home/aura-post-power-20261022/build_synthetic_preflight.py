"""Package the isolated no-device observer cost check for the current boot."""
import ast
import base64
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
TOOLS=Path('/home/ghmd/aura-offline-validation-20261022')
BOOT='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
names=['prepare_sources.py','evaluate_preflight.py','run_preflight.py','test_evaluator.py',
 'reference/face_targets.py','candidate/aura/board/identity/face_targets.py',
 'candidate/aura/board/identity/face_freshness_metrics.py','tests/test_freshness_metrics.py']
files={name:(TOOLS/name).read_bytes() for name in names}
for name,data in files.items():ast.parse(data.decode(),filename=name)
hashes={name:hashlib.sha256(data).hexdigest() for name,data in files.items()}
encoded=gzip.compress(json.dumps({name:base64.b64encode(data).decode() for name,data in files.items()},
    separators=(',',':')).encode(),mtime=0)
prefix='PAYLOAD='+repr(base64.b64encode(encoded).decode())+'\nHASHES='+repr(hashes)+'\nEXPECTED_BOOT='+repr(BOOT)+'\n'
source=prefix+'''import base64,gzip,hashlib,json,os,subprocess,sys,time,urllib.request
from pathlib import Path
if sys.flags.optimize:raise RuntimeError('assertions required')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==EXPECTED_BOOT
source=Path(sys._getframe().f_code.co_filename).resolve();digest=hashlib.sha256(source.read_bytes()).hexdigest()
root=Path('/home/root/aura-post-power-20261022/synthetic')/digest[:16]
root.mkdir(parents=True,exist_ok=True);work=root/'work';work.mkdir(exist_ok=True)
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def health():
 with op.open('http://127.0.0.1:8790/health',timeout=3) as f:return json.load(f)
def units():
 return {name:subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','NRestarts','-p','ActiveState'],timeout=3).decode().strip() for name in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service')}
before=health();protected=units()
assert not before['camera_error'] and not before['detector_error']
assert before['identity']['face_targets']['backend']=='DPU_YUNET_INT8'
assert not (root/'report.json').exists(),'Do not rerun or overwrite evidence'
payload=json.loads(gzip.decompress(base64.b64decode(PAYLOAD)))
for name,value in payload.items():
 relative=Path(name);assert not relative.is_absolute() and '..' not in relative.parts
 data=base64.b64decode(value);assert hashlib.sha256(data).hexdigest()==HASHES[name]
 target=work/name;target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists():assert target.read_bytes()==data
 else:target.write_bytes(data)
out=subprocess.run(['/usr/bin/python3','-B',str(work/'run_preflight.py'),'--output',str(root/'results')],
 stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60)
result={'scope':'TARGET_BOARD_SYNTHETIC_NO_DEVICE_OBSERVER_PREFLIGHT','helper_sha256':digest,
 'source_sha256':HASHES,'boot':EXPECTED_BOOT,'new_dpu_jobs_created':0,'production_files_modified':False,
 'returncode':out.returncode,'stderr':out.stderr.decode(errors='replace')[-2000:],
 'stdout':out.stdout.decode(errors='replace')[-2000:]}
if (root/'results/report.json').exists():result['benchmark_report']=json.loads((root/'results/report.json').read_text())
if (root/'results/assessment.json').exists():result['assessment']=json.loads((root/'results/assessment.json').read_text())
after=health();result['protected_before']=protected;result['protected_after']=units()
result['camera_before']={'pid':before['pid'],'detected_frames':before['detected_frames']}
result['camera_after']={'pid':after['pid'],'detected_frames':after['detected_frames'],'face_targets':after['identity']['face_targets']}
result['same_camera_advanced']=(before['pid']==after['pid'] and after['detected_frames']>before['detected_frames'])
result['passed']=bool(out.returncode==0 and result.get('assessment',{}).get('passed')
 and result['same_camera_advanced'] and result['protected_before']==result['protected_after'])
(root/'report.json').write_text(json.dumps(result,indent=2)+'\\n')
raw=json.dumps(result,separators=(',',':')).encode()
print(json.dumps({'root':str(root),'passed':result['passed'],'decoded_bytes':len(raw),
 'gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode()}))
'''
ast.parse(source)
previous=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_postpower_synthetic_20261022.py')
previous_sha=hashlib.sha256(previous.read_bytes()).hexdigest()
assert previous_sha=='fae37bfe9b09507799ab4122106c5e8ea6704df7edbf7aae66b84261e45f5ef7'
previous_tree=ast.parse(previous.read_text())
previous_constants={node.targets[0].id:ast.literal_eval(node.value) for node in previous_tree.body
    if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name)
    and node.targets[0].id in ('PAYLOAD','HASHES','EXPECTED_BOOT')}
previous_payload=json.loads(gzip.decompress(base64.b64decode(previous_constants['PAYLOAD'])))
changed={name:base64.b64encode(gzip.compress(data,mtime=0)).decode() for name,data in files.items()
    if hashes[name]!=previous_constants['HASHES'][name]}
assert set(changed)=={'run_preflight.py'}
source='''import ast,base64,gzip,hashlib,json,sys
from pathlib import Path
p=Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/helpers/fae37bfe9b095077/source.py')
raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()=='fae37bfe9b09507799ab4122106c5e8ea6704df7edbf7aae66b84261e45f5ef7'
tree=ast.parse(raw)
constants={node.targets[0].id:ast.literal_eval(node.value) for node in tree.body
 if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name)
 and node.targets[0].id in ('PAYLOAD','HASHES','EXPECTED_BOOT')}
payload=json.loads(gzip.decompress(base64.b64decode(constants['PAYLOAD'])))
for name,value in REPLACEMENTS.items():
 data=gzip.decompress(base64.b64decode(value));payload[name]=base64.b64encode(data).decode()
 constants['HASHES'][name]=hashlib.sha256(data).hexdigest()
constants['PAYLOAD']=base64.b64encode(gzip.compress(json.dumps(payload,separators=(',',':')).encode(),mtime=0)).decode()
body=[node for node in tree.body if not(isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name)
 and node.targets[0].id in ('PAYLOAD','HASHES','EXPECTED_BOOT'))]
globals().update(constants)
current=Path(sys._getframe().f_code.co_filename).resolve()
exec(compile(ast.Module(body=body,type_ignores=[]),str(current),'exec'),globals())
'''
source='REPLACEMENTS='+repr(changed)+'\n'+source
ast.parse(source)
target=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_postpower_synthetic_r2_20261022.py')
if target.exists():assert target.read_text()==source
else:target.write_text(source)
manifest={'helper':str(target),'sha256':hashlib.sha256(source.encode()).hexdigest(),
 'expected_boot':BOOT,'files':hashes,'scope':'no device opens or additional native inference; existing camera remains active'}
(ROOT/'synthetic-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest))
