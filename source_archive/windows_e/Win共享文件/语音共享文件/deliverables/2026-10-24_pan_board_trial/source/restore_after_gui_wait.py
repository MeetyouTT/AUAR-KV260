"""Complete the original rollback; allow the configured GUI startup grace."""
import fcntl,hashlib,importlib.util,json,sys,time
from pathlib import Path

CONTROLLER=Path('/home/root/aura-post-power-20261022/helpers/ce9111604e2f71ed/source.py')
PIN='ce9111604e2f71ede7d3a26a7611ae9b4df6db1a092e3cb4379d46de19981d3a'
ROOT=Path('/home/root/aura-pan-vsrv2-20261024/778d2512-1236ccf4')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='1236ccf4-7df1-420e-83e7-8df17e2c53a4'
assert hashlib.sha256(CONTROLLER.read_bytes()).hexdigest()==PIN

def run():
 spec=importlib.util.spec_from_file_location('owned_pan',str(CONTROLLER))
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 original=module.Trial.start_models
 def start_with_grace(self):
  try:return original(self)
  except RuntimeError as error:
   if str(error)!='Original GUI restart not confirmed':raise
   end=time.monotonic()+120;last=''
   while time.monotonic()<end:
    try:
     h=self.brief(self.get(8790,'/health'));g=self.get(8783,'/api/state')
     module.require(h['native_critical'] and not h['owner_fenced'] and h['identity_ready'] and h['worker_alive'],'Native r4 no longer healthy')
     module.require(self.props(module.GUI)['ActiveState']=='active' and g['phase']=='IDLE'
       and not g['playing'] and g['audio_output_state']=='IDLE_READY','GUI startup still pending')
     return self.save('ORIGINAL_R4_AND_GUI_RUNNING',restarted=h,extended_gui_grace_used=True)
    except Exception as problem:last=str(problem);time.sleep(.5)
   raise RuntimeError('Extended original GUI readiness failed: '+last)
 module.Trial.start_models=start_with_grace
 trial=module.Trial(ROOT)
 with (ROOT/'operation.lock').open('a+') as own,(Path(trial.base['ops_root'])/'operation.lock').open('a+') as existing:
  fcntl.flock(own,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(existing,fcntl.LOCK_EX|fcntl.LOCK_NB)
  trial.verify();result=trial.restore()
 with (ROOT/'manual-restore-result.json').open('x') as out:json.dump(result,out,indent=2);out.write('\n')
 print(json.dumps({'restored':True,'phase':result['phase']}))

if sys.argv[1:]==['--run']:run()
else:
 assert not sys.argv[1:]
 import subprocess
 p=subprocess.run(['systemd-run','--unit=aura-pan-vsrv2-1236ccf4-manual-recovery',
  '--property=Type=exec','--property=KillMode=process','--property=SendSIGKILL=no',
  '--property=TimeoutStartSec=infinity','/usr/bin/python3','-B',str(Path(__file__).resolve()),'--run'],
  capture_output=True,text=True,timeout=10)
 assert p.returncode==0,p.stderr
 print(json.dumps({'recovery_launched':True,'no_forced_model_kill':True}))
