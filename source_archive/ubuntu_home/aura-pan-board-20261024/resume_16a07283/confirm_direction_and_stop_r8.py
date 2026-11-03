import json,time,urllib.request
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def read():
 with o.open(base+'/api/state',timeout=3) as r:return json.load(r)['manual_pan']
before=read();assert before['automatic_following'] and 'continuous-v10r8/' in before['face_follow']['report']
request=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_stop"}',headers={'Origin':base,'Content-Type':'application/json'})
with o.open(request,timeout=3) as r:reply=json.load(r)
end=time.monotonic()+8
while time.monotonic()<end:
 after=read()
 if not after['automatic_following'] and after['state']=='READY':break
 time.sleep(.1)
assert after['state']=='READY' and not after['automatic_following'] and after['readback']['flags']==0 and after['readback']['lease_left_ms']==0,after
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');p=R/'direction-calibration.json';d=json.loads(p.read_text());assert d['axis_camera_mirrored_control_polarity']==1
d.update(automatic_direction_verified=True,automatic_direction_status='HUMAN_CLOSED_LOOP_DIRECTION_CONFIRMED',latest_closed_loop_user_feedback='方向正确，但是开始晚、延迟高、转动顿挫')
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'R8_STOPPED_FOR_R9','manual':after,'reply':reply}))
