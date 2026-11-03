import hashlib,json,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283')
e=R/'r12-v16-supervised-38307025192991.json'
d=json.loads(e.read_text());p=Path(d['report']);r=json.loads(p.read_text())
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:m=json.load(f)['manual_pan']
assert not m['automatic_following'] and m['state']=='READY'
assert m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
assert r['status']=='CONTINUOUS_FACE_ZONE_STOPPED' and not r['result']['fatal']
assert r['result']['stopped']==m['readback']
s=json.loads((R/'state.json').read_text())
assert s['boot']==r['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
s.update(phase='R12_SOURCE_V16_SUPERVISED_STOPPED',automatic_following=False,
 latest_supervised_trial=str(e),latest_supervised_report=str(p))
t=R/'state.json.supervised-complete';t.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n');t.replace(R/'state.json')
print(json.dumps({'status':'VERIFIED_STOPPED_REPORT_CAPTURED','report':str(p),
 'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'final_report':r,
 'timeline':[{'elapsed_s':x['elapsed_s'],'result':x.get('result'),
 'observations':x.get('observations')} for x in d['samples']],
 'motor_commands_sent_by_reader':0,'automatic_following':False}))
