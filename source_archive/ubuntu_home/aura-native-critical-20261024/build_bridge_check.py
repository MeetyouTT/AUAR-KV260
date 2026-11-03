"""Build the native lease isolation check on KV260, without loading the library or submitting model jobs."""
import ast,base64,gzip,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
files={}
for name in ('native_lease.hpp','test_native_lease.cpp','tensor_layout.hpp','test_tensor_layout.cpp','native_bridge.h','native_bridge.cpp'):
    raw=(ROOT/name).read_bytes();files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
data=json.dumps(files,sort_keys=True,separators=(',',':')).encode()
body=(ROOT/'board_compile_worker.py').read_text()

out=ROOT/'board_bridge_check.py'
out.write_text('PAYLOAD='+repr(base64.b64encode(gzip.compress(data,mtime=0)).decode())+'\nPAYLOAD_SHA='+repr(hashlib.sha256(data).hexdigest())+'\n'+body)
ast.parse(out.read_text())
(ROOT/'board-bridge-manifest.json').write_text(json.dumps({'helper_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'files':{k:v['sha256'] for k,v in files.items()},'real_dpu_jobs_submitted':0},indent=2)+'\n')
print(out.stat().st_size)
