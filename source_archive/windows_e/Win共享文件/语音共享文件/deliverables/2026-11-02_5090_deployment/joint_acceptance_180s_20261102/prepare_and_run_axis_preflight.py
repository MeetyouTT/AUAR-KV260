"""Consume the explicit root preflight handoff; never start following here."""
import ast
import base64
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

D=Path('E:/Win共享文件/语音共享文件/deliverables/2026-11-02_5090_deployment')
HERE=Path(__file__).resolve().parent
H=D/'other_components_20261102/live_enrollment_20261102/full_system_acceptance_20261102/AXIS_PREFLIGHT_HANDOFF.json'
h=json.loads(H.read_bytes());now=datetime.datetime.now(datetime.timezone.utc)
assert now<datetime.datetime.fromisoformat(h['may_begin_preflight_before_host_utc']),'Preflight grant expired; no board call'
assert h['sole_axis_operator_thread']=='01a19b64-8194-70e3-806b-03fa9a283918'
assert h['root_all_board_calls_paused_after_handoff'] and h['no_new_motion_until_ready_report']
source_path=D/'maintenance_original_axis_20261101/new_boot_a6d4_readonly_20261102/collect_axis_new_boot_readonly.py'
source=source_path.read_text(encoding='utf-8');tree=ast.parse(source);last=tree.body[-1]
assert isinstance(last,ast.Expr) and isinstance(last.value,ast.Call) and last.value.func.id=='print'
inner=last.value.args[0];assert isinstance(inner,ast.Call) and inner.func.attr=='dumps'
assignment=ast.Assign(targets=[ast.Name(id='out',ctx=ast.Store())],value=inner.args[0]);ast.fix_missing_locations(assignment)
source='\n'.join(source.splitlines()[:last.lineno-1])+'\n'+ast.unparse(assignment)+'\n'
header="""import base64,hashlib,json
from pathlib import Path
GRANT=json.loads(base64.b64decode('GRANT_BASE64'))
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==GRANT['boot_id']
_axis_startup=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
assert hashlib.sha256(_axis_startup.read_bytes()).hexdigest()==GRANT['startup_sha256']
for _axis_key in ('gui_owner','gtk_owner','camera_owner'):
    _axis_owner=GRANT[_axis_key];_axis_p=Path('/proc')/str(_axis_owner['pid'])
    assert _axis_p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==_axis_owner['birth_ticks']
    assert hashlib.sha256(_axis_p.joinpath('cmdline').read_bytes()).hexdigest()==_axis_owner['command_sha256']
""".replace('GRANT_BASE64',base64.b64encode(json.dumps(h).encode()).decode())
tail="""
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
        cmd=Path('/proc',str(editor_pid),'cmdline').read_bytes().split(b'\\0')
        script=next((Path(x.decode()) for x in cmd if x.endswith(b'face_zone_editor.py')),None)
        layout.update(pid=editor_pid,owner=process(editor_pid))
        if script and script.is_file() and script.stat().st_size<100000:
            text=script.read_text();lines=text.splitlines()
            layout.update(inspected_source=True,script=str(script),source_sha256=sha(script),
                relevant_source_lines=[dict(line=i+1,text=line[:220]) for i,line in enumerate(lines)
                    if any(token in line for token in ('set_default_size','set_keep_above','window.move(','set_size_request','position_text','face_position'))][:16])
        env={}
        gtk_env=Path('/proc',str(GRANT['gtk_owner']['pid']),'environ').read_bytes().split(b'\\0')
        for item in gtk_env:
            if item.startswith((b'DISPLAY=',b'XAUTHORITY=')):
                key,value=item.decode().split('=',1);env[key]=value
        if env.get('DISPLAY'):
            import os,re
            penv=dict(os.environ,**env)
            listing=subprocess.run(['xprop','-root','_NET_CLIENT_LIST'],env=penv,capture_output=True,text=True,timeout=2)
            for wid in re.findall(r'0x[0-9a-fA-F]+',listing.stdout)[:24]:
                p=subprocess.run(['xprop','-id',wid,'_NET_WM_PID'],env=penv,capture_output=True,text=True,timeout=1)
                nums=re.findall(r'\\d+',p.stdout.split('=',1)[-1]) if '=' in p.stdout else []
                if nums and int(nums[0])==editor_pid:
                    win=subprocess.run(['xwininfo','-id',wid,'-stats'],env=penv,capture_output=True,text=True,timeout=2)
                    geom={}
                    for key,pattern in (('x',r'Absolute upper-left X:\\s+(-?\\d+)'),('y',r'Absolute upper-left Y:\\s+(-?\\d+)'),('width',r'Width:\\s+(\\d+)'),('height',r'Height:\\s+(\\d+)')):
                        m=re.search(pattern,win.stdout)
                        if m:geom[key]=int(m.group(1))
                    layout.update(window_id=wid,geometry=geom)
                    break
    except (OSError,ValueError,subprocess.TimeoutExpired) as error:layout['optional_metadata_error_type']=type(error).__name__
out['face_position_overlay_metadata']=layout
print(json.dumps(out))
"""
remote=header+source+tail;ast.parse(remote)
script=HERE/'axis_preflight_current_grant.prepared.py';assert not script.exists();script.write_text(remote,encoding='utf-8')
transport=D.parent/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('axis_joint_ssh',transport);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
started=datetime.datetime.now(datetime.timezone.utc)
assert started<datetime.datetime.fromisoformat(h['may_begin_preflight_before_host_utc']),'Preflight grant expired; no board call'
result=json.loads(m.ssh('python3 -B -',remote,timeout=55));end=datetime.datetime.now(datetime.timezone.utc).isoformat()
raw=dict(host_started_utc=started.isoformat(),host_completed_utc=end,handoff_path=str(H),handoff_sha256=hashlib.sha256(H.read_bytes()).hexdigest(),
    source_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),board_result=result)
