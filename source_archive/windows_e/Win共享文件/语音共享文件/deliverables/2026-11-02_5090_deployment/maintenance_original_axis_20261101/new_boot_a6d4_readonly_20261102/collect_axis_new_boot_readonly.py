"""Inspect existing platform/config metadata only; never import actuator modules."""
import datetime
import hashlib
import http.client
import json
from pathlib import Path
import subprocess
import time

B=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
S=B/'startup/config.json';A=B/'runtime/aura'
EXPECTED_NEW_BOOT='a6d4a069-e9b0-4065-8df7-dc23556b168e'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def text_file(path):
    p=Path(path)
    return p.read_bytes().rstrip(b'\0\n').decode('utf-8','replace') if p.is_file() else None
def load(p):
    p=Path(p);assert p.suffix not in ('.db','.sqlite','.sqlite3') and p.is_file() and not p.is_symlink() and p.stat().st_size<64000000
    return json.loads(p.read_bytes())
def get(port,path):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
    try:
        c.request('GET',path);r=c.getresponse();raw=r.read(2097153)
        if r.status!=200 or len(raw)>2097152:return dict(reachable=False,http_status=r.status)
        return dict(reachable=True,value=json.loads(raw))
    except (OSError,TimeoutError,http.client.HTTPException,ValueError) as e:
        return dict(reachable=False,error_type=type(e).__name__)
    finally:c.close()
def unit(name):
    p=subprocess.run(['systemctl','show',name,'--property=MainPID,ActiveState,SubState,Result,Job,ExecMainStatus'],
        capture_output=True,text=True,timeout=4)
    return dict(v.split('=',1) for v in p.stdout.splitlines() if '=' in v)
def process(pid):
    p=Path('/proc')/str(pid)
    try:
        cmd=(p/'cmdline').read_bytes();parts=(p/'stat').read_text().rsplit(')',1)[1].split()
        maps=(p/'maps').read_text();libs=[]
        for line in maps.splitlines():
            if any(x in line for x in ('libvart','libaura_native_operator','libvsrv')):
                path=line.split()[-1]
                if path not in libs:libs.append(path)
        devices=[]
        for fd in (p/'fd').iterdir():
            try:
                target=str(fd.readlink())
                if target.startswith(('/dev/dri/renderD','/dev/dpu')) or target=='/dev/mem':devices.append(target)
            except FileNotFoundError:pass
        return dict(pid=int(pid),birth=parts[19],cmd_sha256=hashlib.sha256(cmd).hexdigest(),
            ppid=int(parts[1]),native_libraries=libs,hardware_descriptors=sorted(set(devices)))
    except (FileNotFoundError,ProcessLookupError):return dict(pid=int(pid),alive=False)
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
started_ms=round(time.monotonic()*1000);startup_before=sha(S);startup=load(S);pins=startup['component_sha256']
components_bad=[]
for k,v in pins.items():
    try:
        if sha(A/k)!=v:components_bad.append(k)
    except OSError:components_bad.append(k)
face=load(A/'config/pan_face.local.json');root=Path(face['release_root']);manifest=load(root/'deployment-manifest.json')
controller_bad=[]
for f in manifest['files']:
    p=Path(f['destination']);p.relative_to(root)
    if not p.is_file() or sha(p)!=f['sha256'] or p.stat().st_size!=f['bytes']:controller_bad.append(str(p))
pan_pins={}
for name,pin in pins.items():
    if name.startswith('config/pan_'):
        p=A/name;v=load(p);pan_pins[name]=dict(path=str(p),pin_sha256=pin,actual_sha256=sha(p),config=v)
arguments=face['arguments'];context_path=Path(arguments['context']);context=load(context_path)
evidence={}
for name in ('direction-evidence','human-evidence'):
    p=Path(arguments[name]);v=load(p)
    evidence[name]=dict(path=str(p),sha256=sha(p),fields={k:v.get(k) for k in
        ('boot_id','board_boot_id','status','axis_camera_mirrored_control_polarity','physical_direction_verified','motion_verified') if k in v},keys=sorted(v))
zone_path=Path(arguments['zone-settings']);zone=load(zone_path)
zone_projection={k:zone.get(k) for k in ('board_boot_id','left_camera_ratio','left_ratio','right_ratio','target_center_ratio',
    'center_tolerance_ratio','frame_width','frame_height','mirror_horizontal')}
platform=dict(fdt_sha256=sha('/sys/firmware/fdt'),firmware_name=text_file('/proc/device-tree/fpga-full/firmware-name'),
    fpga_state=text_file('/sys/class/fpga_manager/fpga0/state'),vart_conf=text_file('/etc/vart.conf'),overlays=[])
overlays=Path('/sys/kernel/config/device-tree/overlays')
if overlays.is_dir():
    for p in sorted(overlays.iterdir()):platform['overlays'].append(dict(name=p.name,status=text_file(p/'status')))
