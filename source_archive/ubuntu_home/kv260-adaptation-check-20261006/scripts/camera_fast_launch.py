"""Mirror the audited current preview; no PL or motor writes."""
import hashlib,json,os,signal,subprocess,time,uuid
from pathlib import Path
ROOT=Path('/home/root/aura-realtime-vision-20261007')
BOOT='f7a3ff07-fc20-4804-af12-c314a7a1847a'
REPLACEMENTS=[("BACKEND_SHA = '020668a71c2f08c2e671e0514790a00c241e25b1ce940f6e66be9ad6bc415443'", "BACKEND_SHA = 'ee34109e23423d99a4ea3ff75c2bf9d113329b1c8162cd02f30e7dfcfb6bfeaf'"), ("    backend = model_root/'face_compat.py'", "    backend = Path(__file__).with_name('face_compat_fast.py')"), ("    sys.path.insert(0, str(model_root))\n    from face_compat import YuNetCompat\n    cv2.setNumThreads(1)\n    return YuNetCompat(model_root/'models/yunet_2022mar.onnx')", "    sys.path.insert(0, str(backend.parent))\n    from face_compat_fast import YuNetCompat\n    cv2.setNumThreads(2)\n    return YuNetCompat(model_root/'models/yunet_2022mar.onnx', input_size=192)"), ("                      device='/dev/video0', capture_size=[640,480], capture_format='YUY2',\n", "                      device='/dev/video0', capture_size=[640,480], capture_format='YUY2',\n                      detector_input_size=[192,192], detector_cpu_threads=2,\n")]
DESIRED='fd7aab4cc5ac31287c97b150c5263f27ba8fd6e95b63323df1a1f90da7efd316'
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
assert release==Path('/home/root/aura-realtime-vision-20261007/releases/mirror-fa8246dfdbee850b') and pid==22427
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
assert sha(source.encode())=='9c82891b7ab023e1947d1bee329c30b2c0921e78aaf3b7ca2adcf85735f96b90'
for old,new in REPLACEMENTS:
 assert source.count(old)==1,old
 source=source.replace(old,new,1)
assert sha(source.encode())==DESIRED
contents['realtime_vision.py']=source.encode()
backend=Path('/home/root/aura-adaptation-20261006/detector-fast-7de5799a0afd4071/face_compat_fast.py')
contents['face_compat_fast.py']=backend.read_bytes()
assert sha(contents['face_compat_fast.py'])=='ee34109e23423d99a4ea3ff75c2bf9d113329b1c8162cd02f30e7dfcfb6bfeaf'
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
