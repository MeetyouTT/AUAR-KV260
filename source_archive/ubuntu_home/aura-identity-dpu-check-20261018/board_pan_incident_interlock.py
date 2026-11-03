"""Hold the audited native mutex after STOP, without opening hardware."""
import hashlib,json,os,subprocess,time
from pathlib import Path
BOOT='3e1add36-b917-4289-91dc-699348528782'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
p=Path('/home/root/aura-pan-incident-20261020');p.mkdir(exist_ok=True)
script='''import fcntl,json,os,signal,stat,time
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==%r
fd=os.open('/run/aura-vsrv.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
s=os.fstat(fd);assert stat.S_ISREG(s.st_mode) and s.st_uid==0
fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
Path(%r).write_text(json.dumps({'pid':os.getpid(),'boot_id':%r,'status':'INHIBITED_NO_MMIO','reason':'Unexpected large return movement reported; waveform/command review pending'})+'\\n')
def close(*unused):raise SystemExit(0)
signal.signal(signal.SIGTERM,close);signal.signal(signal.SIGINT,close)
try:
 while True:signal.pause()
finally:os.close(fd)
'''%(BOOT,str(p/'lock-status.json'),BOOT)
target=p/'lock_guard.py'
with target.open('x') as f:f.write(script)
with (p/'lock-guard.log').open('xb') as log:
 child=subprocess.Popen(['/usr/bin/python3','-B',str(target)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
for _ in range(20):
 if (p/'lock-status.json').exists():break
 time.sleep(.1)
value=json.loads((p/'lock-status.json').read_text());assert value['pid']==child.pid
cmd=Path('/proc/%d/cmdline'%child.pid).read_bytes();assert str(target).encode() in cmd
fds=[os.readlink(str(f)) for f in Path('/proc/%d/fd'%child.pid).iterdir()]
assert '/run/aura-vsrv.lock' in fds and '/dev/mem' not in fds
print(json.dumps(dict(value,guard_sha256=hashlib.sha256(script.encode()).hexdigest(),hardware_opened=False,movement_commands_sent=0)),flush=True)
