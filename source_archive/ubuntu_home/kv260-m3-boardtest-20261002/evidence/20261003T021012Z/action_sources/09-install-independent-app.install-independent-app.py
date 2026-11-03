import hashlib
from pathlib import Path
p=Path('/home/root/kv260-m3-boardtest-20261003T021012Z/baseline/guard_reference.py')
G=p.read_bytes()
assert hashlib.sha256(G).hexdigest()=='99c1fc5c842a026c05531eb637080717e44aaa199220d8ab942fbfe430814a6e','Guard source changed'
exec(compile(G,str(p),'exec'))
WORK=Path('/home/root/kv260-m3-boardtest-20261003T021012Z')
def baseline_hashes():
 p=WORK/'baseline/runtime-hashes.json'
 assert digest(p)=='89be552ca73fbc1d8cf4ff94dd1dd6f2f6b8dc7f5d25ab151ada76a733853c0e','Saved manifest changed'
 for path,expected in json.loads(p.read_text()).items():
  assert digest(path)==expected,'Baseline file changed: '+path
def gate(expected,app):
 guard(expected,app)
 baseline_hashes()
 if app is not None:
  assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
  assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()==app+'.bit.bin'
def capture(label):
 snapshot(label)
 print(label+'_MANAGER_JOURNAL_BEGIN',flush=True)
 r=subprocess.run(['journalctl','-u','dfx-mgrd','--no-pager','-n','200','-o','short-monotonic'])
 print(label+'_MANAGER_JOURNAL_RC '+str(r.returncode),flush=True)
 print(label+'_MANAGER_JOURNAL_END',flush=True)
gate('0991D1B457855C8987936E6','kv260-benchmark-b4096')
stage=WORK/'m3-stage';p=stage/'provenance/runtime_manifest.json'
assert digest(p)=='6b613c84a61c2256a9af2b5e25954869cc0ad71aaefb039e1ca3ffe1c1b4165a'
manifest=json.loads(p.read_text());assert manifest['application']=='kv260-benchmark-b4096-m3' and len(manifest['runtime_files'])==4
target=Path('/lib/firmware/xilinx/kv260-benchmark-b4096-m3');target.mkdir(exist_ok=False)
for item in manifest['runtime_files']:
 rel=Path(item['path']);assert rel.parent==Path('lib/firmware/xilinx/kv260-benchmark-b4096-m3')
 src=stage/rel;assert src.is_file() and not src.is_symlink() and digest(src)==item['sha256']
 with (target/rel.name).open('xb') as out:out.write(src.read_bytes())
 assert digest(target/rel.name)==item['sha256']
 print('INSTALLED_HASH '+json.dumps({'path':str(target/rel.name),'sha256':item['sha256']}),flush=True)
text=subprocess.check_output(['dfx-mgr-client','-listPackage'],text=True);print(text,flush=True)
assert any(line.split() and line.split()[0]=='kv260-benchmark-b4096-m3' for line in text.splitlines()),'M3 package not registered'
gate('0991D1B457855C8987936E6','kv260-benchmark-b4096')
