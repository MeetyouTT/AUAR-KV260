"""Bounded read-only UART chunks; the ELF stays in the private workspace."""
import base64,gzip,hashlib,json,subprocess,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROBES=Path('/home/ghmd/aura-model-inventory-20261021')
metadata=json.loads((HERE/'event-5788-raw.json').read_text())
out=bytearray();chunk_size=8192;proof=[]
for index,offset in enumerate(range(0,metadata['compressed_size'],chunk_size)):
    script=PROBES/('native_vart_part_'+str(index)+'.py')
    source="""import base64,hashlib,json
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7924ac9f-311d-4fcd-98be-57bf023cf1aa'
with Path(CACHE).open('rb') as f:
 f.seek(OFFSET);raw=f.read(8192)
print(json.dumps({'offset':OFFSET,'data':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}))
""".replace('CACHE',repr(metadata['remote_cache'])).replace('OFFSET',str(offset))
    if script.exists():assert script.read_text()==source
    else:script.write_text(source)
    passed=False
    for attempt in range(2):
        with (HERE/('elf-part-'+str(index)+'-'+str(attempt)+'.private.log')).open('w') as stream:
            result=subprocess.run([sys.executable,str(PROBES/'run_probe.py'),script.name],stdout=stream,stderr=subprocess.STDOUT,timeout=40)
        status=json.loads(script.with_suffix('.status.json').read_text())
        if result.returncode==0 and status.get('exit_code')==0 and status.get('console_echo_restored'):
            row=json.loads(script.with_suffix('.response.json').read_text());data=base64.b64decode(row['data'])
            assert row['offset']==offset and hashlib.sha256(data).hexdigest()==row['sha256']
            assert len(data)==min(chunk_size,metadata['compressed_size']-offset)
            out.extend(data);proof.append({'offset':offset,'bytes':len(data),'sha256':row['sha256'],'attempt':attempt});passed=True;break
    assert passed,'Chunk failed: '+str(index)
assert hashlib.sha256(out).hexdigest()==metadata['compressed_sha256']
raw=gzip.decompress(out)
assert len(raw)==metadata['vart_size'] and hashlib.sha256(raw).hexdigest()==metadata['vart_sha256']
folder=HERE/'exact-runtime';folder.mkdir(exist_ok=True)
target=folder/'vart.so'
if target.exists():assert target.read_bytes()==raw
else:target.write_bytes(raw)
(folder/'download-proof.json').write_text(json.dumps({'sha256':metadata['vart_sha256'],'bytes':len(raw),'chunks':proof,'boot':'7924ac9f-311d-4fcd-98be-57bf023cf1aa','private_analysis_only':True},indent=2)+'\n')
print(json.dumps({'downloaded':True,'sha256':metadata['vart_sha256'],'bytes':len(raw),'chunks':len(proof),'path':str(target)}))
