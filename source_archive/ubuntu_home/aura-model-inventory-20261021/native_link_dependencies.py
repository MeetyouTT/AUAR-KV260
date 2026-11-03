import hashlib,json,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='008f3e1b-c627-4b98-b120-d2a460cdbcbe'
files={}
for name in ['libvart-runner.so','libxir.so','libunilog.so','libstdc++.so.6','libc.so.6']:
 candidates=[Path('/usr/lib')/name,Path('/usr/lib/aarch64-linux-gnu')/name,Path('/lib/aarch64-linux-gnu')/name]
 selected=next((p.resolve() for p in candidates if p.exists()),None)
 if selected is None:files[name]={'missing':True};continue
 files[name]={'path':str(selected),'sha256':hashlib.sha256(selected.read_bytes()).hexdigest(),
              'bytes':selected.stat().st_size}
print(json.dumps({'scope':'read-only link dependency metadata; no ELF data copied/loaded',
 'files':files,'compiler':subprocess.check_output(['g++','--version'],text=True).splitlines()[0]}))
