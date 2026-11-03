"""Re-establish the stopped command reference from explicit user continuity."""
import hashlib,json,secrets,sys,time,fcntl
from pathlib import Path
BOOT='5f167a36-a715-4bbb-9186-4dff2bff8ee3';R=Path('/home/root/aura-system-pan-20261028/restore-5f167a36');B=Path('/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4-r2')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert hashlib.sha256(Path('/sys/firmware/fdt').read_bytes()).hexdigest()=='22516e08c2c862dfe3ee999a962ff62ed7830ad8e1183e36432cd22acde77762'
assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()=='aura-visual-servo-b4096-v2.bit.bin'
assert Path('/etc/vart.conf').read_text()=='firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-v2/aura-visual-servo-b4096-v2.xclbin\n'
assert hashlib.sha256((B/'candidate-manifest.json').read_bytes()).hexdigest()=='ed175a70735b4c445d6f86cbcd2909cdd1add349ba52f852f367a7602d30f9ab'
m=json.loads((B/'candidate-manifest.json').read_text());proof=json.loads((R/'id-stop.json').read_text())
assert proof['boot_id']==BOOT and proof['identity_stop_passed']
sys.path.insert(0,str(B/'driver'));from vsrv_transport import NativeRegisters
from vsrv_driver import VSRVDriver,BIND,REFERENCE
dest=R/'continuity-reference.json'
assert not dest.exists()
with Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/operation.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 with NativeRegisters(B/'driver/libvsrv.so',m['payload_files']['libvsrv.so'],BOOT,m['runtime_files']) as io:
  dev=VSRVDriver(io,0x778d2512,BOOT);before=dev.status();assert before==proof['after_stop']
  try:
   io.write(0x10,secrets.randbelow(0xfffffffe)+1);io.write(0x14,before['epoch']+1);io.write(0x24,BIND)
   assert dev.status()['flags']==8
   io.write(0x3c,1400);io.write(0x24,REFERENCE);defined=dev.status()
   assert defined['flags']==12 and defined['width_us']==defined['target_us']==defined['reference_us']==1400 and defined['lease_left_ms']==0
  finally:stopped=dev.stop()
  assert stopped['flags']==0 and stopped['lease_left_ms']==0 and stopped['width_us']==1400
 record={'schema':'aura-current-boot-continuity-reference-1','boot_id':BOOT,'fdt_sha256':'22516e08c2c862dfe3ee999a962ff62ed7830ad8e1183e36432cd22acde77762','user_quote':'都没有，机械朝向保持上次的位置','user_confirmed_no_manual_or_powerup_motion':True,'reference_us':1400,'source':'USER_CONFIRMED_CONTINUITY_FROM_PREVIOUS_STOPPED_COMMAND','predecessor_record':'Windows interaction final verification 2026-10-27T14:08:31.088346+00:00; automatic_following=false motor_active=false pan_us=1400','predecessor_boot':'da36c36a-ef4d-4122-8ad6-cfae3931303e','before':before,'defined':defined,'stopped_readback':stopped,'ARM_sent':False,'COMMIT_sent':False,'mechanical_angle_measured':False,'mechanical_zero_calibrated':False,'recorded_mono_s':time.monotonic()}
 with dest.open('x') as f:json.dump(record,f,ensure_ascii=False,indent=2)
print(json.dumps({'status':'CONTINUITY_REFERENCE_RECORDED_NO_PWM','reference_us':1400,'readback':stopped,'ARM_sent':False,'COMMIT_sent':False,'mechanical_angle_measured':False,'reference_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}))
