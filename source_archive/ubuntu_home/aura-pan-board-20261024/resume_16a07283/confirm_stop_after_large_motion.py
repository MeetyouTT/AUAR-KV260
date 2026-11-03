import json,subprocess,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');old=Path('/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4-r2')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='16a07283-9e14-45e6-816d-3bda4cf333a7'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
assert not u['manual_pan']['automatic_following'] and u['manual_pan']['state']=='FAULT'
out=R/'id-stop-after-user-100deg.json'
p=subprocess.run(['/usr/bin/python3','-B',str(old/'bench_identity_stop.py'),'--execute','--confirmation','ID_STOP_ONLY',
 '--manifest',str(old/'candidate-manifest.json'),'--manifest-sha256','ed175a70735b4c445d6f86cbcd2909cdd1add349ba52f852f367a7602d30f9ab',
 '--context',str(R/'context.json'),'--output',str(out)],capture_output=True,text=True,timeout=15)
assert p.returncode==0,p.stderr[-700:]
proof=json.loads(out.read_text());assert proof['identity_stop_passed'] and proof['after_stop']['flags']==0 and proof['after_stop']['lease_left_ms']==0
s=json.loads((R/'state.json').read_text());s.update(phase='USER_REPORTED_APPROX_100DEG_MOTION_TESTS_HALTED',physical_response_accepted=False,
 human_feedback_verbatim='转了角度为100度，幅度这么大么',automatic_following=False,physical_motion_tests_halted=True)
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'before':proof['before'],'after_stop':proof['after_stop'],'ARM_sent':False,'COMMIT_sent':False,'automatic_following':False}))