p=HERE/'AXIS_PREFLIGHT_ACTUAL.json';assert not p.exists();p.write_text(json.dumps(raw,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
compat=result['compatibility'];blockers=[]
if not compat['expected_wide_firmware_loaded'] or not compat['expected_wide_vart_selected']:blockers.append('ACTUAL_PLATFORM_NOT_ORIGINAL_WIDE')
if not all(compat[k] for k in ('context_boot_matches','context_fdt_matches','context_firmware_matches','direction_boot_matches','human_evidence_boot_matches')):blockers.append('FOLLOW_BINDINGS_NOT_CURRENT_PLATFORM_BOOT')
if not result['manual_binding_matches_current_platform']:blockers.append('MANUAL_BINDING_NOT_CURRENT_PLATFORM_BOOT')
if result['bad_components'] or result['bad_controller_files'] or not result['accepted_parameters_match']:blockers.append('SOURCE_OR_ACCEPTED_PARAMETER_MISMATCH')
if not result['fresh_root_startup_matches'] or not result['selected_binding_matches_root_handoff']:blockers.append('ROOT_HANDOFF_SOURCE_DRIFT')
if not result['current_stop_readback_verified']:blockers.append('NO_CURRENT_READY_STOP_REGISTER_PROOF')
can_participate=not blockers
ready=dict(schema='aura-axis-joint-acceptance-ready-1',observed_host_utc=end,preflight_host_started_utc=started.isoformat(),
    status='READY_WAITING_START_GATE' if can_participate else 'BLOCKED_CURRENT_GUARD_WAITING_ROOT_COORDINATION',
    can_participate=can_participate,start_gate_required=True,start_action_executed=False,
    main_coordinator_thread='01a1994e-f547-74e1-903d-3591021d67c8',identity_handoff_thread='01a19ad7-5865-7c60-82fa-605d17aea70f',
    sole_axis_operator_thread='01a19b64-8194-70e3-806b-03fa9a283918',window='NEW_180_SECOND_JOINT_FUNCTIONAL_ACCEPTANCE',
    prior_90_or_40_second_windows_reused=False,handoff_path=str(H),handoff_sha256=raw['handoff_sha256'],
    boot_id=result['boot_id'],startup_sha256=result['startup_sha256_after'],components_count=result['components_count'],
    bad_components=result['bad_components'],owners=h,actual_platform=result['platform'],pan=result['gui'],
    controller_root=result['controller_root'],controller_manifest_sha256=result['controller_manifest_sha256'],
    controller_file_count=result['controller_file_count'],bad_controller_files=result['bad_controller_files'],
    accepted_parameters_match=result['accepted_parameters_match'],compatibility=result['compatibility'],
    manual_binding_matches_current_platform=result['manual_binding_matches_current_platform'],selected_binding_matches=result['selected_binding_matches_root_handoff'],
    current_stop_readback_verified=result['current_stop_readback_verified'],blockers=blockers,
    this_stage_actions=dict(original_pan_stop_sent=result['original_pan_stop_sent_once'],follow_start=False,
        axis_commands=result['axis_commands_sent'],DFX=False,services_restarted=False,initialization=False,recentering=False,
        source_or_config_or_parameter_change=False),
    end_plan='Only after main START_GATE and fresh READY/source/no-conflict check: original UI follow toggle once; observe agreed180s; original pan_stop at end and confirm followfalse/flags0/lease0. No tuning, calibration, recenter, firmware or service changes in this acceptance grant.',
    recovery_dependency_if_blocked='Root coordinates actual guard/platform recovery separately. No DFX/reset is authorized by this preflight. If original wide loading is required, motor power must be isolated first under the original powered-off restoration procedure; root asks the observer, axis chat does not repeat questions.',
    power_state_from_user_handoff=h['user_physical_confirmation'],face_position_overlay_metadata=result['face_position_overlay_metadata'],
    raw_numeric_evidence=str(p),human_axis_follow_no_stutter_acceptance_remains_pass=True)
p=HERE/'AXIS_ACCEPTANCE_READY.json';assert not p.exists();p.write_text(json.dumps(ready,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(path=str(p),status=ready['status'],can_participate=can_participate,blockers=blockers,
    platform=ready['actual_platform'],pan=ready['pan'],controller_files=ready['controller_file_count'],
    components=ready['components_count'],axis_commands=result['axis_commands_sent'],
    layout=result['face_position_overlay_metadata']),ensure_ascii=False,indent=2))
