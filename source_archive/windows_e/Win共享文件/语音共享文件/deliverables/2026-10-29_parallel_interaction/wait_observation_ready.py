"""Bounded startup observation; never generates another model request."""
import argparse,datetime,json,sys,time,urllib.request
from pathlib import Path
H=Path(__file__).resolve().parent;A=H.parents[1]/'aura';sys.path.insert(0,str(A))
from common.gpu_coordination import NvidiaMemoryProbe
expected=json.loads((H/'observation_installation.json').read_text(encoding='utf-8'))['fingerprint']
parser=argparse.ArgumentParser();parser.add_argument('--output',default='observation_ready.json');args=parser.parse_args()
assert '/' not in args.output and '\\' not in args.output
assert not (H/args.output).exists(),'Preserve prior startup evidence'
probe=NvidiaMemoryProbe();rows=[];started=time.monotonic();last_print=-30;value=None
def get(url):
    try:
        with urllib.request.urlopen(url,timeout=2) as r:return json.load(r)
    except OSError:return None
creation=json.loads((H/'service_processes.json').read_text(encoding='utf-8-sig'))['8792']['creation_utc']
launch_utc=datetime.datetime.fromisoformat(creation.replace('Z','+00:00'))
elapsed=max(0,(datetime.datetime.now(datetime.timezone.utc)-launch_utc).total_seconds())
deadline=started+max(0,300-elapsed)
while time.monotonic()<deadline:
    voice=get('http://192.168.50.1:8792/health');hub=get('http://127.0.0.1:8812/health')
    resident=get('http://127.0.0.1:11435/api/ps')
    try:memory=probe.read().public(time.monotonic())
    except Exception:memory=probe.public()
    row=dict(at=round(time.monotonic()-started,2),voice_ready=bool(voice and voice.get('ready')),
      hub_ready=bool(hub and hub.get('speaker_ready')),memory=memory,
      llm_resident=[{k:v for k,v in item.items() if k in ('name','size_vram','context_length')} for item in (resident or {}).get('models',[])])
    rows.append(row)
    if row['at']-last_print>=20:
        print(json.dumps({k:v for k,v in row.items() if k!='memory'}|{'free_mib':memory.get('free_mib')}),flush=True);last_print=row['at']
    if row['voice_ready'] and row['hub_ready']:
        assert voice['source_fingerprint']==expected
        value=dict(status='READY_FOR_CALIBRATION_NOT_FINAL',voice_health=voice,hub_health=hub,rows=rows,
          peak_device_used_mib=max(r['memory'].get('used_mib',0) for r in rows),observed_seconds=row['at'])
        break
    time.sleep(1)
if value is None:value=dict(status='STARTUP_NOT_READY',rows=rows)
value['checked_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(H/args.output).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in value.items() if k not in ('rows','voice_health','hub_health')}),flush=True)
raise SystemExit(0 if value['status']=='READY_FOR_CALIBRATION_NOT_FINAL' else 1)
