import hashlib,json,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283')
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
m=u['manual_pan'];assert m['automatic_following']
p=Path(m['face_follow']['report']);assert 'continuous-v10r7/runs/' in str(p)
s=json.loads((R/'state.json').read_text());assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
began=time.monotonic();samples=[];first=None;last=None
while time.monotonic()-began<25:
 r=json.loads(p.read_text());x=r['result'];assert r['boot_id']==s['boot']
 assert r['consumer_manifest_sha256']==s['physical_consumer_sha256']
 if first is None:first=r
 last=r
 samples.append(dict(elapsed_s=round(time.monotonic()-began,2),state=x['state'],reason=x['reason'],
  pulse_us=x['pulse_us'],commands=x['commands_accepted'],motion_changes=x['motion_target_changes'],
  segments=x['segments'],fatal=x['fatal'],input_summary=r.get('input_summary'),latest_face=r.get('observation_trace',[])[-1:]))
 if r['status']!='CONTINUOUS_FACE_ZONE_RUNNING' or x['fatal']:break
 time.sleep(.5)
out={'status':last['status'],'window_s':round(time.monotonic()-began,3),'report':str(p),
 'report_sha256_at_end':hashlib.sha256(p.read_bytes()).hexdigest(),'samples':samples,
 'delta_commands':last['result']['commands_accepted']-first['result']['commands_accepted'],
 'delta_motion_changes':last['result']['motion_target_changes']-first['result']['motion_target_changes'],
 'delta_segments':last['result']['segments']-first['result']['segments'],'motor_commands_sent_by_observer':0}
(R/'r7-user-observation-25s.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out))
