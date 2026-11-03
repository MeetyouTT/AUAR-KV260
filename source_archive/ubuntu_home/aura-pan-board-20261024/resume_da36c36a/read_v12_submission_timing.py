import json,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
m=u['manual_pan'];p=Path(m['face_follow']['report']);p.relative_to(Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v12r1/runs'))
d=json.loads(p.read_text());r=d['result']
print(json.dumps(dict(report=str(p),report_status=d['status'],manual_state=m['state'],automatic_following=m['automatic_following'],stopped=r.get('stopped'),
 submission_timing=d.get('submission_timing'),telemetry=d.get('telemetry'),reader_queue=d.get('reader_queue'),live_writer=d.get('live_writer'),
 observation_trace=d.get('observation_trace'),motor_commands_sent=0),ensure_ascii=False))
