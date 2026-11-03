"""Seal exact original checkpoint bytes and read platform state. No loader or MMIO."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

BOOT='903cfade-b93c-48fa-804e-379be1967313'
TX=Path('/home/root/aura-5090-recovery-20261102-903cfade/original-axis-restore-v1')
CP=Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/state/native-protection-checkpoint.json')
SHA='c6c8baab1de423e27740137330f8315796a7778e36735c93a0c87f2a56029471'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
assert not TX.is_symlink() and TX.resolve()==TX
for name in ('aura-avatar-ui.service','aura-camera-ui.service'):
    p=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,Job,Result'],capture_output=True,text=True,timeout=4)
    v=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
    assert p.returncode==0 and v=={'MainPID':'0','ActiveState':'inactive','SubState':'dead','Job':'','Result':'success'}
assert not Path('/proc/1333').exists()
raw=CP.read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
assert not os.path.lexists(str(CP)+'.native-consumed-'+SHA)
sealed=TX/('native-final-'+SHA+'.json')
fd=os.open(sealed,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
fd=os.open(TX,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
assert sealed.read_bytes()==raw and CP.read_bytes()==raw
owners=[];unreadable=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():continue
    try:
        maps=(proc/'maps').read_text();handles=[]
        for file in (proc/'fd').iterdir():
            try:handles.append(str(file.readlink()))
            except FileNotFoundError:continue
        if any(x in maps for x in ('libvart','libaura_native_operator','libvsrv.so')) or any(h.startswith(('/dev/dri/renderD','/dev/dpu')) or h=='/dev/mem' for h in handles):owners.append(int(proc.name))
    except (FileNotFoundError,ProcessLookupError):continue
    except PermissionError:
        if proc.exists():unreadable.append(int(proc.name))
assert not owners and not unreadable
assert hashlib.sha256(Path('/usr/bin/dfx-mgr-client').read_bytes()).hexdigest()=='a37d8449c3362a509d459f9e57aa3711314602369354f7d98ca60c3e51607ad7'
assert hashlib.sha256(Path('/usr/local/lib/kv260-dfx-state-repair-20261003/dfx-mgrd').read_bytes()).hexdigest()=='369c7fb0ddd023a7cf7af14896a7fda6036219a36f4980c73640889720c95dfd'
daemon=Path('/proc/1121');assert (daemon/'stat').read_text().rsplit(')',1)[1].split()[19]=='1516'
assert hashlib.sha256((daemon/'cmdline').read_bytes()).hexdigest()=='eba390fe164718811ee931534079ab55a51a95b5e8092c7600dcf730346d7088'
overlay_root=Path('/sys/kernel/config/device-tree/overlays');overlays=[]
if overlay_root.exists():
    for entry in sorted(overlay_root.iterdir()):
        if entry.is_dir():overlays.append({'name':entry.name,'status':(entry/'status').read_text().strip() if (entry/'status').exists() else None})
drm=[]
for entry in sorted(Path('/sys/class/drm').glob('renderD*')):drm.append({'name':entry.name,'device':str((entry/'device').resolve())})
driver=Path('/sys/bus/platform/drivers/zocl')
zocl=[entry.name for entry in driver.iterdir() if entry.is_symlink()] if driver.exists() else []
print(json.dumps({'schema':'aura-original-platform-seal-and-inventory-1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'boot_id':BOOT,'sealed_checkpoint_path':str(sealed),'sealed_checkpoint_sha256':SHA,'sealed_bytes':len(raw),
    'original_bytes_unchanged':True,'checkpoint_consumed':False,'native_or_motion_owners':owners,
    'unreadable_alive_processes':unreadable,'firmware':Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode(),
    'fpga_state':Path('/sys/class/fpga_manager/fpga0/state').read_text().strip(),
    'vart':Path('/etc/vart.conf').read_text(),'fdt_sha256':hashlib.sha256(Path('/sys/firmware/fdt').read_bytes()).hexdigest(),
    'overlays':overlays,'render_devices':drm,'zocl_driver_links':zocl,
    'daemon_pid':1121,'daemon_birth_ticks':1516,'loader_sent':False,'device_opened':False}))
