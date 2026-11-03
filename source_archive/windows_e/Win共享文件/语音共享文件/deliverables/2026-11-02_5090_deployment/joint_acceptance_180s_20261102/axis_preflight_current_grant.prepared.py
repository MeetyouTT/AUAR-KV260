import base64,hashlib,json
from pathlib import Path
GRANT=json.loads(base64.b64decode('eyJzY2hlbWEiOiAiYXVyYS11c2VyLXVuZnJvemVuLWF4aXMtZnVsbC1hY2NlcHRhbmNlLWhhbmRvZmYtMSIsICJpc3N1ZWRfaG9zdF91dGMiOiAiMjAyNi0xMS0wMlQxNzo0NjozMy42NTc5MDcrMDA6MDAiLCAibWF5X2JlZ2luX3ByZWZsaWdodF9iZWZvcmVfaG9zdF91dGMiOiAiMjAyNi0xMS0wMlQxNzo1NjozMy42NTc5MDcrMDA6MDAiLCAidXNlcl9leHBsaWNpdF9yZXF1ZXN0IjogIlVuZnJlZXplIGF4aXMgZm9yIGZ1bGwtcHJvY2VzcyBhY2NlcHRhbmNlIiwgInVzZXJfcGh5c2ljYWxfY29uZmlybWF0aW9uIjogeyJtb3Rvcl9wb3dlcl9jb25uZWN0ZWQiOiB0cnVlLCAiaW5zdGFsbGF0aW9uX3VuY2hhbmdlZCI6IHRydWUsICJzcGFjZV9hbmRfY2FibGVfbWFyZ2luX3N1ZmZpY2llbnQiOiB0cnVlLCAib2JzZXJ2ZXJfcHJlc2VudF9jYW5fZGlzY29ubmVjdF9wb3dlciI6IHRydWV9LCAic29sZV9heGlzX29wZXJhdG9yX3RocmVhZCI6ICIwMWExOWI2NC04MTk0LTcwZTMtODA2Yi0wM2ZhOWEyODM5MTgiLCAiZ3JhbnQiOiAiRXhjbHVzaXZlIGZyZXNoIGF4aXMvcGxhdGZvcm0vc291cmNlL1NUT1AgcHJlZmxpZ2h0LiBPcmlnaW5hbCBwYW5fc3RvcCBvbmx5IGlmIG5lZWRlZCB0byBlc3RhYmxpc2ggcHJvdGVjdGVkIHN0b3AuIFJlcG9ydCByZWFkaW5lc3MgYmVmb3JlIHN0YXJ0aW5nIG9yaWdpbmFsIGZvbGxvd2luZy4iLCAibm9fbmV3X21vdGlvbl91bnRpbF9yZWFkeV9yZXBvcnQiOiB0cnVlLCAibm9fREZYX2luaXRpYWxpemF0aW9uX3JlY2VudGVyaW5nX29yX3NvdXJjZV9jaGFuZ2VzX2luX3RoaXNfcHJlZmxpZ2h0X2dyYW50IjogdHJ1ZSwgImlmX2luY29tcGF0aWJsZV9wbGF0Zm9ybSI6ICJSZXBvcnQgY3VycmVudCBldmlkZW5jZSBhbmQgcmVjb3ZlcnkgcHJlcmVxdWlzaXRlIGJlZm9yZSBhbnkgZmlybXdhcmUgb3Igc2VydmljZSBhY3Rpb247IG1vdG9yIGN1cnJlbnRseSBwb3dlcmVkLiIsICJyb290X2FsbF9ib2FyZF9jYWxsc19wYXVzZWRfYWZ0ZXJfaGFuZG9mZiI6IHRydWUsICJjcHVfYm9vdF9hbmRfR1VJX2xheW91dF9kZXZpY2VfY2hhbmdlc19yZW1haW5fZnJvemVuIjogdHJ1ZSwgImJvb3RfaWQiOiAiYTZkNGEwNjktZTliMC00MDY1LThkZjctZGMyMzU1NmIxNjhlIiwgInN0YXJ0dXBfc2hhMjU2IjogImQ2NjdiODcxZTE1OWE5ZjJiNTJjZmI0OGExNmEzMWJhMzk4NDdlNGQ2ODY1OGE1MjFhZWUwMDZlN2RiOTE1ZWYiLCAiZ3VpX293bmVyIjogeyJwaWQiOiAzMTM2OTMsICJiaXJ0aF90aWNrcyI6ICIyMjczMTU3IiwgImNvbW1hbmRfc2hhMjU2IjogIjQ4YTI4ZWZhMzJiMjA1MDkwMWU3M2U4NWE4MGEzMGE5MGRjZmJjZTBiNzI0OWJkZTVkNmQ5MDkwMjc0MDYzMWQifSwgImd0a19vd25lciI6IHsicGlkIjogMzEzNzQyLCAiYmlydGhfdGlja3MiOiAiMjI3ODU1NiIsICJjb21tYW5kX3NoYTI1NiI6ICI5NDdlNzQwYzIyZDJjN2M2ZmMyNTE1N2EyM2QwMDIxOTdkNTM0NWVjZTk2N2RlYTQyYWRkNGM1YTU0ZmRjNTU3In0sICJjYW1lcmFfb3duZXIiOiB7InBpZCI6IDEzMzIsICJiaXJ0aF90aWNrcyI6ICIyMjM2IiwgImNvbW1hbmRfc2hhMjU2IjogImFjZjNlZTEyM2Q3Njc0ZmRlYTZlOTBlNzkyNTI5MDljYTM5NjI0OWM4NzAyNjkxNjk5MTA4NzlkOTQwYzI3ZGQifSwgInNlbGVjdGVkX2ZhY2VfYmluZGluZyI6IHsicGF0aCI6ICIvaG9tZS9yb290L2F1cmEtNTA5MC1yZWNvdmVyeS0yMDI2MTEwMi1hNmQ0YTA2OS9ndWktc2VsZWN0ZWQtMTMzMi0yNnBpbnMtdjEvZmFjZV9nYWxsZXJ5X3JlYWRiYWNrLmxvY2FsLmpzb24iLCAic2hhMjU2IjogIjk5YzUzYzU5OTIzNTVhMmE0ZGZkZWRjZWIzY2M5MGQ4MTM5ODEzMjg0NTZiOTg3ZTUwMzQ1OWZlNmQwNjkxYjUiLCAiY29uZmlndXJlZF9zaGFfbWF0Y2hlcyI6IHRydWUsICJzb3VyY2VfcGluX2NvdW50IjogMjYsICJzb3VyY2VfYW5kX2xpdmVfb3duZXJfdmVyaWZpZWQiOiB0cnVlfSwgImZ1bGxfMzgwX3BpbnNfcmVjZWlwdCI6ICIuLi9GVUxMX0FDQ0VQVEFOQ0VfUFJFRkxJR0hUX1JFU1VMVC5qc29uIiwgImxpc3RlbmluZ19lbmFibGVkIjogZmFsc2UsICJtaWNyb3Bob25lX29wZW4iOiBmYWxzZSwgInBsYXliYWNrX2FuZF9idXNpbmVzc19qb2JzX2lkbGUiOiB0cnVlLCAiZmFjZV9hbmRfdm9pY2Vfc2FtcGxpbmdfaWRsZSI6IHRydWUsICJwcmVzZXJ2ZV92b2ljZV90aHJlc2hvbGQiOiAwLjM1LCAicHJlc2VydmVfZGFpbHlfc2luZ2xlX3NlbnRlbmNlX2FkZHJlc3MiOiB0cnVlLCAicHJlc2VydmVfbW9kZWxzX2JhY2tlbmRfYW5kX2Zvcm1hbF9pZGVudGl0aWVzIjogdHJ1ZSwgImZhY2Vfdm9pY2VfbGlua2luZ19leGNsdWRlZCI6IHRydWUsICJzY2VuZV9tYWluX3BhZ2VfbGFzdF9vYnNlcnZlZCI6IGZhbHNlLCAiYXZhdGFyX3Zpc2libGVfbGFzdF9vYnNlcnZlZCI6IGZhbHNlLCAic2NlbmVfbm90ZSI6ICJObyBwYWdlIGNoYW5nZSBtYWRlIGJ5IHJvb3Q7IHJlYWQgYWN0dWFsIHBhZ2UgYmVmb3JlIFVJIGFjY2VwdGFuY2UuIn0='))
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==GRANT['boot_id']
_axis_startup=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
assert hashlib.sha256(_axis_startup.read_bytes()).hexdigest()==GRANT['startup_sha256']
for _axis_key in ('gui_owner','gtk_owner','camera_owner'):
    _axis_owner=GRANT[_axis_key];_axis_p=Path('/proc')/str(_axis_owner['pid'])
    assert _axis_p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==_axis_owner['birth_ticks']
    assert hashlib.sha256(_axis_p.joinpath('cmdline').read_bytes()).hexdigest()==_axis_owner['command_sha256']
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
out = dict(schema='aura-axis-new-boot-readonly-assessment-1', board_wall_utc_untrusted=datetime.datetime.now(datetime.timezone.utc).isoformat(), observation_monotonic_ms=round(time.monotonic() * 1000), started_monotonic_ms=started_ms, boot_id=boot, expected_new_boot_matches=boot == EXPECTED_NEW_BOOT, startup_path=str(S), startup_sha256_before=startup_before, startup_sha256_after=sha(S), startup_stable=startup_before == sha(S), components_count=len(pins), bad_components=components_bad, pan_component_pins=pan_pins, controller_root=str(root), controller_manifest_sha256=sha(root / 'deployment-manifest.json'), configured_controller_manifest_sha256=face['manifest_sha256'], controller_file_count=len(manifest['files']), bad_controller_files=controller_bad, follow_arguments=arguments, axis_context=dict(path=str(context_path), sha256=sha(context_path), data=context), evidence=evidence, zone=dict(path=str(zone_path), sha256=sha(zone_path), fields=zone_projection), platform=platform, units=units, owners=owners, follow_processes=follow_owners, gui=gui_projection, camera=camera_projection, selected_face_readback=selected, compatibility=compatibility, board_mutations=False, axis_commands_sent=False, device_or_actuator_modules_opened=False, services_changed=False, source_or_config_files_written=False, private_content_exported=False)

