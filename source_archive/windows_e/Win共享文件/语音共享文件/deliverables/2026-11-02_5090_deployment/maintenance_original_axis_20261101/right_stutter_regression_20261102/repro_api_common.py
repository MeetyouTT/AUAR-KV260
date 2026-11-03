import hashlib,http.client,json,time
from pathlib import Path
B=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13');A=B/'runtime/aura';ROOT=Path('/home/root/aura-pan-wide-20261028/control-10282601-left40-right45-stable150-35d5e154')
EXPECTED='c3861fa3d2cbb10fee424804f7b3932eadd576819a2a6290c7ca406d900b9602';MANIFEST='9cd35b967bf9c859ed3f1f4de4dc5dad199e81ddfed845435fc8745a41be0ba9'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def req(kind=None):
 c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
 try:
  if kind:c.request('POST','/api/command',json.dumps({'type':kind}).encode(),{'Origin':'http://127.0.0.1:8783','Host':'127.0.0.1:8783','Content-Type':'application/json'})
  else:c.request('GET','/api/state')
  r=c.getresponse();raw=r.read(2097153);assert r.status==200 and len(raw)<=2097152;return json.loads(raw)
 finally:c.close()
def snap(v):
 p=v.get('manual_pan') or {};f=p.get('face_follow') or {};h=v.get('handsfree_dialogue') or {}
 return {'mono_ms':round(time.monotonic()*1000),'ui_page':v.get('ui_page'),'handsfree':{k:h.get(k) for k in ['enabled','state','microphone_open']},'pan':{k:p.get(k) for k in ['state','automatic_following','pulse_us','target_us','readback','backend_pid']},'face_follow_state':f.get('state'),'report':f.get('report'),'runtime_fault_count':(v.get('runtime_faults') or {}).get('count')}
def read_report(path):
 p=Path(path);p.relative_to(ROOT/'runs');assert p.is_file() and not p.is_symlink() and p.stat().st_size<=8388608
 raw=p.read_bytes();return json.loads(raw),hashlib.sha256(raw).hexdigest()
