import hashlib,json,tarfile
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='f7a3ff07-fc20-4804-af12-c314a7a1847a'
root=Path('/home/root/aura-adaptation-20261006/vsrv-source-14da0e60')
archive=root/'bench.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='bade19579a64430bdb2cf897d28c02640c3920381d059826ba11340336a3ebe9'
dest=root/'unpacked';dest.mkdir(exist_ok=False)
with tarfile.open(archive,'r:gz') as t:
 entries=t.getmembers();assert len(entries)==len({e.name for e in entries})==9
 for e in entries:
  assert e.isfile() and Path(e.name).name==e.name
  with (dest/e.name).open('xb') as f:f.write(t.extractfile(e).read())
m=json.loads((dest/'payload_manifest.json').read_text())
for n,d in m['payload_files'].items():assert hashlib.sha256((dest/n).read_bytes()).hexdigest()==d
print(json.dumps({'passed':True,'unpacked':str(dest),'files':len(entries),'motion_emitted':False}))
