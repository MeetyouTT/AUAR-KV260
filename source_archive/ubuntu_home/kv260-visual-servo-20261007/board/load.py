"""One guarded switch; on error restore the official app, never retry loading."""
from common import *
from vsrv_driver import VSRVDriver
guard();check_runtime();assert active()==[BASELINE] and firmware()==BASELINE+'.bit.bin'
assert json.loads((ROOT/'installed.json').read_text())['passed']
snapshot=json.loads((ROOT/'baseline-snapshot.json').read_text())
for p,d in snapshot['firmware_hashes'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==d
assert Path('/etc/vart.conf').read_text()==snapshot['vart_conf']
no_clients();switch_started=False
try:
 switch_started=True
 unloaded=run(['xmutil','unloadapp'])
 assert 'returns: 0 (Ok)' in unloaded
 assert active()==[] and not list(Path('/sys/kernel/config/device-tree/overlays').iterdir())
 loaded=run(['xmutil','loadapp',APP])
 assert 'loaded to slot 0' in loaded and 'Error' not in loaded
 assert active()==[APP] and firmware()==APP+'.bit.bin'
 assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()=='operating'
 assert len(list(Path('/sys/kernel/config/device-tree/overlays').iterdir()))==1
 with open_registers() as io:
  driver=VSRVDriver(io,0x14da0e60,BOOT)
  initial=driver.status();assert initial['flags']==0 and initial['lease_left_ms']==0
  stopped=driver.stop()
 clocks=[s for s in Path('/sys/kernel/debug/clk/clk_summary').read_text().splitlines() if 'pl0_ref' in s]
 save('loaded',{'passed':True,'app':APP,'firmware':firmware(),'initial':initial,'stop':stopped,
  'load_output':loaded,'unload_output':unloaded,'clock_rows':clocks,'pwm_command_emitted':False})
except BaseException as exc:
 restored=False
 try:
  if active()==[APP]:run(['xmutil','unloadapp'])
  if active()==[]:run(['xmutil','loadapp',BASELINE])
  restored=active()==[BASELINE] and firmware()==BASELINE+'.bit.bin'
 finally:save('load-failed',{'passed':False,'error':str(exc),'baseline_restored':restored})
 raise
