"""Finite pulse-polarity check; no visual following or speed tuning."""
import sys,json,time,uuid,signal
from pathlib import Path
sys.path.insert(0,'/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
from common import *
from vsrv_driver import VSRVDriver,BIND,REFERENCE,ARM,COMMIT
guard();check_runtime();assert active()==[APP]
preview=Path('/home/root/aura-realtime-vision-20261007')
current=json.loads((preview/'current.json').read_text())
assert current['pid']==19794 and current['release']==str(preview/'releases/mirror-81f321f9aea59728')
status_file=Path(current['run_root'])/'status.json'
before=json.loads(status_file.read_text())
assert before['boot_id']==BOOT and before['epoch']=='4a34688a223445969d193f5cb2bcbe28'
assert before['mirror_horizontal'] and not before['stopped'] and not before['error']
assert not before['actuation_authorized'] and before['motion_simulation'] is None
assert time.monotonic()-before['snapshot']['observed_time']<2
out=Path('/home/root/aura-adaptation-20261006')/('direction-'+uuid.uuid4().hex)
out.mkdir()
events=[];seq=0;previous=None;t0=None
def interrupted(*_):raise KeyboardInterrupt('Direction test interrupted')
signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
with open_registers() as io:
 driver=VSRVDriver(io,0x14da0e60,BOOT)
 try:
  initial=driver.status();assert initial['flags']==0 and initial['lease_left_ms']==0 and initial['width_us']==1500
  driver.stop()
  io.write(0x10,0x20261008);io.write(0x14,4);io.write(0x24,BIND)
  io.write(0x3c,1500);io.write(0x24,REFERENCE);io.write(0x24,ARM)
  assert driver.status()['flags']==14
  # Reuse previously tested 1500/1520 us points, not measured calibration.
  t0=time.monotonic()
  while time.monotonic()-t0<4:
   elapsed=time.monotonic()-t0
   target=1500 if elapsed<1 or elapsed>=3 else 1520
   seq+=1
   io.write(0x18,seq);io.write(0x1c,target);io.write(0x20,150);io.write(0x24,COMMIT)
   s=driver.status()
   assert s['active'] and s['ack_seq']==seq and s['target_us']==target and not s['reason']
   if target!=previous:
    events.append({'elapsed_s':elapsed,'target_us':target,'readback':s});previous=target
   time.sleep(.04)
  assert driver.status()['width_us']==1500
 finally:
  final=driver.stop()
  assert not final['active'] and final['flags']==0 and final['lease_left_ms']==0
  (out/'stop.json').write_text(json.dumps(final))
duration=time.monotonic()-t0
time.sleep(2);after=json.loads(status_file.read_text())
assert after['epoch']==before['epoch'] and not after['error'] and not after['stopped']
for k in ('capture_frames','detected_frames','display_frames'):assert after[k]>before[k]
result={'passed':True,'scope':'FINITE_PHYSICAL_DIRECTION_CHECK','boot_id':BOOT,
 'camera_epoch':after['epoch'],'preview_pid':current['pid'],'events':events,
 'commands':seq,'duration_s':duration,'final_stop':final,'physical_direction':'AWAITING_USER_OBSERVATION',
 'test_reference_us':1500,'physical_reference_calibrated':False,'speed_tuning_performed':False,
 'visual_following_started':False,'evidence':str(out),'requested_left':'COUNTERCLOCKWISE',
 'requested_right':'CLOCKWISE','rotation_view':'LOOKING_AT_SHAFT_END'}
(out/'result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
