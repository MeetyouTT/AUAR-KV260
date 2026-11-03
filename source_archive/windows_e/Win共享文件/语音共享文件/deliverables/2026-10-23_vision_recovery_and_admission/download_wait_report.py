"""Hash-checked numeric report download in serial chunks, with no parallel UART."""
import base64,gzip,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PROBES=Path('/home/ghmd/aura-model-inventory-20261021')
meta=json.loads((ROOT/'wait-sched-metadata.json').read_text());assert meta['complete']
output=bytearray();proof=[]
for index,offset in enumerate(range(0,meta['compressed_bytes'],16384)):
    p=PROBES/('wait_report_chunk_'+str(index)+'.py')
    p.write_text("import base64,hashlib,json\nfrom pathlib import Path\nassert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='008f3e1b-c627-4b98-b120-d2a460cdbcbe'\nwith Path("+repr(meta['cache'])+").open('rb') as f:\n f.seek("+str(offset)+");b=f.read(16384)\nprint(json.dumps({'offset':"+str(offset)+",'data':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}))\n")
    with (ROOT/('wait-report-chunk-'+str(index)+'.private.log')).open('w') as stream:
        done=subprocess.run([sys.executable,str(PROBES/'run_probe.py'),p.name],stdout=stream,stderr=subprocess.STDOUT,timeout=40)
    status=json.loads(p.with_suffix('.status.json').read_text());assert done.returncode==0 and status['exit_code']==0 and status['console_echo_restored']
    row=json.loads(p.with_suffix('.response.json').read_text());b=base64.b64decode(row['data'])
    assert row['offset']==offset and hashlib.sha256(b).hexdigest()==row['sha256'];output.extend(b)
    proof.append({'offset':offset,'bytes':len(b),'sha256':row['sha256']})
assert hashlib.sha256(output).hexdigest()==meta['compressed_sha256']
raw=gzip.decompress(output);assert hashlib.sha256(raw).hexdigest()==meta['raw_sha256']
(ROOT/'wait-sched-result.json').write_text(json.dumps({'report':json.loads(raw),'readback_proof':proof},indent=2)+'\n')
print(json.dumps({'downloaded':True,'bytes':len(raw),'chunks':len(proof)}))
