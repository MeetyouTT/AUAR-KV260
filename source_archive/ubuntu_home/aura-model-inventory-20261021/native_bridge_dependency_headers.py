import base64,gzip,hashlib,json,re
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
base=Path('/usr/include');allowed={'vart','xir','UniLog','glog','gflags'}
files={};missing=set()
def visit(path):
 path=Path(path)
 if not path.is_relative_to(base) or path.relative_to(base).parts[0] not in allowed:return
 name=str(path.relative_to(base))
 if name in files:return
 if not path.is_file():missing.add(name);return
 raw=path.read_bytes();assert len(raw)<1000000
 files[name]={'sha256':hashlib.sha256(raw).hexdigest(),'data':base64.b64encode(raw).decode()}
 for target in re.findall(rb'^\s*#\s*include\s*[<"]([^>"\n]+)',raw,re.M):
  name=target.decode()
  if name.split('/')[0] in allowed:visit(base/name)
  elif (path.parent/name).is_file():visit(path.parent/name)
for name in ['vart/runner.hpp','vart/tensor_buffer.hpp','xir/graph/graph.hpp','xir/graph/subgraph.hpp','xir/tensor/tensor.hpp']:
 visit(base/name)
raw=json.dumps(files,separators=(',',':'),sort_keys=True).encode();assert len(raw)<4000000
compressed=gzip.compress(raw,mtime=0);assert len(compressed)<150000
print(json.dumps({'scope':'read-only installed C++ dependency headers; no model, owner or device calls',
 'sha256':hashlib.sha256(raw).hexdigest(),'gzip_base64':base64.b64encode(compressed).decode(),
 'count':len(files),'missing':sorted(missing)}))
