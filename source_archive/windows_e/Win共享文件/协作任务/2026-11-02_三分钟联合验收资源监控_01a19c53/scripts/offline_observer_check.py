"""Exercise the observer on Ubuntu with all application HTTP calls stubbed out."""
from pathlib import Path
import runpy,sys,io,contextlib,json,hashlib
source=Path(__file__).with_name('board_monitor.py')
module=runpy.run_path(str(source),run_name='offline_observer_module')
calls=[]
def no_network(port,path):
    calls.append([port,path]);return {'ok':False,'request_ms':0,'error_type':'OfflineSelfTestNoNetwork'}
module['main'].__globals__['get']=no_network
sys.argv=[str(source),'--duration','10']
buffer=io.StringIO()
with contextlib.redirect_stdout(buffer):module['main']()
rows=[json.loads(x) for x in buffer.getvalue().splitlines()]
samples=[r for r in rows if r.get('event')=='sample']
assert len(samples)==5 and rows[-1]['event']=='end'
assert all(0<=x<=100 for r in samples for x in r['cpu'].values() if x is not None)
assert all(r['memory_kib']['MemTotal']>0 for r in samples)
assert all(r['camera']['error_type']=='OfflineSelfTestNoNetwork' for r in samples)
result={'status':'PASS_UBUNTU_OFFLINE_OBSERVER_CHECK','script_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'samples_checked':len(samples),'network_calls':0,'application_calls_stubbed':len(calls),'kv260_accessed':False,'acceptance_data_created':False,'scope':'Runtime exercise of observer core on development Ubuntu only; not a board performance result'}
Path(__file__).with_name('OFFLINE_OBSERVER_CHECK.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
