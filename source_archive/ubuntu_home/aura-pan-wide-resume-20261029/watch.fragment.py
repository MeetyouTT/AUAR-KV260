def watch():
 s=json.loads((R/'state.json').read_text());fixed(s);assert s['phase']=='WIDE_LOADED_ID_STOP_PASS'
 assert props(CAM)['MainPID']==props(GUI)['MainPID']=='0'
 sys.path.insert(0,str(B/'driver'));sys.path.insert(0,'/home/root/aura-pan-wide-20261028/control-10282601')
 from batch_transport import BatchRegisters
 from batch_driver import BatchDriver
 manifest=json.loads((B/'candidate-manifest.json').read_text());samples=[];started=time.monotonic()
 def leds():
  out={}
  for p in Path('/sys/class/leds').glob('*'):
   out[p.name]={n:(p/n).read_text().strip() for n in ['brightness','trigger'] if (p/n).exists()}
  return out
 with BatchRegisters(B/'driver/libvsrv.so',manifest['payload_files']['libvsrv.so'],BOOT,manifest['runtime_files']) as io:
  d=BatchDriver(io,0x10282601,BOOT)
  while time.monotonic()-started<90:
   assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
   rb=d.status();assert rb['flags']==0 and rb['lease_left_ms']==0
   sample={'elapsed_s':round(time.monotonic()-started,3),'uptime_s':float(Path('/proc/uptime').read_text().split()[0]),'readback':rb,'leds':leds()}
   samples.append(sample);atomic(R/'wide-idle-watch.json',{'status':'RUNNING','boot_id':BOOT,'samples':samples,'ARM_sent':False,'COMMIT_sent':False})
   time.sleep(5)
 s['phase']='WIDE_IDLE_WATCH_PASS';atomic(R/'state.json',s)
 result={'phase':s['phase'],'boot_id':BOOT,'elapsed_s':time.monotonic()-started,'samples':len(samples),'readback':samples[-1]['readback'],'leds':samples[-1]['leds'],'ARM_sent':False,'COMMIT_sent':False}
 atomic(R/'wide-idle-watch-result.json',result);return result