for name,path in (('zocl_driver','/sys/bus/platform/drivers/zocl-drm/axi:zyxclmm_drm'),('render_device','/sys/class/drm/renderD128/device')):
    p=Path(path);platform[name]=str(p.resolve()) if p.exists() else None
units={name:unit(name) for name in ('aura-avatar-ui.service','aura-camera-ui.service','aura-face-zone-editor.service')}
owners=[]
main_pids=[int(v.get('MainPID') or 0) for v in units.values() if int(v.get('MainPID') or 0)>0]
for pid in main_pids:owners.append(process(pid))
known={v['pid'] for v in owners}
follow_owners=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        cmd=(p/'cmdline').read_bytes()
        if (str(root/'run_face_motion.py').encode()+b'\0') in cmd:follow_owners.append(process(int(p.name)))
        if b'board_avatar_gtk.py\0' in cmd and int(p.name) not in known:
            owners.append(process(int(p.name)));known.add(int(p.name))
    except (FileNotFoundError,ProcessLookupError):pass
gui=get(8783,'/api/state');gui_projection=dict(reachable=gui['reachable'])
if gui['reachable']:
    state=gui['value'];pan=state.get('manual_pan') or {};faults=state.get('runtime_faults') or {}
    gui_projection.update(ui_page=state.get('ui_page'),manual_pan={k:pan.get(k) for k in
        ('state','automatic_following','error','pulse_us','target_us','readback','backend_pid')},
        runtime_fault_count=faults.get('count') if isinstance(faults,dict) else None)
else:gui_projection.update({k:v for k,v in gui.items() if k!='value'})
camera=get(8790,'/health');camera_projection=dict(reachable=camera['reachable'])
if camera['reachable']:
    h=camera['value'];camera_projection.update({k:h.get(k) for k in
        ('pid','board_boot_id','camera_epoch','service_epoch','camera_error','detector_error','capture_frames','detected_frames','motion_command_emitted')})
ui=load(A/'config/board_avatar_gtk.json');selected_spec=ui.get('board_business',{}).get('face_readback') or {}
selected={}
if selected_spec.get('path'):
    p=Path(selected_spec['path']);v=load(p);source_pins=v.get('source_sha256') or {}
    bad=[]
    for name,pin in source_pins.items():
        try:
            if sha(name)!=pin:bad.append(name)
        except OSError:bad.append(name)
    selected=dict(path=str(p),configured_sha256=selected_spec.get('sha256'),actual_sha256=sha(p),
        fields={k:v.get(k) for k in ('board_boot_id','camera_pid','camera_start_ticks','camera_config')},
        source_pin_count=len(source_pins),bad_source_pins=bad)
    run_path=v.get('camera_config')
    if run_path:selected['camera_config_sha256']=sha(run_path)
compatibility=dict(context_boot_matches=context.get('boot_id')==boot,context_fdt_matches=context.get('fdt_sha256')==platform['fdt_sha256'],
    context_firmware_matches=context.get('firmware_name')==platform['firmware_name'],
    expected_wide_firmware_loaded=platform['firmware_name']=='aura-visual-servo-b4096-wide-v1.bit.bin',
    expected_wide_vart_selected=platform['vart_conf']=='firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-wide-v1/aura-visual-servo-b4096-wide-v1.xclbin',
    zone_boot_matches=zone.get('board_boot_id')==boot,
    direction_boot_matches=evidence['direction-evidence']['fields'].get('boot_id')==boot,
    human_evidence_boot_matches=evidence['human-evidence']['fields'].get('boot_id')==boot)
print(json.dumps(dict(schema='aura-axis-new-boot-readonly-assessment-1',board_wall_utc_untrusted=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    observation_monotonic_ms=round(time.monotonic()*1000),started_monotonic_ms=started_ms,boot_id=boot,expected_new_boot_matches=boot==EXPECTED_NEW_BOOT,
    startup_path=str(S),startup_sha256_before=startup_before,startup_sha256_after=sha(S),startup_stable=startup_before==sha(S),
    components_count=len(pins),bad_components=components_bad,pan_component_pins=pan_pins,
    controller_root=str(root),controller_manifest_sha256=sha(root/'deployment-manifest.json'),configured_controller_manifest_sha256=face['manifest_sha256'],
    controller_file_count=len(manifest['files']),bad_controller_files=controller_bad,
    follow_arguments=arguments,axis_context=dict(path=str(context_path),sha256=sha(context_path),data=context),
    evidence=evidence,zone=dict(path=str(zone_path),sha256=sha(zone_path),fields=zone_projection),
    platform=platform,units=units,owners=owners,follow_processes=follow_owners,gui=gui_projection,camera=camera_projection,
    selected_face_readback=selected,compatibility=compatibility,
    board_mutations=False,axis_commands_sent=False,device_or_actuator_modules_opened=False,services_changed=False,
    source_or_config_files_written=False,private_content_exported=False)))
