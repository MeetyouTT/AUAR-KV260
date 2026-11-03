"""Read one existing original-client load result and the actual paired platform."""
import base64
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

TX=Path('/home/root/aura-5090-recovery-20261102-903cfade/original-axis-restore-v1')
APP='aura-visual-servo-b4096-wide-v1';UNIT='aura-original-load-903c-v1.service'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='903cfade-b93c-48fa-804e-379be1967313'
props='LoadState,Job,ActiveState,SubState,InvocationID,MainPID,ExecMainPID,ExecMainStartTimestampMonotonic,ExecMainExitTimestampMonotonic,ExecMainCode,ExecMainStatus,Result,ExecStart'
p=subprocess.run(['systemctl','show',UNIT,'--property='+props],capture_output=True,text=True,timeout=5)
assert p.returncode==0
state=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
assert state['InvocationID']=='990d648e43ee4a9fb5cf9f6066ba2156' and state['ExecMainPID']=='79397'
out=(TX/'load.stdout.raw').read_bytes();err=(TX/'load.stderr.raw').read_bytes()
assert len(out)<=65536 and len(err)<=65536
overlays=[];root=Path('/sys/kernel/config/device-tree/overlays')
for entry in root.iterdir():
    if entry.is_dir():overlays.append({'name':entry.name,'status':(entry/'status').read_text().strip() if (entry/'status').exists() else None})
render=[{'name':e.name,'device':str((e/'device').resolve())} for e in Path('/sys/class/drm').glob('renderD*')]
bindings=[];module_links=[];unexpected=[]
for driver in Path('/sys/bus/platform/drivers').iterdir():
    if 'zocl' not in driver.name.lower():continue
    for entry in driver.iterdir():
        if not entry.is_symlink():continue
        target=str(entry.resolve())
        if target.startswith('/sys/devices/'):bindings.append({'path':str(entry),'device':target})
        elif entry.name=='module' and target.startswith('/sys/module/'):module_links.append(str(entry))
        else:unexpected.append({'path':str(entry),'target':target})
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
release=Path('/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c')
manifest_raw=(release/'candidate-manifest.json').read_bytes()
assert hashlib.sha256(manifest_raw).hexdigest()=='6a4b645a5bbfd35c9107976edf27886cf8e0c91e40f48be6f052a95e1172c1cf'
manifest=json.loads(manifest_raw)
runtime_ok=all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected for path,expected in manifest['runtime_files'].items())
drivers_ok=all(hashlib.sha256((release/'driver'/name).read_bytes()).hexdigest()==expected for name,expected in manifest['payload_files'].items())
xclbin=[path for path in manifest['runtime_files'] if path.endswith('.xclbin')];assert len(xclbin)==1
vart=Path('/etc/vart.conf').read_bytes();vart_ok=vart==('firmware: '+xclbin[0]+'\n').encode()
fw_path=Path('/proc/device-tree/fpga-full/firmware-name')
firmware=fw_path.read_bytes().rstrip(b'\0').decode() if fw_path.exists() else None
fpga=Path('/sys/class/fpga_manager/fpga0/state').read_text().strip()
finished=state['ActiveState']=='active' and state['SubState']=='exited' and not state['Job'] and int(state['ExecMainExitTimestampMonotonic'])>int(state['ExecMainStartTimestampMonotonic'])
os_ok=finished and state['ExecMainCode']=='1' and state['ExecMainStatus']=='0' and state['Result']=='success'
semantic_ok=out==(APP+': loaded to slot 0\n').encode() and not err
zocl_tree_ok=(len(render)==1 and sum(b['device']==render[0]['device'] for b in bindings)==1
    and all(b['device']==render[0]['device'] or b['device'].startswith(render[0]['device']+'/') for b in bindings))
hardware_ok=(runtime_ok and drivers_ok and vart_ok and fpga=='operating' and firmware==APP+'.bit.bin'
    and len(overlays)==1 and overlays[0]['name'].startswith(APP+'_image_') and overlays[0]['status']=='applied'
    and zocl_tree_ok
    and not owners and not unexpected and stopped)
print(json.dumps({'schema':'aura-original-client-load-readback-1','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status':'LOAD_CONFIRMED_ORIGINAL_WIDE_PLATFORM_ACTIVE' if os_ok and semantic_ok and hardware_ok else 'PENDING_OR_HOLD',
    'unit':state,'os_exit_confirmed':os_ok,'exact_original_reply_success':semantic_ok,'actual_paired_wide_platform_verified':hardware_ok,
    'stdout':out.decode('utf-8','backslashreplace'),'stderr':err.decode('utf-8','backslashreplace'),
    'stdout_base64':base64.b64encode(out).decode(),'stderr_base64':base64.b64encode(err).decode(),
    'stdout_sha256':hashlib.sha256(out).hexdigest(),'stderr_sha256':hashlib.sha256(err).hexdigest(),
    'firmware':firmware,'fpga_state':fpga,'vart':vart.decode(),'exact_vart_verified':vart_ok,
    'runtime_files_verified':runtime_ok,'driver_files_verified':drivers_ok,'overlays':overlays,
    'render_devices':render,'zocl_bound_links':bindings,'paired_zocl_parent_and_child_tree_verified':zocl_tree_ok,
    'unexpected_zocl_links':unexpected,
    'native_or_motion_owners':owners,'services':services,'fdt_sha256':hashlib.sha256(Path('/sys/firmware/fdt').read_bytes()).hexdigest(),
    'loader_resent':False,'camera_started':False,'register_accessed':False,'motion_requested':False}))