# No motion or configuration action occurs in this stage. STOP is conditional.
def stop_ready(pan):
    rb=pan.get('readback') or {}
    return (pan.get('automatic_following') is False and pan.get('state')=='READY' and not pan.get('error')
        and rb.get('flags')==0 and rb.get('lease_left_ms')==0 and rb.get('reason')==0)
pan=(out.get('gui') or {}).get('manual_pan') or {};rb=pan.get('readback') or {}
out['preflight_pan_before_stop']=dict(pan);stop_sent=False
need_stop=pan.get('automatic_following') is True or bool(rb and (rb.get('flags') or rb.get('lease_left_ms')))
if need_stop:
    assert sha(S)==GRANT['startup_sha256']
    c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
    try:
        c.request('POST','/api/command',b'{"type":"pan_stop"}',{'Origin':'http://127.0.0.1:8783','Host':'127.0.0.1:8783','Content-Type':'application/json'})
        r=c.getresponse();r.read(2097153);assert r.status==200;stop_sent=True
    finally:c.close()
    end=time.monotonic()+12
    while True:
        result=get(8783,'/api/state');assert result['reachable']
        actual=result['value']['manual_pan']
        pan={k:actual.get(k) for k in ('state','automatic_following','error','pulse_us','target_us','readback','backend_pid')}
        out['gui']['manual_pan']=pan
        if stop_ready(pan):break
        if time.monotonic()>=end:break
        time.sleep(.25)
