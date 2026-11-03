"""Read the existing original-client job and actual unload state; never resend it."""
import base64
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

TX=Path('/home/root/aura-5090-recovery-20261102-903cfade/original-axis-restore-v1')
UNIT='aura-original-remove-903c-v1.service'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='903cfade-b93c-48fa-804e-379be1967313'
props='LoadState,Job,ActiveState,SubState,InvocationID,MainPID,ExecMainPID,ExecMainStartTimestampMonotonic,ExecMainExitTimestampMonotonic,ExecMainCode,ExecMainStatus,Result,ExecStart'
p=subprocess.run(['systemctl','show',UNIT,'--property='+props],capture_output=True,text=True,timeout=5)
assert p.returncode==0
state=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
assert state['InvocationID']=='2f576a41a8f44a34b173cbca8305a82a' and state['ExecMainPID']=='79180'
out=(TX/'remove.stdout.raw').read_bytes();err=(TX/'remove.stderr.raw').read_bytes()
assert len(out)<=65536 and len(err)<=65536
overlays=[];root=Path('/sys/kernel/config/device-tree/overlays')
if root.exists():
    for entry in root.iterdir():
        if entry.is_dir():overlays.append({'name':entry.name,'status':(entry/'status').read_text().strip() if (entry/'status').exists() else None})
render=[e.name for e in Path('/sys/class/drm').glob('renderD*')]
bindings=[]
for driver in Path('/sys/bus/platform/drivers').iterdir():
    if 'zocl' in driver.name.lower():
        bindings.extend(str(e) for e in driver.iterdir() if e.is_symlink())
owners=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():continue
    try:
        maps=(proc/'maps').read_text();targets=[]
        for fd in (proc/'fd').iterdir():
            try:targets.append(str(fd.readlink()))
            except FileNotFoundError:continue
        if any(x in maps for x in ('libvart','libaura_native_operator','libvsrv.so')) or any(t.startswith(('/dev/dri/renderD','/dev/dpu')) or t=='/dev/mem' for t in targets):owners.append(int(proc.name))
    except (FileNotFoundError,ProcessLookupError):continue
services={}
for name in ('aura-camera-ui.service','aura-avatar-ui.service'):
    result=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,Job'],capture_output=True,text=True,timeout=4)
    assert result.returncode==0
    services[name]=dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
stopped=all(v=={'MainPID':'0','ActiveState':'inactive','SubState':'dead','Job':''} for v in services.values())
finished=state['ActiveState']=='active' and state['SubState']=='exited' and not state['Job'] and int(state['ExecMainExitTimestampMonotonic'])>int(state['ExecMainStartTimestampMonotonic'])
semantic_ok=out==b'remove from slot 0 returns: 0 (Ok)\n' and not err
os_ok=finished and state['ExecMainCode']=='1' and state['ExecMainStatus']=='0' and state['Result']=='success'
hardware_ok=not overlays and not render and not bindings and not owners and stopped
print(json.dumps({'schema':'aura-original-client-remove-readback-1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status':'REMOVE_CONFIRMED_AND_ACTUAL_PLATFORM_UNLOADED' if os_ok and semantic_ok and hardware_ok else 'PENDING_OR_HOLD',
    'unit':state,'os_exit_confirmed':os_ok,'exact_original_reply_success':semantic_ok,
    'actual_platform_unloaded':hardware_ok,'stdout':out.decode('utf-8','backslashreplace'),'stderr':err.decode('utf-8','backslashreplace'),
    'stdout_base64':base64.b64encode(out).decode(),'stderr_base64':base64.b64encode(err).decode(),
    'stdout_sha256':hashlib.sha256(out).hexdigest(),'stderr_sha256':hashlib.sha256(err).hexdigest(),
    'overlays':overlays,'render_devices':render,'zocl_bound_links':bindings,'native_or_motion_owners':owners,
    'services':services,'vart_after':Path('/etc/vart.conf').read_text(),
    'firmware_after':Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode() if Path('/proc/device-tree/fpga-full/firmware-name').exists() else None,
    'loader_resent':False,'device_opened_by_observer':False}))
