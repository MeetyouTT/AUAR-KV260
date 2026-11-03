"""Thirty-second supervised visual direction bench; formal calibration stays false."""
import sys,json,time,uuid,signal,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from direction_bench import DirectionBench
sys.path.insert(0,'/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
from common import *
from vsrv_driver import VSRVDriver,BIND,REFERENCE,ARM,COMMIT
guard();check_runtime();assert active()==[APP]
preview=Path('/home/root/aura-realtime-vision-20261007')
current=json.loads((preview/'current.json').read_text())
assert 'mirror-' in current['release']
status_file=Path(current['run_root'])/'status.json'
before=json.loads(status_file.read_text())
assert before['boot_id']==BOOT and before['mirror_horizontal']
assert not before['stopped'] and not before['error'] and not before['actuation_authorized']
assert Path('/proc/%d/cmdline'%current['pid']).read_bytes().find(current['release'].encode())>=0
epoch=before['epoch'];controller=DirectionBench(BOOT,epoch)
observation_file=Path(before['control_observation_path'])
assert observation_file.parent==Path('/run/aura-vision-observation')
OUT=Path('/home/root/aura-adaptation-20261006')/('visual-direction-'+uuid.uuid4().hex);OUT.mkdir()
events=[];commands=0;reason='TIME_LIMIT';start=time.monotonic()
session=int(uuid.uuid4().hex[:8],16) or 1;hardware_epoch=int(epoch[:8],16) or 1
def interrupt(*_):raise KeyboardInterrupt('INTERRUPTED')
signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt)
with open_registers() as io:
 driver=VSRVDriver(io,0x14da0e60,BOOT)
 try:
  initial=driver.status();assert initial['flags']==0 and initial['lease_left_ms']==0
  driver.stop();io.write(0x10,session);io.write(0x14,hardware_epoch);io.write(0x24,BIND)
  io.write(0x3c,1500);io.write(0x24,REFERENCE);io.write(0x24,ARM)
  assert driver.status()['flags']==14
  armed_at=time.monotonic()
  while time.monotonic()-start<30:
   s=json.loads(observation_file.read_text());now=time.monotonic()
   observation=(s.get('snapshot') or {}).get('observed_time',0)
   if observation<=armed_at:
    time.sleep(.02);continue
   decision=controller.observe(s,now)
   if decision['kind']=='STOP':reason=decision['reason'];break
   if decision['kind']=='COMMAND':
    target=decision['target_us'];commands+=1
    io.write(0x18,commands);io.write(0x1c,target)
    remaining=math.floor((.25-(time.monotonic()-decision['source_time'])-.02)*1000)
    if remaining<1:reason='SUBMISSION_TOO_LATE';break
    io.write(0x20,remaining);io.write(0x24,COMMIT)
    accepted=driver.status()
    assert accepted['active'] and accepted['ack_seq']==commands and accepted['target_us']==target and not accepted['reason'],accepted
    controller.accept(target)
    events.append(dict(decision,accepted=accepted,elapsed_s=time.monotonic()-start))
   if commands:
    status=driver.status()
    if not status['active']:reason='HARDWARE_LEASE_ENDED';break
   time.sleep(.02)
 except KeyboardInterrupt:reason='INTERRUPTED'
 finally:
  final=driver.stop()
  assert final['flags']==0 and final['lease_left_ms']==0
  (OUT/'stop.json').write_text(json.dumps(final))
duration=time.monotonic()-start
time.sleep(2);after=json.loads(status_file.read_text())
assert after['epoch']==epoch and not after['error'] and not after['stopped']
for k in ('capture_frames','detected_frames','display_frames'):assert after[k]>before[k]
(OUT/'events.json').write_text(json.dumps(events,indent=2))
result={'scope':'FINITE_VISUAL_DIRECTION_BENCH_NOT_FORMAL_TRACKING','command_transport_passed':commands>0,
 'stop_verified':True,'stop_reason':reason,'commands':commands,'duration_s':duration,
 'requested_left':'COUNTERCLOCKWISE','requested_right':'CLOCKWISE','user_reported_pulse_increase':'COUNTERCLOCKWISE',
 'polarity':-1,'test_reference_us':1500,'range_us':[1480,1520],'mapping_is_measured_pointing':False,
 'source':'MIRRORED_FACE_CENTER_RELATIVE_TO_BLUE_LINE','speed_tuning_performed':False,
 'physical_reference_calibrated':False,'formal_tracking_started':False,
 'boot_id':BOOT,'camera_epoch':epoch,'preview_pid':current['pid'],'final_stop':final,
 'directions_commanded':sorted(set(e['desired_direction'] for e in events)),
 'target_range_us':[min(e['target_us'] for e in events),max(e['target_us'] for e in events)] if events else None,
 'evidence':str(OUT),'mechanical_following_confirmation':'AWAITING_USER'}
(OUT/'result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
