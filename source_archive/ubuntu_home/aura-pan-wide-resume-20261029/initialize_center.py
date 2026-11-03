"""Explicit two-second nominal-center initialization, with no angle claim."""
import fcntl,hashlib,json,os,secrets,signal,sys,time
from pathlib import Path
BOOT='3336afd3-7926-40b3-b5fd-e17b86256830'
R=Path('/home/root/aura-pan-wide-resume-20261029/3336afd3')
B=Path('/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c')
C=Path('/home/root/aura-pan-wide-20261028/control-10282601')
def save(p,d):
 t=p.with_name(p.name+'.partial-'+str(os.getpid()))
 with t.open('x') as f:json.dump(d,f,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(t,p)
def main():
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
 s=json.loads((R/'state.json').read_text());assert s['phase']=='WIDE_CAMERA_RUNNING_GUI_HELD'
 auth=json.loads((R/'physical-authorization.json').read_text())
 assert auth['boot_id']==BOOT and auth['motor_power_on_user_reported'] is True
 assert auth['clearance_confirmed'] is True and auth['requested_angles_deg']==[-90,90]
 sys.path.insert(0,str(B));from bench_identity_stop import validated_context
 from types import SimpleNamespace
 args=SimpleNamespace(manifest=B/'candidate-manifest.json',manifest_sha256='6a4b645a5bbfd35c9107976edf27886cf8e0c91e40f48be6f052a95e1172c1cf',context=R/'context.json')
 root,manifest,boot=validated_context(args)
 sys.path.insert(0,str(root));sys.path.insert(0,str(C))
 from batch_transport import BatchRegisters
 from batch_driver import BatchDriver
 from vsrv_driver import BIND,REFERENCE,ARM,COMMIT,STOP,QUIESCE
 cancelled=[False]
 def cancel(*unused):cancelled[0]=True
 signal.signal(signal.SIGTERM,cancel);signal.signal(signal.SIGINT,cancel)
 report={'boot_id':BOOT,'status':'STARTING','source':'EXPLICIT_OPERATOR_NOMINAL_CENTER_INITIALIZATION','starting_physical_position_known':False,'target_us':1500,'mechanical_angle_measured':False,'mechanical_zero_calibrated':False,'commands':0,'initialization_command_completed':False,'stop_confirmed':False}
 output=R/'center-initialization.json';assert not output.exists();save(output,report)
 with (Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/operation.lock')).open('a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  with BatchRegisters(root/'libvsrv.so',manifest['payload_files']['libvsrv.so'],boot,manifest['runtime_files']) as io:
   d=BatchDriver(io,0x10282601,boot);before=d.status();assert before['flags']==0 and before['lease_left_ms']==0
   assert before['width_us']==before['target_us']==1500
   session=secrets.randbelow(0xfffffffe)+1;epoch=before['epoch']+1;started=time.monotonic();seq=0
   try:
    io.write(0x10,session);io.write(0x14,epoch);io.write(0x24,BIND)
    assert d.status()['flags']==8
    io.write(0x3c,1500);io.write(0x24,REFERENCE);assert d.status()['flags']==12
    io.write(0x24,ARM);assert d.status()['flags']==14
    while time.monotonic()-started<2.0:
     if cancelled[0]:raise RuntimeError('Operator cancelled initial center')
     state=d.status();assert state['reason']==0 and state['session']==session and state['epoch']==epoch
     assert state['flags']==(14 if seq==0 else 15)
     seq+=1
     for address,value in [(0x10,session),(0x14,epoch),(0x18,seq),(0x1c,1500),(0x20,100),(0x24,COMMIT)]:io.write(address,value)
     rb=d.status();assert rb['flags']==15 and rb['ack_seq']==seq and rb['target_us']==rb['width_us']==1500 and rb['lease_left_ms']>0
     report['commands']=seq;time.sleep(.02)
    io.write(0x24,QUIESCE);end=time.monotonic()+.05
    while d.status()['flags']&15 and time.monotonic()<end:time.sleep(.0005)
    assert d.status()['flags']==0
    report['initialization_command_completed']=True;report['status']='NOMINAL_CENTER_COMMAND_COMPLETED_PENDING_HUMAN'
   except BaseException as e:
    report['status']='FAILED_STOPPED_OR_REQUIRES_CHECK';report['error']=type(e).__name__+': '+str(e);raise
   finally:
    stopped=d.stop();report.update(stopped_readback=stopped,reference_us=1500,elapsed_s=time.monotonic()-started,stop_confirmed=stopped['flags']==0 and stopped['lease_left_ms']==0)
    save(output,report)
 print(json.dumps(report))
if __name__=='__main__':main()