out['original_pan_stop_sent_once']=stop_sent;out['axis_commands_sent']=int(stop_sent)
out['board_mutations']=stop_sent
out['new_follow_start_sent']=False;out['DFX_or_service_change']=False
out['reference_or_initialization_or_parameter_change']=False
out['accepted_parameters_match']=(arguments.get('left-target-center-ratio')=='0.40'
    and arguments.get('target-center-ratio')=='0.45' and arguments.get('rearm-stability-ms')=='150'
    and out['controller_manifest_sha256']=='9cd35b967bf9c859ed3f1f4de4dc5dad199e81ddfed845435fc8745a41be0ba9')
manual_cfg=pan_pins.get('config/pan_manual.local.json',{}).get('config') or {}
out['manual_binding_matches_current_platform']=(manual_cfg.get('boot_id')==boot
    and manual_cfg.get('fdt_sha256')==platform['fdt_sha256'])
out['current_stop_readback_verified']=stop_ready(pan)
out['fresh_root_startup_matches']=sha(S)==GRANT['startup_sha256']
out['selected_binding_matches_root_handoff']=(selected.get('actual_sha256')==GRANT['selected_face_binding']['sha256']
    and not selected.get('bad_source_pins') and selected.get('fields',{}).get('board_boot_id')==boot
    and selected.get('fields',{}).get('camera_pid')==GRANT['camera_owner']['pid']
    and str(selected.get('fields',{}).get('camera_start_ticks'))==GRANT['camera_owner']['birth_ticks'])
