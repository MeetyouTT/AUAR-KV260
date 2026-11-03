"""Observe disabled registers and camera return for ten seconds; no writes."""
import hashlib,json,sys,time
from pathlib import Path
BOOT='c2753755-e758-4ab6-a4b6-2929271aa723'
root=Path('/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
assert hashlib.sha256((root/'common.py').read_bytes()).hexdigest()=='f529550d981a6114b669353db08c05174a6e45221c6385456d40896c18b0cc4a'
sys.path.insert(0,str(root));import common
common.BOOT=BOOT;common.guard();common.check_runtime()
from vsrv_driver import VSRVDriver
c=json.loads(Path('/home/root/aura-realtime-vision-20261007/current.json').read_text())
p=Path(c['run_root'])/'status.json';before=json.loads(p.read_text())
observation=Path(before['control_observation_path']);samples=[];start=time.monotonic()
with common.open_registers() as io:
 driver=VSRVDriver(io,0x14da0e60,BOOT)
 while time.monotonic()-start<10:
  s=driver.status();assert s['flags']==0 and s['lease_left_ms']==0 and not s['active'] and not s['armed']
  o=json.loads(observation.read_text());assert o['boot_id']==BOOT and o['epoch']==before['epoch'] and not o['error'] and not o['stopped']
  snap=o.get('snapshot') or {};visible=[t for t in snap.get('tracks',[]) if t.get('visible') and t.get('confirmed')]
  samples.append({'elapsed_s':time.monotonic()-start,'hardware':s,'frame_id':snap.get('frame_id'),'visible_targets':len(visible)})
  time.sleep(.2)
after=json.loads(p.read_text());assert not after['error'] and not after['stopped']
for k in ('capture_frames','detected_frames','display_frames'):assert after[k]>before[k]
print(json.dumps({'scope':'READ_ONLY_10S_DISABLED_MONITOR','passed':True,'boot_id':BOOT,'epoch':before['epoch'],'samples':samples,'visible_samples':sum(s['visible_targets']>0 for s in samples),'all_disabled':True,'ack_seq_unchanged':len(set(s['hardware']['ack_seq'] for s in samples))==1,'before_frames':before['detected_frames'],'after_frames':after['detected_frames'],'final_status':samples[-1]['hardware'],'motion_command_emitted':False}))
