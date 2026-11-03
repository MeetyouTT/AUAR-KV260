"""Read one private gzip trace serially, verify, parse on host to numeric evidence."""
import ast,base64,gzip,hashlib,json,re,subprocess,sys
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parent;PROBES=Path('/home/ghmd/aura-model-inventory-20261021')
report_path=Path(sys.argv[1]);source=Path(sys.argv[2]);tag=sys.argv[3]
report=json.loads(report_path.read_text());assert report['complete'] and report.get('raw_trace')
assert hashlib.sha256(source.read_bytes()).hexdigest()==report['source_sha256']
meta=report['raw_trace'];chunks=[];proof=[]
for index,offset in enumerate(range(0,meta['compressed_bytes'],32768)):
    p=PROBES/(tag+'_chunk_'+str(index)+'.py')
    p.write_text("import base64,hashlib,json\nfrom pathlib import Path\nassert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='008f3e1b-c627-4b98-b120-d2a460cdbcbe'\nwith Path("+repr(meta['path'])+").open('rb') as f:\n f.seek("+str(offset)+");b=f.read(32768)\nprint(json.dumps({'offset':"+str(offset)+",'data':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}))\n")
    with (ROOT/(tag+'-chunk-'+str(index)+'.private.log')).open('w') as stream:
        done=subprocess.run([sys.executable,str(PROBES/'run_probe.py'),p.name],stdout=stream,stderr=subprocess.STDOUT,timeout=40)
    status=json.loads(p.with_suffix('.status.json').read_text());assert done.returncode==0 and status['exit_code']==0 and status['console_echo_restored']
    row=json.loads(p.with_suffix('.response.json').read_text());raw=base64.b64decode(row['data'])
    assert row['offset']==offset and hashlib.sha256(raw).hexdigest()==row['sha256'];chunks.append(raw)
    proof.append({'offset':offset,'bytes':len(raw),'sha256':row['sha256']})
blob=b''.join(chunks);assert hashlib.sha256(blob).hexdigest()==meta['compressed_sha256']
raw=gzip.decompress(blob);assert hashlib.sha256(raw).hexdigest()==meta['sha256']
(ROOT/(tag+'.private.trace.txt')).write_bytes(raw)
tree=ast.parse(source.read_text());functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('parse','parse_switches')]
env={'re':re,'h':SimpleNamespace(GROUP=report['trace_group'],NAMES=tuple(report['phase_names']))}
exec(compile(ast.fix_missing_locations(ast.Module(body=functions,type_ignores=[])),'verified-host-parser','exec'),env)
numeric=env['parse'](raw.decode(),set(report['record_tids']));numeric.update(env['parse_switches'](raw.decode(),report['target_tid']))
result=dict(report,**numeric)
result['host_measurement_passed']=bool(numeric['cycles']) and report['collection_passed']
result['host_parse_scope']='Original board measurement_passed=false meant unparsed; host evidence is separate and does not turn cost-gate failures into passes'
(ROOT/(tag+'-result.json')).write_text(json.dumps({'report':result,'readback_proof':proof},indent=2)+'\n')
print(json.dumps({'cycles':len(numeric['cycles']),'intervals':len(numeric['off_cpu_intervals']),'compressed_bytes':len(blob),'tag':tag,'host_measurement_passed':result['host_measurement_passed']}))
