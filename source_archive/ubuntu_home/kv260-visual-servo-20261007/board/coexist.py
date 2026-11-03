"""Actual DPU query/classification concurrent with finite PWM and live preview."""
from common import *
from vsrv_driver import VSRVDriver,BIND,REFERENCE,ARM,COMMIT
import re
guard();assert json.loads((ROOT/'bench.json').read_text())['passed']
current=json.loads(Path('/home/root/aura-realtime-vision-20261007/current.json').read_text())
status_path=Path(current['run_root'])/'status.json';before=json.loads(status_path.read_text())
env=dict(os.environ,XLNX_VART_FIRMWARE='/lib/firmware/xilinx/'+APP+'/'+APP+'.xclbin')
query=json.loads(run(['xdputil','query'],30,env))
assert query['DPU IP Spec']['DPU Core Count']==1
expected={'DPU Arch':'DPUCZDX8G_ISA1_B4096','DPU Frequency (MHz)':300,'cu_addr':'0xa0010000','fingerprint':'0x101000056010407'}
assert len(query['kernels'])==1 and all(query['kernels'][0][k]==v for k,v in expected.items())
command=['/home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification',
 '/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel','/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg']
log=ROOT/'classification.txt'
with open_registers() as io:
 driver=VSRVDriver(io,0x14da0e60,BOOT);process=None
 try:
  driver.stop();io.write(0x10,0x20261008);io.write(0x14,2);io.write(0x24,BIND)
  io.write(0x3c,1500);io.write(0x24,REFERENCE);io.write(0x24,ARM)
  assert driver.status()['flags']==14
  with log.open('w') as f:
   process=subprocess.Popen(command,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
   t0=time.monotonic();assert process.poll() is None
   io.write(0x18,1);io.write(0x1c,1500);io.write(0x20,400);io.write(0x24,COMMIT)
   overlap=driver.status();inference_alive=process.poll() is None
   assert overlap['active'] and overlap['ack_seq']==1 and inference_alive
   rc=process.wait(timeout=25);duration=time.monotonic()-t0
  after_inference=driver.status();assert rc==0
  text=log.read_text()
  top5=[(int(a),b) for a,b in re.findall(r'r.index (\d+) .*?r.score ([0-9.eE+-]+)',text)]
  assert top5==[(258,'0.949879'),(270,'0.00931229'),(259,'0.00821807'),(257,'0.00498451'),(279,'0.00388194')],top5
 finally:
  if process and process.poll() is None:process.terminate();process.wait(timeout=5)
  final=driver.stop()
time.sleep(3);after=json.loads(status_path.read_text())
assert after['boot_id']==BOOT and not after['error'] and not after['stopped']
for k in ('capture_frames','detected_frames','display_frames','rendered_frames'):assert after[k]>before[k]
display=run(['xset','-display',':0','q'],10);assert 'Monitor is On' in display
save('coexist',{'passed':True,'query':query,'classification_top5':top5,'classification_duration_s':duration,
 'inference_process_alive_at_pwm_ack':inference_alive,'pwm_during_inference':overlap,
 'status_after_inference':after_inference,'final_stop':final,'preview_before':before,'preview_after':after,
 'display_on':True,'test_reference_us':1500,'physical_reference_calibrated':False,
 'physical_waveform_verified':False,'camera_pid_unchanged':current['pid'],'active_app':active()})
