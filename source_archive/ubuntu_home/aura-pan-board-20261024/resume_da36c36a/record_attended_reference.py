"""User confirms historical 1420 forward position; record without ARM/COMMIT."""
import fcntl,hashlib,json,secrets,sys,time
from pathlib import Path
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/fixed-motion-bench-v1')
sys.path.insert(0,str(P))
from board_fixed_cli import preflight,R,OPS,OLD,BOOT,FDT
manifest,control=preflight('9a47a0319dc67644bf871497715da70171b39d329ec335b16b56079dc6850718')
assert not (R/'attended-fixed-reference.json').exists()
proof=json.loads((R/'id-stop.json').read_text());assert proof['boot_id']==BOOT and proof['identity_stop_passed']
C=OPS/'pan-face-edge-v5/continuous-v10r15';sys.path.extend([str(C),str(OLD/'driver')])
from batch_transport import BatchRegisters
from batch_driver import BatchDriver
from vsrv_driver import BIND,REFERENCE
library=C/'libvsrv_batch.so';pin=next(x['sha256'] for x in control['files'] if x['destination']==str(library))
with (OPS/'operation.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with BatchRegisters(library,pin,BOOT,manifest['runtime_files']) as io:
  d=BatchDriver(io,0x778d2512,BOOT);before=d.status()
  assert before==proof['after_stop'] and before['flags']==0 and before['lease_left_ms']==0
  try:
   d.stop();io.write(0x10,secrets.randbelow(0xfffffffe)+1);io.write(0x14,before['epoch']+1);io.write(0x24,BIND)
   assert d.status()['flags']==8
   io.write(0x3c,1420);io.write(0x24,REFERENCE);defined=d.status()
   assert defined['flags']==12 and defined['width_us']==defined['reference_us']==defined['target_us']==1420 and defined['lease_left_ms']==0
  finally:stopped=d.stop()
  assert stopped['flags']==0 and stopped['lease_left_ms']==0 and stopped['width_us']==1420
 now=time.monotonic();ident='attended-fixed-'+str(time.monotonic_ns())
 receipt=dict(schema='aura-user-observed-fixed-reference-1',boot_id=BOOT,fdt_sha256=FDT,
  user_present=True,confirmed_current_position=True,user_observation='用户说“我在镜头前”；询问是否仍为此前1420µs正前位置后，用户答“是的”。',
  reference_us=1420,bounds_us=[1402,1420],polarity=1,camera_moves_with_axis=True,authorization_id=ident,
  observed_mono_s=now,expires_mono_s=now+600,stopped_readback=stopped,
  source='USER_CURRENT_OBSERVATION_PLUS_PREVIOUS_1420_REFERENCE_NOT_REGISTER_DEFAULT',
  reference_setup=dict(before=before,defined=defined,ARM_sent=False,COMMIT_sent=False,mechanical_angle_measured=False))
 with (R/'attended-fixed-reference.json').open('x') as out:json.dump(receipt,out,ensure_ascii=False,indent=2);out.write('\n')
print(json.dumps({'status':'USER_OBSERVED_REFERENCE_RECORDED_OUTPUT_OFF','boot_id':BOOT,'readback':stopped,
 'receipt_sha256':hashlib.sha256((R/'attended-fixed-reference.json').read_bytes()).hexdigest(),
 'ARM_sent':False,'COMMIT_sent':False,'physical_motion_requested':False,'external_measurement':False}))
