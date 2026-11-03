"""Four-second finite bench sequence with inference alive and PWM through completion."""
import sys
sys.path.insert(0,'/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
from common import *
from vsrv_driver import VSRVDriver,BIND,REFERENCE,ARM,COMMIT
import statistics
guard();assert json.loads((ROOT/'coexist.json').read_text())['passed']
current=json.loads(Path('/home/root/aura-realtime-vision-20261007/current.json').read_text())
status_file=Path(current['run_root'])/'status.json';before=json.loads(status_file.read_text())
env=dict(os.environ,XLNX_VART_FIRMWARE='/lib/firmware/xilinx/'+APP+'/'+APP+'.xclbin')
command=['/home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification',
 '/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel','/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg']
events=[];latencies=[];process=None;completed=None
with open_registers() as io:
 driver=VSRVDriver(io,0x14da0e60,BOOT)
 try:
  driver.stop();io.write(0x10,0x20261008);io.write(0x14,3);io.write(0x24,BIND)
  io.write(0x3c,1500);io.write(0x24,REFERENCE);io.write(0x24,ARM)
  assert driver.status()['flags']==14
  with (ROOT/'overlap-classification.txt').open('w') as f:
   process=subprocess.Popen(command,env=env,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT)
   start=time.monotonic();seq=0;previous=None
   while time.monotonic()-start<4:
    elapsed=time.monotonic()-start;target=(1500,1480,1520,1500)[min(3,int(elapsed))]
    seq+=1;t=time.monotonic()
    io.write(0x18,seq);io.write(0x1c,target);io.write(0x20,150);io.write(0x24,COMMIT)
    s=driver.status();latencies.append((time.monotonic()-t)*1000)
    assert s['active'] and s['ack_seq']==seq and s['target_us']==target and not s['reason']
    if target!=previous:events.append({'elapsed_s':elapsed,'target_us':target,'status':s});previous=target
    if completed is None and process.poll() is not None:
     assert process.returncode==0;completed={'elapsed_s':time.monotonic()-start,'pwm_status':s}
    time.sleep(.04)
   duration=time.monotonic()-start
   assert duration<5 and completed and driver.status()['width_us']==1500
   assert process.poll()==0
 finally:
  final=driver.stop()
  if process and process.poll() is None:process.terminate();process.wait(timeout=5)
text=(ROOT/'overlap-classification.txt').read_text()
assert 'r.index 258' in text and 'r.score 0.949879' in text
time.sleep(2);after=json.loads(status_file.read_text())
assert not after['error'] and not after['stopped']
for k in ('capture_frames','detected_frames','display_frames','rendered_frames'):assert after[k]>before[k]
save('overlap',{'passed':True,'test_reference_us':1500,'physical_reference_calibrated':False,
 'commands':seq,'duration_s':duration,'events':events,'inference_completed_with_pwm_active':completed,
 'commit_to_ack_median_ms':statistics.median(latencies),'commit_to_ack_max_ms':max(latencies),
 'classification_output':text,'final_stop':final,'preview_frames_before':{k:before[k] for k in ('capture_frames','detected_frames','display_frames')},
 'preview_frames_after':{k:after[k] for k in ('capture_frames','detected_frames','display_frames')},
 'mechanical_response':'UNOBSERVED','external_waveform_verified':False,'pwm_running_after_test':False})
