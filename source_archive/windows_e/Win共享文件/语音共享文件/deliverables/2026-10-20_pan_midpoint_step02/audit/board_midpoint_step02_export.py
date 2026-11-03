"""Read one completed midpoint transaction; no hardware commands or retry."""
import base64,gzip,hashlib,json
from pathlib import Path
root=Path('/home/root/aura-pan-follow-20261020/midpoint-step-02')
value={'transaction':str(root),'exists':root.exists(),'artifacts':{}}
for name in ['bench.json','result.json','authorization.json','failure-traceback.txt','midpoint1520_bench.py']:
 path=root/name
 if not path.is_file():continue
 raw=path.read_bytes();data=gzip.compress(raw,mtime=0) if name in ['bench.json','result.json'] else raw
 dest=name+'.gz' if name in ['bench.json','result.json'] else name
 value['artifacts'][dest]={'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}
if (root/'result.json').is_file():
 r=json.loads((root/'result.json').read_text())
 value.update({k:v for k,v in r.items() if k not in ['bench']})
 if 'bench' in r:
  b=r['bench'];value['bench']={k:v for k,v in b.items() if k!='events'}
  value['bench']['commands_accepted']=len(b['events'])
  value['bench']['target_pulses_us']=sorted(set(e['target_us'] for e in b['events']))
  value['bench']['event_elapsed_ms_last']=b['events'][-1]['elapsed_ms'] if b['events'] else None
else:value['status']='RESULT_NOT_YET_WRITTEN_DO_NOT_REEXECUTE'
print(json.dumps(value),flush=True)
