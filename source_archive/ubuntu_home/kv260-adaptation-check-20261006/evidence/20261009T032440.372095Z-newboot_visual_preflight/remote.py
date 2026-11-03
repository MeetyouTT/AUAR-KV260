"""Sample face quality and source age while hardware remains disabled."""
import hashlib,json,statistics,sys,time,collections
from pathlib import Path
BOOT='c2753755-e758-4ab6-a4b6-2929271aa723'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
base=Path('/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
assert hashlib.sha256((base/'common.py').read_bytes()).hexdigest()=='f529550d981a6114b669353db08c05174a6e45221c6385456d40896c18b0cc4a'
sys.path.insert(0,str(base))
import common
common.BOOT=BOOT
common.guard();common.check_runtime()
from vsrv_driver import VSRVDriver
with common.open_registers() as io:
 s=VSRVDriver(io,0x14da0e60,BOOT).status()
 assert s['flags']==0 and s['lease_left_ms']==0
root=Path('/home/root/aura-realtime-vision-20261007')
c=json.loads((root/'current.json').read_text());p=Path(c['run_root'])/'status.json';before=json.loads(p.read_text())
assert before['boot_id']==BOOT and before['mirror_horizontal'] and not before['error'] and not before['stopped']
d=Path('/home/root/aura-adaptation-20261006/timing-fix-a312fd5f10cb4705/direction_bench.py')
assert hashlib.sha256(d.read_bytes()).hexdigest()=='42e17352881897c244d20463a33a600ca4f26034909c9d60ca335376ea0aec0f'
sys.path.insert(0,str(d.parent));from direction_bench import DirectionBench
ctrl=DirectionBench(BOOT,before['epoch']);observ=Path(before['control_observation_path'])
start=time.monotonic();ages=[];reasons=collections.Counter();ready_frames=0;centers=[];last=0
while time.monotonic()-start<5:
 obs=json.loads(observ.read_text());now=time.monotonic();snap=obs.get('snapshot') or {}
 source=snap.get('observed_time');fid=snap.get('frame_id',0)
 if source is not None:ages.append((now-source)*1000)
 if fid>last:
  last=fid;decision=ctrl.observe(obs,now);reasons[decision.get('reason',decision['kind'])]+=1
  if decision['kind']=='COMMAND':ready_frames+=1;centers.append(decision['center_x']);ctrl.accept(decision['target_us'])
 time.sleep(.005)
after=json.loads(p.read_text());assert not after['error'] and not after['stopped']
for k in ('capture_frames','detected_frames','display_frames'):assert after[k]>before[k]
print(json.dumps({'scope':'READ_ONLY_FACE_AND_TIMING_PREFLIGHT','boot_id':BOOT,'pid':c['pid'],'epoch':before['epoch'],'source_age_ms':{'samples':len(ages),'median':statistics.median(ages),'max':max(ages)} if ages else None,'over250':sum(a>250 for a in ages),'ready_frames':ready_frames,'reasons':dict(reasons),'center_range': [min(centers),max(centers)] if centers else None,'hardware_status':s,'after':after,'motion_command_emitted':False}))
