import hashlib,json,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283')
e=R/'r14-v17-supervised-46817477006800.json';d=json.loads(e.read_text());p=Path(d['report']);r=json.loads(p.read_text())
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:m=json.load(f)['manual_pan']
assert m['state']=='READY' and not m['automatic_following']
assert m['readback']['flags']==0 and m['readback']['lease_left_ms']==0 and r['result']['stopped']==m['readback']
s=json.loads((R/'state.json').read_text());assert s['boot']==r['boot_id']
s.update(phase='R14_V17_ATTENDED_FOLLOW_NOT_ACCEPTED_STOPPED',current_last_command_us=m['readback']['width_us'],
 latest_supervised_trial=str(e),latest_supervised_report=str(p),automatic_following=False,
 latest_user_feedback='舵机有抽动，有延迟响应，我现在想让你去解决')
(R/'state.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'report_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
 'report':str(p),'final_report':r,'timeline':d['samples'],'readback':m['readback'],'motor_commands_sent':0}))
