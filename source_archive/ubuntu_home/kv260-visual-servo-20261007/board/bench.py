"""Finite powered bench protocol test; 1500 us is a test point, not calibration."""
from common import *
from vsrv_driver import VSRVDriver,BIND,REFERENCE,ARM,COMMIT,STOP
import statistics
guard();assert json.loads((ROOT/'loaded.json').read_text())['passed']
events=[];t0=time.monotonic()
def event(label,status,**extra):events.append({'name':label,'elapsed_ms':(time.monotonic()-t0)*1000,'status':status,**extra})
with open_registers() as io:
 driver=VSRVDriver(io,0x14da0e60,BOOT)
 try:
  # A second cooperative owner must fail before any register access.
  try:second=open_registers()
  except OSError as e:assert e.errno in (11,35);event('second_owner_rejected',{},errno=e.errno)
  else:second.close();raise AssertionError('Lock did not exclude second owner')
  event('initial_stop',driver.stop())
  io.write(0x24,COMMIT);s=driver.status();assert s['reason']==2 and not s['active'];event('unarmed_rejected',s)
  def setup():
   driver.stop();io.write(0x10,0x20261008);io.write(0x14,1);io.write(0x24,BIND)
   io.write(0x3c,1500);io.write(0x24,REFERENCE);io.write(0x24,ARM)
   s=driver.status();assert s['flags']==14 and s['reference_us']==1500;return s
  def commit(seq,target,lease):
   io.write(0x18,seq);io.write(0x1c,target);io.write(0x20,lease);io.write(0x24,COMMIT)
   s=driver.status();assert s['ack_seq']==seq and s['target_us']==target and s['active'] and not s['reason'];return s
  event('bench_setup',setup())
  event('lease_start',commit(1,1500,120));start=time.monotonic()
  deadline=start+.4
  while time.monotonic()<deadline:
   s=driver.status()
   if not s['active']:break
   time.sleep(.001)
  elapsed=(time.monotonic()-start)*1000
  assert s['flags']==64 and s['lease_left_ms']==0 and 90<elapsed<200,(s,elapsed)
  event('lease_expired',s,observed_expiry_ms=elapsed)
  io.write(0x18,2);io.write(0x24,COMMIT);s=driver.status()
  assert s['reason']==2 and not s['active'] and s['ack_seq']==1;event('expiry_no_auto_rearm',s)
  event('bench_rearm',setup());event('small_positive_command',commit(1,1504,300))
  time.sleep(.09);s=driver.status();assert s['width_us']==1504;event('positive_width_readback',s)
  io.write(0x18,1);io.write(0x24,COMMIT);s=driver.status();assert s['reason']==2 and s['ack_seq']==1;event('duplicate_rejected',s)
  event('small_negative_command',commit(2,1496,300));time.sleep(.09)
  s=driver.status();assert s['width_us']==1496;event('negative_width_readback',s)
  t=time.monotonic();s=driver.stop();event('explicit_stop',s,ack_ms=(time.monotonic()-t)*1000)
  latencies=[]
  for _ in range(100):
   t=time.monotonic();driver.status();latencies.append((time.monotonic()-t)*1000)
  budget={'status_median_ms':statistics.median(latencies),'status_max_ms':max(latencies)}
 finally:
  final=driver.stop();event('finally_stop',final)
save('bench',{'passed':True,'powered_test_authorized':True,'cutoff_protection':'USER_REPORTED_NOT_VERIFIED',
 'test_reference_us':1500,'physical_reference_calibrated':False,'events':events,'transport_budget':budget,
 'external_waveform_verified':False,'mechanical_response':'UNOBSERVED','motion_active_after_test':False})
