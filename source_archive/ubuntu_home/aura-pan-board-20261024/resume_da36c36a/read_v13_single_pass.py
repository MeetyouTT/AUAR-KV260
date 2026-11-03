import json,time,urllib.request
from pathlib import Path
ROOT=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v13r1')
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as f:return json.load(f)
rows=[];report=None;path=None
for i in range(8):
 u=get(8783,'/api/state');m=u['manual_pan'];f=m.get('face_follow') or {}
 if f.get('report') and str(f['report']).startswith(str(ROOT/'runs')+'/'):
  path=Path(f['report']);path.relative_to(ROOT/'runs')
  if path.is_file() and path.stat().st_size:report=json.loads(path.read_text())
 r=(report or {}).get('result') or {};control=r.get('control') or {};p=get(8790,'/v1/motion/face/observation');t=p.get('target') or {};b=t.get('box')
 rows.append(dict(mono_ms=round(time.monotonic()*1000),automatic_following=m['automatic_following'],manual_state=m['state'],
  reason=r.get('reason'),state=r.get('state'),pulse_us=r.get('pulse_us'),commands_accepted=r.get('commands_accepted'),
  motion_target_changes=r.get('motion_target_changes'),segments=r.get('segments'),brief_face_gaps=r.get('brief_face_gaps'),
  brief_face_recoveries=r.get('brief_face_recoveries'),center_settles=r.get('center_settles'),readback=r.get('stopped') or r.get('readback'),
  recenter_phase=control.get('recenter_phase'),recenter_direction=control.get('recenter_direction'),
  controller_face_center_ratio=control.get('raw_center_ratio'),requested_velocity_us_s=control.get('requested_velocity_us_s'),
  trajectory_velocity_us_s=control.get('velocity_us_s'),controller_source_mono_ms=control.get('source_mono_ms'),
  face_state=p.get('state'),tracking_reason=(p.get('face_tracking') or {}).get('reason'),
  face_center_ratio=(b[0]+b[2]/2)/p['frame_width'] if b else None,face_left_ratio=b[0]/p['frame_width'] if b else None))
 if i<7:time.sleep(1)
h=get(8790,'/health')
print(json.dumps(dict(samples=rows,report=str(path) if path else None,report_status=(report or {}).get('status'),
 result=(report or {}).get('result'),input_summary=(report or {}).get('input_summary'),input_timing=(report or {}).get('input_timing'),
 camera_pid=h['pid'],capture_hz=h.get('capture_hz'),primary_overruns=h['dpu_schedule']['primary_period_overruns'],
 optional_overruns={k:v['overruns'] for k,v in h['dpu_schedule']['optional'].items()},motor_commands_sent_by_reader=0),ensure_ascii=False))
