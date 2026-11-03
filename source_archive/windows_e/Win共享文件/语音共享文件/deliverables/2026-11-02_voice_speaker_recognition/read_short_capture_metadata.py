"""Read numeric length/route diagnostics only; no transcript, audio or names."""
import hashlib
import http.client
import json
from pathlib import Path
import time

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='a6d4a069-e9b0-4065-8df7-dc23556b168e'
p=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='7d60ab0f83fc2484f59e065b720cec73cdb2dbe051cb34e366c08ebcbc8e785e'
c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
try:
    c.request('GET','/api/state');r=c.getresponse();assert r.status==200;v=json.loads(r.read(2097152))
finally:c.close()
b=v.get('board_business') or {};d=b.get('dialogue') or {};route=d.get('last_voice_route') or {};trace=route.get('entry_route_trace') or route.get('entry_trace') or {};rec=v.get('local_recording') or {};speaker=b.get('speaker') or {};af=(v.get('audio_frontend') or {}).get('current') or {}
def numeric(x):return {k:z for k,z in x.items() if type(z) in (int,float,bool) and not any(t in k.lower() for t in ('score','probability','sample_value'))}
print(json.dumps({'schema':'aura-short-capture-readonly-numeric-diagnostics-1','mono_ms':int(time.monotonic()*1000),'route_keys':sorted(route),'last_route_numeric':numeric(route),'route_trace_numeric':numeric(trace),'recording_numeric':numeric(rec),'recording_state':rec.get('state'),'frontend_cache_numeric':numeric(af),'address':speaker.get('conversation_address'),'speaker_counts':{k:speaker.get(k) for k in ('submitted','complete','unavailable','evidence_errors')},'handsfree':{k:(v.get('handsfree_dialogue') or {}).get(k) for k in ('state','enabled','microphone_open')},'control_writes':0}))
