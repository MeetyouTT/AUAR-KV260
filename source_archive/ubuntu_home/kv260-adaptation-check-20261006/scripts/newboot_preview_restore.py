"""Restore the last hash-verified mirrored CPU preview, without motion."""
import hashlib,json,os,subprocess,time,uuid
from pathlib import Path
BOOT='c2753755-e758-4ab6-a4b6-2929271aa723'
root=Path('/home/root/aura-realtime-vision-20261007')
state=json.loads((root/'current.json').read_text())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert state['after']['boot_id']!=BOOT
release=Path(state['release'])
assert release==root/'releases/mirror-0c1d48dd418e922d' and not release.is_symlink()
stages=[json.loads(p.read_text()) for p in (root/'staged.json',root/'motion-staged.json') if p.exists()]
matches=[s for s in stages if s['release']==str(release)]
assert len(matches)==1
for name,digest in matches[0]['hashes'].items():
 assert '/' not in name and not (release/name).is_symlink()
 assert hashlib.sha256((release/name).read_bytes()).hexdigest()==digest
def owners():
 result=[]
 for p in Path('/proc').iterdir():
  if p.name.isdecimal():
   try:
    if any(f.resolve()==Path('/dev/video0') for f in (p/'fd').iterdir()):result.append(int(p.name))
   except (FileNotFoundError,PermissionError):pass
 return sorted(result)
def apps():
 p=subprocess.run(['xmutil','listapps'],capture_output=True,text=True,timeout=12);p.check_returncode()
 a=[r.split()[0] for r in p.stdout.splitlines() if r.split() and r.split()[-1].rstrip(',')=='0']
 assert a==['aura-visual-servo-b4096-v1'],a
 return p.stdout
assert owners()==[] and Path('/dev/video0').exists()
before_apps=apps()
preflight=subprocess.run(['python3','-B',str(release/'realtime_vision.py'),'--preflight'],capture_output=True,text=True,timeout=30)
assert preflight.returncode==0,(preflight.stdout,preflight.stderr)
assert json.loads(preflight.stdout)['passed']
# Ask Xorg to re-probe EDID, then choose 1024x600 only if actually offered.
xr=subprocess.run(['xrandr','--display',':0','--verbose'],capture_output=True,text=True,timeout=15);xr.check_returncode()
if '1024x600' in xr.stdout:
 subprocess.run(['xrandr','--display',':0','--output','DP-1','--mode','1024x600','--primary'],check=True,timeout=15)
for cmd in [['xset','-display',':0','dpms','force','on'],['xset','-display',':0','s','reset']]:
 subprocess.run(cmd,check=True,timeout=10)
run=root/'runs'/('newboot-mirror-'+uuid.uuid4().hex);run.mkdir()
(run/'previous-state.json').write_text(json.dumps(state))
(run/'preflight.json').write_text(preflight.stdout)
with (run/'worker.log').open('ab') as log:
 p=subprocess.Popen(['python3','-u',str(release/'realtime_vision.py'),'--run-root',str(run),'--mirror-horizontal'],env=dict(os.environ,DISPLAY=':0'),stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
(run/'vision.pid').write_text(str(p.pid))
try:
 deadline=time.monotonic()+25;first=None
 while time.monotonic()<deadline:
  assert p.poll() is None,(run/'worker.log').read_text()[-1500:]
  if (run/'status.json').exists():
   s=json.loads((run/'status.json').read_text());assert not s['error'],s['error']
   if s['detector_ready'] and s['detected_frames']>=3 and s['rendered_frames']>=3:first=s;break
  time.sleep(.2)
 assert first,'Preview not ready'
 time.sleep(3);after=json.loads((run/'status.json').read_text())
 assert after['boot_id']==BOOT and after['epoch']!=state['after']['epoch']
 assert not after['error'] and not after['stopped'] and p.poll() is None
 assert after['mirror_horizontal'] and after['detector_input_size']==[192,192] and after['detector_cpu_threads']==2
 assert not after['actuation_authorized'] and not after['motion_command_emitted'] and after['motion_simulation'] is None
 assert owners()==[p.pid] and apps()==before_apps
 for k in ('capture_frames','detected_frames','display_frames','rendered_frames'):assert after[k]>first[k],k
 restored=dict(pid=p.pid,run_root=str(run),release=str(release),scope='MIRRORED_VIDEO_PREVIEW_ONLY',previous_boot=state['after']['boot_id'],before=first,after=after,passed=True,rollback=False,physical_reference_valid=False)
 t=root/'current-restore.tmp';t.write_text(json.dumps(restored));t.replace(root/'current.json')
 print(json.dumps(dict(restored,fpga_modified=False,motion_command_emitted=False)))
except BaseException:
 if p.poll() is None:p.terminate();p.wait(timeout=10)
 print(json.dumps({'passed':False,'worker_log':(run/'worker.log').read_text()[-2000:],'new_worker_stopped':p.poll() is not None}))
 raise
