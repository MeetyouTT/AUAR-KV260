"""Check final service identity within its original startup budget."""
import argparse,datetime,json,time,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--output',default='final_ready.json');args=parser.parse_args()
assert '/' not in args.output and '\\' not in args.output
assert not (H/args.output).exists(),'Keep previous startup failure evidence'
manifest=json.loads((H/'final_manifest.json').read_text(encoding='utf-8'))
record=json.loads((H/'service_processes.json').read_text(encoding='utf-8-sig'))['8792']
creation=datetime.datetime.fromisoformat(record['creation_utc'].replace('Z','+00:00'))
until=time.monotonic()+max(0,300-(datetime.datetime.now(datetime.timezone.utc)-creation).total_seconds())
rows=[];last=-30;result=None;start=time.monotonic()
def get(url):
    try:
        with urllib.request.urlopen(url,timeout=2) as r:return json.load(r)
    except OSError:return None
while time.monotonic()<until:
    v=get('http://192.168.50.1:8792/health');h=get('http://127.0.0.1:8812/health')
    row=dict(at=round(time.monotonic()-start,2),voice_ready=bool(v and v.get('ready')),
        hub_ready=bool(h and h.get('speaker_ready')),binding_ready=bool(h and h.get('anonymous_binding',{}).get('enabled')))
    rows.append(row)
    if row['at']-last>=20:print(json.dumps(row),flush=True);last=row['at']
    if all(row[k] for k in ('voice_ready','hub_ready','binding_ready')):
        assert v['source_fingerprint']==manifest['fingerprint'] and v['service_revision']==manifest['revision']
        assert v['gpu_coordination']['mode']=='adaptive' and v['gpu_coordination']['enforcing']
        assert v['cold_startup']['capacity_verified'] and v['cold_startup']['automatic_unload'] is False
        result=dict(status='READY',voice=v,hub=h,rows=rows,startup_age_seconds=(datetime.datetime.now(datetime.timezone.utc)-creation).total_seconds());break
    time.sleep(1)
if result is None:result=dict(status='NOT_READY_WITHIN_ORIGINAL_BUDGET',rows=rows)
result['checked_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
path=H/args.output;path.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('status','checked_utc')}|{'startup_age_seconds':result.get('startup_age_seconds')}),flush=True)
raise SystemExit(0 if result['status']=='READY' else 1)
