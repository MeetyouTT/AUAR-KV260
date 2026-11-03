import base64,gzip,hashlib,json,subprocess
from pathlib import Path
names=['/usr/include/vart/runner.hpp','/usr/include/vart/tensor_buffer.hpp',
 '/usr/include/vart/runner_ext.hpp','/usr/include/xir/graph/graph.hpp',
 '/usr/include/xir/graph/subgraph.hpp','/usr/include/xir/tensor/tensor.hpp',
 '/usr/include/xir/util/data_type.hpp']
out={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'headers':{},'libraries':{}}
for name in names:
 p=Path(name)
 if p.is_file():
  b=p.read_bytes();out['headers'][name]={'sha256':hashlib.sha256(b).hexdigest(),'text':b.decode()}
for pattern in ('libvart-runner.so*','libxir.so*','libvitis_ai_library-yolovx.so*','libvart-util.so*'):
 for p in Path('/usr/lib').glob(pattern):
  if p.is_file():out['libraries'][str(p)]={'target':str(p.resolve()),'bytes':p.stat().st_size}
raw=json.dumps(out,separators=(',',':')).encode()
print(json.dumps({'sha256':hashlib.sha256(raw).hexdigest(),'gzip_b64':base64.b64encode(gzip.compress(raw,mtime=0)).decode()}))
