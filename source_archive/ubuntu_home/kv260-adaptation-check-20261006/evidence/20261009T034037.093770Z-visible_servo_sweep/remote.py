"""Finite, more visible sweep over the user's previously observed pulse range."""
import sys,json,time,uuid,signal,hashlib
from pathlib import Path
BOOT='c2753755-e758-4ab6-a4b6-2929271aa723'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
root=Path('/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
assert hashlib.sha256((root/'common.py').read_bytes()).hexdigest()=='f529550d981a6114b669353db08c05174a6e45221c6385456d40896c18b0cc4a'
sys.path.insert(0,str(root));import common
common.BOOT=BOOT;common.guard();common.check_runtime()
from vsrv_driver import VSRVDriver,BIND,REFERENCE,ARM,COMMIT
preview=Path('/home/root/aura-realtime-vision-20261007')
c=json.loads((preview/'current.json').read_text())
assert c['pid']==16981 and c['release']==str(preview/'releases/mirror-0c1d48dd418e922d')
status=Path(c['run_root'])/'status.json';before=json.loads(status.read_text())
assert before['boot_id']==BOOT and before['epoch']=='d9c2155d0af74326904cbb9b0ba94b31'
assert not before['error'] and not before['stopped'] and not before['actuation_authorized']
assert time.monotonic()-before['snapshot']['observed_time']<2
out=Path('/home/root/aura-adaptation-20261006')/('visible-sweep-'+uuid.uuid4().hex);out.mkdir()
session=uuid.uuid4().int&0xffffffff or 1;epoch=0x20261009
schedule=[(1500,2),(1600,4),(1500,2),(1400,4),(1500,2)]*2
events=[];seq=0;error=None;started=time.monotonic()
def interrupted(*_):raise KeyboardInterrupt('Visible sweep interrupted')
signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
with common.open_registers() as io:
 d=VSRVDriver(io,0x14da0e60,BOOT)
 try:
  initial=d.status();assert initial['flags']==0 and initial['lease_left_ms']==0
  d.stop();io.write(0x10,session);io.write(0x14,epoch);io.write(0x24,BIND)
  io.write(0x3c,1500);io.write(0x24,REFERENCE);io.write(0x24,ARM)
  assert d.status()['flags']==14
  for stage,(target,seconds) in enumerate(schedule):
   start=time.monotonic();settled=False
   while time.monotonic()-start<seconds:
    pre=d.status()
    assert pre['armed'] and pre['bound'] and pre['referenced']
    if seq:assert pre['active'] and pre['lease_left_ms']>0
    seq+=1
    io.write(0x18,seq);io.write(0x1c,target);io.write(0x20,150);io.write(0x24,COMMIT)
    s=d.status();elapsed=time.monotonic()-start
    assert s['flags']==15 and s['ack_seq']==seq and s['target_us']==target and not s['reason']
    assert s['session']==session and s['epoch']==epoch and s['reference_us']==1500
    assert 1400<=s['width_us']<=1600
    if elapsed>.8:assert s['width_us']==target
    settled=settled or elapsed>.8 and s['width_us']==target
    events.append({'stage':stage,'stage_elapsed_s':elapsed,'elapsed_s':time.monotonic()-started,'target_us':target,'readback':s})
    time.sleep(.04)
   assert settled
 except BaseException as exc:
  error=repr(exc);raise
 finally:
  final=d.stop()
  (out/'events.json').write_text(json.dumps(events))
  (out/'stop.json').write_text(json.dumps(final))
  (out/'error.json').write_text(json.dumps(error))
  assert final['flags']==0 and final['lease_left_ms']==0 and not final['active']
duration=time.monotonic()-started;time.sleep(2);after=json.loads(status.read_text())
assert after['epoch']==before['epoch'] and not after['error'] and not after['stopped']
for k in ('capture_frames','detected_frames','display_frames'):assert after[k]>before[k]
result={'passed':True,'scope':'FINITE_FIXED_VISIBLE_SWEEP_NOT_VISUAL_FOLLOWING',
 'boot_id':BOOT,'camera_epoch':after['epoch'],'preview_pid':c['pid'],
 'commands':seq,'duration_s':duration,'schedule':schedule,'pulse_range_us':[1400,1600],
 'hardware_slew_us_per_20ms':4,'host_ps_visual_slew_limit_used':False,
 'final_stop':final,'physical_reference_calibrated':False,
 'physical_motion':'AWAITING_USER_OBSERVATION','physical_direction':'AWAITING_USER_OBSERVATION',
 'evidence':str(out),'preview_continued':True}
(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
