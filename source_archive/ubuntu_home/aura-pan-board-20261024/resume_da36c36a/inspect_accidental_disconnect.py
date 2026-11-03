import hashlib,json,os,signal,subprocess,time
from pathlib import Path
BOOT=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')
units={}
for name in ('aura-avatar-ui.service','aura-camera-ui.service','aura-face-zone-editor.service'):
 raw=subprocess.run(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','SubState','-p','Result','-p','ExecStart'],capture_output=True,text=True,timeout=3)
 units[name]=dict(x.split('=',1) for x in raw.stdout.splitlines() if '=' in x)
controllers=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  argv=(proc/'cmdline').read_bytes().split(b'\0')
  scripts=[Path(os.fsdecode(x)) for x in argv if x.endswith(b'/run_face_motion.py')]
  if not scripts:continue
  script=scripts[0];script.relative_to(F)
  stat=(proc/'stat').read_text().rsplit(')',1)[1].split();group=(proc/'cgroup').read_text()
  row={'pid':int(proc.name),'script':str(script),'birth_ticks':int(stat[19]),'owned_gui_cgroup':'aura-avatar-ui.service' in group}
  if row['owned_gui_cgroup']:
   fd=os.pidfd_open(row['pid'])
   try:
    assert (proc/'stat').read_text().rsplit(')',1)[1].split()[19]==stat[19]
    signal.pidfd_send_signal(fd,signal.SIGTERM);row['TERM_requested']=True
   finally:os.close(fd)
  controllers.append(row)
 except (OSError,ValueError,ProcessLookupError):continue
end=time.monotonic()+4
while time.monotonic()<end and any(Path('/proc',str(r['pid'])).exists() for r in controllers):time.sleep(.1)
for r in controllers:r['process_still_present']=Path('/proc',str(r['pid'])).exists()
reports=[]
for root in ('continuous-v11r1','continuous-v10r15'):
 files=sorted((F/root/'runs').glob('*/trial.json'),key=lambda p:p.stat().st_mtime,reverse=True)
 if files:
  try:
   d=json.loads(files[0].read_text());v=d.get('result') or {}
   reports.append({'path':str(files[0]),'boot_id':d.get('boot_id'),'manifest_sha256':d.get('consumer_manifest_sha256'),
    'status':d.get('status'),'state':v.get('state'),'reason':v.get('reason'),'pulse_us':v.get('pulse_us'),
    'readback':v.get('readback'),'stopped':v.get('stopped'),'commands_accepted':v.get('commands_accepted'),
    'motion_target_changes':v.get('motion_target_changes'),'error':d.get('error')})
  except (OSError,ValueError):pass
owners=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  if any(os.path.realpath(fd)=='/dev/mem' for fd in (proc/'fd').iterdir()):owners.append(int(proc.name))
 except OSError:pass
fw=Path('/proc/device-tree/fpga-full/firmware-name')
print(json.dumps({'boot_id':BOOT,'units':units,'controllers':controllers,'latest_reports':reports,'mmio_owner_pids':owners,
 'firmware':fw.read_bytes().rstrip(b'\0').decode() if fw.exists() else None,
 'camera_nodes':[str(x) for x in Path('/dev').glob('video*')],
 'commands_sent':['SIGTERM_TO_VERIFIED_FACE_OWNER'] if controllers else [],'ARM_sent':False,'COMMIT_sent':False,
 'actual_mechanical_angle_known':False}))
