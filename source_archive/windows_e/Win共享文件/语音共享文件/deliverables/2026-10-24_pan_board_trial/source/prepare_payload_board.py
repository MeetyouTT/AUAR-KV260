"""Prepare and verify private candidate files only; never install or load PL."""
import gzip,hashlib,json,os,sys
from pathlib import Path
sys.dont_write_bytecode=True
os.nice(15)
ROOT=Path(__file__).resolve().parent
meta=json.loads((ROOT/'payload.json').read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==meta['baseline']['boot_id']
assert sha('/sys/firmware/fdt')==meta['baseline']['fdt_sha256']
for name,pin in meta['files'].items():assert sha(ROOT/name)==pin,name
sys.path.insert(0,str(ROOT));from delta_codec import apply_delta
manifest=json.loads((ROOT/'candidate-manifest.json').read_text())
assert sha(ROOT/'candidate-manifest.json')==meta['candidate_manifest_sha256']
patch=json.loads(gzip.decompress((ROOT/'firmware-delta.json.gz').read_bytes()))
target=ROOT/'runtime'/meta['app']/(meta['app']+'.bit.bin')
expected=manifest['runtime_files']['/lib/firmware/xilinx/'+meta['app']+'/'+target.name]
raw=apply_delta(Path(meta['delta_base']).read_bytes(),patch,expected)
if target.exists():assert sha(target)==expected
else:
    with target.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
for path,pin in manifest['runtime_files'].items():assert sha(ROOT/'runtime'/meta['app']/Path(path).name)==pin,path
for name,pin in manifest['payload_files'].items():assert sha(ROOT/'driver'/name)==pin,name
result={'prepared':True,'root':str(ROOT),'boot_id':meta['baseline']['boot_id'],
 'reconstructed_bitstream_sha256':expected,'bitstream_bytes':len(raw),
 'firmware_installed':False,'firmware_loaded':False,'mmio_opened':False,'motion_commands_sent':0}
with (ROOT/'prepared.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
