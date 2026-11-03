"""Replay recorded timing/face geometry through a fake actuator, never hardware."""
import json,sys
from pathlib import Path
variant=sys.argv[1];sys.path.insert(0,str(Path(__file__).parent/variant))
from test_continuous_session import SessionTests,Device
from continuous_session import ContinuousSession
from continuous_face_control import EdgeConfig
from types import SimpleNamespace
meta=json.loads(Path('/home/ghmd/aura-pan-board-20261024/latest-resume-16a-r6-user-next-status.json').read_text())
report=json.loads((Path(meta['evidence'])/'response.json').read_text())['report']
rows=report['observation_trace'];SessionTests.setUpClass();fixture=SessionTests();fixture.setUp()
fixture.now=rows[0]['received_mono_ms']/1000.;fixture.device=Device(lambda:fixture.now)
config=EdgeConfig(left_ratio=.1,maximum_correction_us=None,confirm_frames=2 if 'r7_' in variant else 3)
s=ContinuousSession(fixture.device,'boot',config,lambda p:SimpleNamespace(reference_us=p),
 trajectory=fixture.trajectory,clock=lambda:fixture.now,allow_fixture=True,polarity=-1)
decisions={}
for row in rows:
 arrival=row['received_mono_ms']/1000.
 while fixture.now+.02<arrival:
  fixture.now+=.02;s.tick()
 fixture.now=max(fixture.now,arrival)
 if row['state']=='READY':
  x=row['face_left_ratio']*640;w=(row['face_center_ratio']-row['face_left_ratio'])*1280
  p=fixture.packet(row['face_center_ratio']);p['target']['box']=[x,100,min(w,640-x),100]
  p.update(source_frame_id=row['source_frame_id'],source_mono_ms=row['received_mono_ms']-row['source_age_ms'])
  p['deadline_mono_ms']=p['source_mono_ms']+250
  if row['detection_age_ms'] is not None:p['face_detection_mono_ms']=row['received_mono_ms']-row['detection_age_ms']
 else:
  p=fixture.packet(state=row['state'],source_frame_id=None,source_mono_ms=None,deadline_mono_ms=None,target=None,
   face_tracking=dict(version=11,error='',reason=row['tracking_reason']))
 s.step(p);s.tick();decisions[s.reason]=decisions.get(s.reason,0)+1
 if s.fatal:break
print(json.dumps({'kind':'software_reconstructed_timing_not_board_result','variant':variant,'rows':len(rows),
 'duration_s':fixture.now-s.started,'commands':len(fixture.device.commands),'target_changes':s.motion_updates,
 'arms':fixture.device.arms,'range_us':s.status()['range_us'],'fatal':s.fatal,'reason':s.reason,'decisions':decisions}))
