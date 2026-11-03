"""Package the gap-only recorder cost check as a standalone pinned helper."""
import ast,base64,gzip,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
TOOLS=Path('/home/ghmd/aura-gap3-validation-20261023')
previous=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_postpower_synthetic_20261022.py')
raw=previous.read_text()
assert hashlib.sha256(raw.encode()).hexdigest()=='fae37bfe9b09507799ab4122106c5e8ea6704df7edbf7aae66b84261e45f5ef7'
tree=ast.parse(raw)
end=max(n.end_lineno for n in tree.body if isinstance(n,ast.Assign)
        and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('PAYLOAD','HASHES','EXPECTED_BOOT'))
body='\n'.join(raw.splitlines()[end:])+'\n'
body=body.replace("/home/root/aura-post-power-20261022/synthetic", "/home/root/aura-post-power-20261022/gap3-preflight")
names=['prepare_sources.py','evaluate_preflight.py','run_preflight.py','test_evaluator.py',
       'reference/face_targets.py','candidate/aura/board/identity/face_targets.py',
       'candidate/aura/board/identity/face_freshness_metrics.py',
       'candidate/aura/board/vision/dpu_vision_runtime.py','candidate/aura/board/vision/dpu_yunet.py',
       'tests/test_light.py','tests/test_service.py']
files={name:(TOOLS/name).read_bytes() for name in names}
hashes={name:hashlib.sha256(value).hexdigest() for name,value in files.items()}
data=json.dumps({name:base64.b64encode(value).decode() for name,value in files.items()},separators=(',',':')).encode()
prefix='PAYLOAD='+repr(base64.b64encode(gzip.compress(data,mtime=0)).decode())+'\nHASHES='+repr(hashes)+'\nEXPECTED_BOOT='+repr('7924ac9f-311d-4fcd-98be-57bf023cf1aa')+'\n'
source=prefix+body
ast.parse(source)
target=Path('/home/ghmd/aura-identity-dpu-check-20261018/board_gap3_preflight_20261023.py')
assert not target.exists()
target.write_text(source)
result={'helper':str(target),'sha256':hashlib.sha256(source.encode()).hexdigest(),
        'pins':hashes,'functional_tests':35,'full_gap_records':32,'new_dpu_jobs':0,'mean_added_limit_ms':.5}
(ROOT/'gap3-preflight-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='pins'}))
