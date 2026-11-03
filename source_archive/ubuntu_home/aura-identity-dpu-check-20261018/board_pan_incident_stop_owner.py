"""Contain reported uncontrolled motion via its native owner; never ARM."""
import base64,gzip,hashlib,importlib.util,json,os,signal,subprocess,time,urllib.request
from pathlib import Path
BOOT='3e1add36-b917-4289-91dc-699348528782'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
ROOT=Path('/home/root/aura-adaptation-20261006/vsrv-source-14da0e60/unpacked')
def owners():
 result=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  for fd in (p/'fd').glob('*'):
   try:
    if os.readlink(str(fd))=='/run/aura-vsrv.lock':
     result.append({'pid':int(p.name),'cmd':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')});break
   except OSError:pass
 return result
v={'boot':BOOT,'movement_commands_sent':0,'owners_before':owners(),'terminated':[]}
for row in v['owners_before']:
 assert row['pid']!=os.getpid() and 'python' in row['cmd'],row
 os.kill(row['pid'],signal.SIGTERM);v['terminated'].append(row['pid'])
for _ in range(25):
 if not owners():break
 time.sleep(.1)
v['owners_after']=owners()
if not v['owners_after']:
 import sys
 sys.path.insert(0,str(ROOT))
 import common
 assert hashlib.sha256((ROOT/'common.py').read_bytes()).hexdigest()=='f529550d981a6114b669353db08c05174a6e45221c6385456d40896c18b0cc4a'
 common.BOOT=BOOT
 from vsrv_driver import VSRVDriver
 with common.open_registers() as io:v['stopped']=VSRVDriver(io,0x14da0e60,BOOT).stop()
 assert v['stopped']['flags']==0 and v['stopped']['lease_left_ms']==0
v['unit']=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ActiveState,SubState,MainPID,ExecStart,NRestarts'],text=True)
base=Path('/home/root/aura-voice-barge-in-20261020/candidate-667b70d586ca/runtime')
try:
 lines=(base/'stage.log').read_text(errors='replace').splitlines();v['log_issues']=[x for x in lines if any(w in x for w in ['Traceback','Error','CRITICAL','ERROR','WARNING'])][-30:]
except OSError:pass
v['artifacts']={}
for name in ['payload_manifest.json']:
 raw=gzip.compress((ROOT/name).read_bytes(),mtime=0);v['artifacts'][name+'.gz']={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
print(json.dumps(v),flush=True)
