"""Finite visual direction test with per-frame timing and fail-closed acknowledgement."""
import sys,json,time,uuid,signal,math,statistics
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from direction_bench import DirectionBench
sys.path.insert(0,'/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
from common import *
from vsrv_driver import VSRVDriver,BIND,REFERENCE,ARM,COMMIT
guard();check_runtime();assert active()==[APP]
preview=Path('/home/root/aura-realtime-vision-20261007');current=json.loads((preview/'current.json').read_text())
status_file=Path(current['run_root'])/'status.json';before=json.loads(status_file.read_text())
assert before['boot_id']==BOOT and before['mirror_horizontal'] and not before['stopped'] and not before['error']
assert not before['actuation_authorized'] and before['motion_simulation'] is None
assert Path('/proc/%d/cmdline'%current['pid']).read_bytes().find(current['release'].encode())>=0
epoch=before['epoch'];controller=DirectionBench(BOOT,epoch)
observation_file=Path(before['control_observation_path']);assert observation_file.parent==Path('/run/aura-vision-observation')
OUT=Path('/home/root/aura-adaptation-20261006')/('visual-direction-timing-'+uuid.uuid4().hex);OUT.mkdir()
events=[];attempts=commands=0;reason='TIME_LIMIT';error=None;start=None
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
  start=armed_at=time.monotonic()
  while time.monotonic()-start<30:
   s=json.loads(observation_file.read_text());now=time.monotonic()
   source=(s.get('snapshot') or {}).get('observed_time',0)
   if source<=armed_at:time.sleep(.005);continue
   decision=controller.observe(s,now)
   if decision['kind']=='STOP':reason=decision['reason'];break
   # Read active lease BEFORE attempting another commit; expiry never rearms.
   if commands:
    prior=driver.status()
    if not prior['active']:reason='HARDWARE_LEASE_ENDED';events.append({'kind':'STOP','reason':reason,'readback':prior,'elapsed_s':time.monotonic()-start});break
   if decision['kind']=='COMMAND':
    target=decision['target_us'];attempts+=1;seq=commands+1
    submitted=time.monotonic()
    io.write(0x18,seq);io.write(0x1c,target)
    checked=time.monotonic();remaining=math.floor((.25-(checked-decision['source_time'])-.02)*1000)
    if remaining<1:reason='SUBMISSION_TOO_LATE';break
    io.write(0x20,remaining);io.write(0x24,COMMIT)
    accepted=driver.status();completed=time.monotonic()
    event=dict(decision,accepted=accepted,seq=seq,elapsed_s=completed-start,
     publication_time=s['publication_time'],source_age_at_submit_ms=(checked-source)*1000,
     source_age_at_ack_ms=(completed-source)*1000,lease_requested_ms=remaining,
     submission_ms=(completed-submitted)*1000)
    events.append(event)
    exact=(accepted['active'] and accepted['armed'] and accepted['referenced'] and accepted['bound'] and
     accepted['ack_seq']==seq and accepted['target_us']==target and accepted['session']==session and
     accepted['epoch']==hardware_epoch and accepted['reference_us']==1500 and not accepted['reason'])
    if not exact:reason='COMMAND_NOT_ACCEPTED_OR_LEASE_ENDED';break
    commands=seq;controller.accept(target)
   time.sleep(.005)
 except KeyboardInterrupt:reason='INTERRUPTED'
 except Exception as exc:reason='EXCEPTION';error=type(exc).__name__+': '+str(exc)
 finally:
  final=driver.stop();assert final['flags']==0 and final['lease_left_ms']==0
  (OUT/'stop.json').write_text(json.dumps(final));(OUT/'events.json').write_text(json.dumps(events,indent=2))
duration=time.monotonic()-start if start is not None else 0
time.sleep(2);after=json.loads(status_file.read_text())
preview_ok=after['epoch']==epoch and not after['error'] and not after['stopped'] and all(after[k]>before[k] for k in ('capture_frames','detected_frames','display_frames'))
accepted_events=[e for e in events if e.get('kind')=='COMMAND' and e.get('seq',0)<=commands]
widths=[e['accepted']['width_us'] for e in accepted_events]
def summary(key):
 v=[e[key] for e in accepted_events];return {'median':statistics.median(v),'max':max(v),'min':min(v)} if v else None
result={'scope':'FINITE_VISUAL_DIRECTION_BENCH_NOT_FORMAL_TRACKING','continuous_control_passed':reason=='TIME_LIMIT' and duration>=30 and commands>=100 and preview_ok,
 'command_transport_passed':commands>0,'stop_verified':True,'stop_reason':reason,'error':error,
 'commands':commands,'attempts':attempts,'duration_s':duration,'preview_ok':preview_ok,
 'requested_left':'COUNTERCLOCKWISE','requested_right':'CLOCKWISE','user_reported_pulse_increase':'COUNTERCLOCKWISE','polarity':-1,
 'test_reference_us':1500,'range_us':[1480,1520],'mapping_is_measured_pointing':False,
 'source':'MIRRORED_FACE_CENTER_RELATIVE_TO_BLUE_LINE','speed_tuning_performed':False,
 'physical_reference_calibrated':False,'formal_tracking_started':False,'boot_id':BOOT,
 'camera_epoch':epoch,'preview_pid':current['pid'],'final_stop':final,
 'directions_commanded':sorted(set(e['desired_direction'] for e in accepted_events)),
 'target_range_us':[min(e['target_us'] for e in accepted_events),max(e['target_us'] for e in accepted_events)] if accepted_events else None,
 'effective_width_range_us':[min(widths),max(widths)] if widths else None,
 'source_age_at_submit_ms':summary('source_age_at_submit_ms'),'source_age_at_ack_ms':summary('source_age_at_ack_ms'),
 'submission_ms':summary('submission_ms'),'lease_requested_ms':summary('lease_requested_ms'),
 'last_event':events[-1] if events else None,'evidence':str(OUT),'mechanical_following_confirmation':'AWAITING_USER'}
(OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if error or not preview_ok:raise RuntimeError(error or 'Preview verification failed')
