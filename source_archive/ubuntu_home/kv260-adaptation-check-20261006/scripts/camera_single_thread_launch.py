"""Mirror the audited current preview; no PL or motor writes."""
import hashlib,json,os,signal,subprocess,time,uuid
from pathlib import Path
ROOT=Path('/home/root/aura-realtime-vision-20261007')
BOOT='f7a3ff07-fc20-4804-af12-c314a7a1847a'
REPLACEMENTS=[('    cv2.setNumThreads(4)\n', '    cv2.setNumThreads(1)\n')]
DESIRED='9c82891b7ab023e1947d1bee329c30b2c0921e78aaf3b7ca2adcf85735f96b90'
def sha(data):return hashlib.sha256(data).hexdigest()
def atomic(p,v):
 t=p.with_suffix('.tmp');t.write_text(json.dumps(v));t.replace(p)
def owners():
 result=[]
 for p in Path('/proc').iterdir():
  if p.name.isdecimal():
   try:
    if any(f.resolve()==Path('/dev/video0') for f in (p/'fd').iterdir()):result.append(int(p.name))
   except (FileNotFoundError,PermissionError):pass
 return sorted(result)
def apps():
 p=subprocess.run(['xmutil','listapps'],capture_output=True,text=True,timeout=12)
 assert p.returncode==0
 active=[r.split()[0] for r in p.stdout.splitlines() if r.split() and r.split()[-1].rstrip(',')=='0']
 assert active==['aura-visual-servo-b4096-v1'],active
 return p.stdout
def alive(pid):
 try:return Path('/proc/%d/stat'%pid).read_text().split()[2]!='Z'
 except FileNotFoundError:return False
def ready(p,run,mirror,old_epoch):
 deadline=time.monotonic()+25
 while time.monotonic()<deadline:
  assert p.poll() is None,(run/'worker.log').read_text()[-1800:]
  if (run/'status.json').exists():
   s=json.loads((run/'status.json').read_text())
   assert not s['error'],s['error']
   if s['detector_ready'] and s['detected_frames']>=3 and s['rendered_frames']>=3:break
  time.sleep(.2)
 else:raise RuntimeError('Preview not ready')
 time.sleep(3);after=json.loads((run/'status.json').read_text())
 assert not after['error'] and not after['stopped'] and after['boot_id']==BOOT
 assert after['epoch']!=old_epoch and after.get('mirror_horizontal',False)==mirror
 assert not after['actuation_authorized'] and not after['motion_command_emitted'] and after['motion_simulation'] is None
 assert owners()==[p.pid],owners()
 for k in ['capture_frames','detected_frames','display_frames','rendered_frames']:assert after[k]>s[k],k
 return s,after
def start(argv,run):
 env=dict(os.environ,DISPLAY=':0')
 with (run/'worker.log').open('ab') as log:
  p=subprocess.Popen(argv,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
 (run/'vision.pid').write_text(str(p.pid));return p
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
state=json.loads((ROOT/'current.json').read_text())
release=Path(state['release']);pid=state['pid'];oldrun=Path(state['run_root'])
assert release==Path('/home/root/aura-realtime-vision-20261007/releases/mirror-4f553d6e2ef836c2') and pid==22229
argv=[s.decode() for s in Path('/proc/%d/cmdline'%pid).read_bytes().split(b'\0') if s]
assert argv==['python3','-u',str(release/'realtime_vision.py'),'--run-root',str(oldrun),'--mirror-horizontal']
assert owners()==[pid]
oldstatus=json.loads((oldrun/'status.json').read_text())
assert not oldstatus['stopped'] and not oldstatus['error'] and oldstatus['motion_simulation'] is None
before_apps=apps()
stages=[(p,json.loads(p.read_text())) for p in (ROOT/'staged.json',ROOT/'motion-staged.json') if p.exists()]
matches=[(p,s) for p,s in stages if s['release']==str(release)]
assert len(matches)==1
stagepath,stage=matches[0];contents={}
for name,digest in stage['hashes'].items():
 assert '/' not in name and not (release/name).is_symlink()
 contents[name]=(release/name).read_bytes();assert sha(contents[name])==digest
source=contents['realtime_vision.py'].decode()
assert sha(source.encode())=='acdd9cb7aff55580484a9b7f7a62721f2a9d04ff09db3364af35458d29cbba36'
for old,new in REPLACEMENTS:
 assert source.count(old)==1,old
 source=source.replace(old,new,1)
assert sha(source.encode())==DESIRED
contents['realtime_vision.py']=source.encode()
hashes={n:sha(d) for n,d in contents.items()}
identity=sha(json.dumps(hashes,sort_keys=True).encode())[:16]
newrelease=ROOT/'releases'/('mirror-'+identity);newrelease.mkdir()
for n,d in contents.items():(newrelease/n).write_bytes(d)
preflight=subprocess.run(['python3','-B',str(newrelease/'realtime_vision.py'),'--preflight'],capture_output=True,text=True,timeout=30)
assert preflight.returncode==0,(preflight.stdout,preflight.stderr)
checked=json.loads(preflight.stdout)
assert checked['passed'] and checked['orientation_pixel_checks_passed'] and checked['mirrored_reference_faces']==1
run=ROOT/'runs'/('mirror-preview-'+uuid.uuid4().hex);run.mkdir()
atomic(run/'previous-state.json',state);atomic(run/'previous-staged.json',stage)
(run/'preflight.json').write_text(preflight.stdout)
assert owners()==[pid] and apps()==before_apps
p=None;stopped=False
try:
 os.kill(pid,signal.SIGTERM);stopped=True
 deadline=time.monotonic()+10
 while alive(pid) and time.monotonic()<deadline:time.sleep(.1)
 assert not alive(pid) and owners()==[],'Previous preview did not release camera'
 p=start(['python3','-u',str(newrelease/'realtime_vision.py'),'--run-root',str(run),'--mirror-horizontal'],run)
 first,after=ready(p,run,True,oldstatus['epoch'])
 assert apps()==before_apps
 current=dict(pid=p.pid,release=str(newrelease),run_root=str(run),before=first,after=after,
  passed=True,scope='MIRRORED_VIDEO_PREVIEW_ONLY',rollback=False,
  physical_reference_valid=False,previous_release=str(release),previous_pid=pid,
  mirror_horizontal=True,coordinate_convention='MIRRORED_SELF_VIEW',
  apps_before=before_apps,apps_after=apps())
 newstage=dict(stage,release=str(newrelease),hashes=hashes,
  previous_release=str(release),scope='CPU_CONTROL_TIMING_CHANGE')
 atomic(stagepath,newstage);atomic(ROOT/'mirror-staged.json',newstage)
 atomic(ROOT/'current.json',current)
 print(json.dumps(dict(current,preflight=checked,fpga_modified=False,motion_command_emitted=False)))
except Exception as exc:
 if p and p.poll() is None:p.terminate();p.wait(timeout=10)
 if stopped and not alive(pid):
  assert owners()==[]
  restored=start(argv,oldrun)
  first,after=ready(restored,oldrun,True,oldstatus['epoch'])
  atomic(stagepath,stage)
  atomic(ROOT/'current.json',dict(state,pid=restored.pid,before=first,after=after,rollback=True))
  print(json.dumps(dict(passed=False,error=str(exc),rollback_verified=True,pid=restored.pid)))
 raise