# Optional narrow layout source/geometry metadata: no window title or image export.
layout=dict(inspected_source=False,window_moved=False,gui_reloaded=False)
editor_pid=int(units.get('aura-face-zone-editor.service',{}).get('MainPID') or 0)
if editor_pid:
    try:
        cmd=Path('/proc',str(editor_pid),'cmdline').read_bytes().split(b'\0')
        script=next((Path(x.decode()) for x in cmd if x.endswith(b'face_zone_editor.py')),None)
        layout.update(pid=editor_pid,owner=process(editor_pid))
        if script and script.is_file() and script.stat().st_size<100000:
            text=script.read_text();lines=text.splitlines()
            layout.update(inspected_source=True,script=str(script),source_sha256=sha(script),
                relevant_source_lines=[dict(line=i+1,text=line[:220]) for i,line in enumerate(lines)
                    if any(token in line for token in ('set_default_size','set_keep_above','window.move(','set_size_request','position_text','face_position'))][:16])
        env={}
        gtk_env=Path('/proc',str(GRANT['gtk_owner']['pid']),'environ').read_bytes().split(b'\0')
        for item in gtk_env:
            if item.startswith((b'DISPLAY=',b'XAUTHORITY=')):
                key,value=item.decode().split('=',1);env[key]=value
        if env.get('DISPLAY'):
            import os,re
            penv=dict(os.environ,**env)
            listing=subprocess.run(['xprop','-root','_NET_CLIENT_LIST'],env=penv,capture_output=True,text=True,timeout=2)
            for wid in re.findall(r'0x[0-9a-fA-F]+',listing.stdout)[:24]:
                p=subprocess.run(['xprop','-id',wid,'_NET_WM_PID'],env=penv,capture_output=True,text=True,timeout=1)
                nums=re.findall(r'\d+',p.stdout.split('=',1)[-1]) if '=' in p.stdout else []
                if nums and int(nums[0])==editor_pid:
                    win=subprocess.run(['xwininfo','-id',wid,'-stats'],env=penv,capture_output=True,text=True,timeout=2)
                    geom={}
                    for key,pattern in (('x',r'Absolute upper-left X:\s+(-?\d+)'),('y',r'Absolute upper-left Y:\s+(-?\d+)'),('width',r'Width:\s+(\d+)'),('height',r'Height:\s+(\d+)')):
                        m=re.search(pattern,win.stdout)
                        if m:geom[key]=int(m.group(1))
                    layout.update(window_id=wid,geometry=geom)
                    break
    except (OSError,ValueError,subprocess.TimeoutExpired) as error:layout['optional_metadata_error_type']=type(error).__name__
out['face_position_overlay_metadata']=layout
print(json.dumps(out))
