"""Summarize the installed original implementation; no replacement controller is produced."""
import ast
import copy
import datetime
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
inventory=json.loads((HERE/'original_axis_inventory_01.json').read_text(encoding='utf-8'))['board_result']
index=json.loads((HERE/'source_index.json').read_text(encoding='utf-8'))
oscap=json.loads((HERE/'os_supervision_capabilities_01.json').read_text(encoding='utf-8'))['board_result']
stop=json.loads((HERE/'original_stop_api_source_01.json').read_text(encoding='utf-8'))['board_result']
diagnostic=json.loads((HERE/'input_diagnostics_original_source.json').read_text(encoding='utf-8'))['board_result']
control='/home/root/aura-pan-wide-20261028/control-10282601'
release='/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c'
zone_source=Path(index[control+'/face_zone.py']['local_path']).read_text(encoding='utf-8')
tree=ast.parse(zone_source)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='camera_zone')
space={'math':math}
exec(compile(ast.Module(body=[copy.deepcopy(node)],type_ignores=[]),'<original-pure-camera-zone>','exec'),space)
old_zone=inventory['argument_documents']['zone-settings']
geometry=space['camera_zone'](old_zone,old_zone['board_boot_id'])
old_boot_rejected=False
try:space['camera_zone'](old_zone,inventory['boot_id'])
except ValueError:old_boot_rejected=True
assert old_boot_rejected

def source(path):
    item=index[path]
    return {'path':path,'sha256':item['sha256'],'local_snapshot':item['local_path']}

entries={
 'continuous_follow':dict(source(control+'/run_face_motion.py'),
    cli=['--manifest','--manifest-sha256','--context','--app-root','--output','--direction-evidence','--human-evidence','--zone-settings','--confirmation FACE_ZONE_CONTINUOUS','--duration 0..300'],
    reusable_original_code=True,current_input_documents_usable=False,
    reason='Original code accepts a fresh context, but selected platform/direction/zone evidence is from bebd3e7d and current platform is benchmark.'),
 'input_diagnostics':{'path':diagnostic['path'],'sha256':diagnostic['sha256'],
    'cli':['--settings <current-boot settings>','--output <exclusive new result>','--duration 1..30'],
    'actuator_imports':False,'usable_before_wide':True,
    'environment':'PYTHONPATH=<actual GUI aura root> for the original common.motion_observation import',
    'scope':'source packets and software perception only; internal1450 is a synthetic calculation reference, not shaft position'},
 'identity_stop':dict(source(release+'/bench_identity_stop.py'),
    cli=['--execute','--confirmation ID_STOP_ONLY','--manifest','--manifest-sha256','--context','--output'],
    reusable_original_code=True,currently_usable=False,
    prerequisites=['actual wide/operating/exact VART','fresh boot/FDT context','pinned four runtime/three driver files','no conflicting owner']),
 'finite_initialization':dict(source('/home/root/aura-axis-priority-20261101-3c94e7a0/bench_finite_step_deadline_fix.py'),
    cli=['--execute','--confirmation OBSERVED_FINITE_2S','--initial-us','--target-us','--manifest','--manifest-sha256','--context','--output'],
    reusable_original_code_with_fresh_inputs=True,duration_s=2,maximum_delta_us=5,range_us=[1400,1600],
    environment='PYTHONPATH='+release+' so its top-level original bench_identity_stop import resolves exactly',
    physical_observation_required=True,old_output_or_reference_reusable=False),
 'direction_roundtrip':dict(source('/home/root/aura-axis-priority-20261101-3c94e7a0/bench_observed_80us_6s.py'),
    cli=['--execute','--confirmation OBSERVED_80US_RETURN_6S','--expected-state','--manifest','--manifest-sha256','--context','--output'],
    reusable_original_code_with_fresh_inputs=True,duration_s=6,excursion_us=80,
    prerequisites=['fresh stopped-register expected-state','explicit current observation','origin and origin+80 inside1400..1600'],
    old_output_or_reference_reusable=False),
 'gui_follow_toggle':{'path':inventory['runtime_root']+'/tools/face_pan_controls.py',
    'sha256':index[inventory['runtime_root']+'/tools/face_pan_controls.py']['sha256'],
    'api':{'path':'http://127.0.0.1:8783/api/command','payload':{'type':'pan_face_follow'}},
    'semantics':'toggle: running=>stop, otherwise=>start; enabled parameter is not consulted',
    'requires':'READY manual backend and disabled output before a start; preserve existing exclusive ownership transition'},
 'gui_explicit_stop':{'path':stop['path'],'sha256':stop['sha256'],
    'api':{'path':'http://127.0.0.1:8783/api/command','payload':{'type':'pan_stop'}},
    'semantics':'direct self.pan.stop(), preferred explicit GUI stop; original origin/host and state checks remain'},
 'camera_normal_lifecycle':{'unit':'aura-camera-ui.service',
    'commands':[['systemctl','stop','--no-block','aura-camera-ui.service'],['systemctl','start','--no-block','aura-camera-ui.service']],
    'exec_start':'/usr/bin/python3 -B /home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/face-source-v17/entry.py',
    'protections':{'Restart':'no','KillMode':'process','SendSIGKILL':'no','TimeoutStopUSec':'infinity'},
    'restore_requires':'new real original final checkpoint, full original validation/archive/counters, one-time original restore and exact_seed audit'},
 'old_native_maintenance_ops':dict(source('/home/root/aura-native-live-20261024/ops/be72669aa53de735/boot_ops.py'),
    use='keep the existing service ExecCondition; do not call arm/reboot/benchmark/activate/rollback as wide recovery',
    reason='This is the original native-domain maintenance controller, not a generic parameterized wide platform switch.'),
 'original_dfx_client':{'path':'/usr/bin/dfx-mgr-client','sha256':oscap['client_sha256'],
    'unload_argv':['/usr/bin/dfx-mgr-client','-remove','0'],
    'load_argv':['/usr/bin/dfx-mgr-client','-load','aura-visual-servo-b4096-wide-v1'],
    'success_stdout':{'unload':'remove from slot 0 returns: 0 (Ok)\n','load':'aura-visual-servo-b4096-wide-v1: loaded to slot 0\n'},
    'success_requires':'confirmed unit/client exit plus complete semantic stdout AND actual overlay/ZOCL/firmware/VART/FDT readback; RC0 alone is insufficient'}
}
parameters={
 'mode':'latched_visual_center_hardware_slew','effective_left_camera_ratio':geometry['left_ratio'],
 'effective_right_camera_ratio':geometry['right_ratio'],'content_rect':geometry['content_rect'],
 'screen_left_line_x':geometry['screen_left_line_x'],'screen_right_line_x':geometry['screen_line_x'],
 'target_center_ratio':0.5,'center_tolerance_ratio':0.03,'prearm_trigger_margin_ratio':0.05,
 'confirmed_actual_frames_before_arm':2,'control_tick_ms':20,'maximum_image_age_ms':250,
 'maximum_detection_anchor_age_ms':500,'hardware_pulse_step_us':4,'hardware_frame_ms':20,
 'nominal_hardware_slew_us_s':200,'range_us':[500,2500],'duration_s':inventory['face_config']['duration_s'],
 'one_euro':{'min_cutoff_hz':1.0,'beta':6.0,'derivative_cutoff_hz':1.0,'width_beta':2.0},
 'jump_admission':{'absolute_center_ratio_delta':0.08,'velocity_threshold_ratio_s':1.5,'requires_next_actual_confirmation':True},
 'legacy_config_fields_not_hardware_slew_speed':['maximum_speed_us_s=40','maximum_acceleration_us_s2=120','filter_tau_ms','median_window'],
 'json_center_fields_not_consumed_by_entry':['target_center_ratio','center_tolerance_ratio'],
 'identity_required_for_follow':False,'old_manual_button_sign':-1,'old_follow_polarity':1,
 'old_direction_accepted_for_current_boot':False}

result={'schema':'aura-original-axis-reuse-review-1','updated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'ORIGINAL_CONTROLLER_INTACT_CURRENT_PLATFORM_AND_INPUT_BINDING_RESTORE_PENDING',
 'scope':'Original board implementation only; no new controller or recovery framework',
 'source_observation_startup_sha256':inventory['startup_sha256'],
 'root_reported_identity_only_updated_startup_sha256':'0f2a319abb15d26956857c945c247f6b5fac6421b42692fd173a48104f2e3c4f',
 'original_controller_root':control,'original_controller_manifest_sha256':'5c8206ee626c91c9f311ee870245813e169ac14e554e2579554c74489066f562',
 'original_25_files_verified':inventory['controllers'][control]['all_match'],
 'entrypoints':entries,'effective_parameters':parameters,
 'old_zone_rejected_by_original_current_boot_guard':old_boot_rejected,
 'old_geometry_conversion_executed_without_project_import':True,
 'geometry_calculation_is_current_display_or_motion_evidence':False,
 'optimization_order':['restore existing wide platform and fresh original context/binding while motor power is off',
   'run original input diagnostics and inspect source age/anchor/queue/disconnect reasons',
   'establish this boot reference/direction and a bounded original follow observation',
   'if necessary, adjust existing visual boundary through existing GUI after confirmed stop, one variable at a time',
   'keep original source deadlines, lease, lock, range, hardware slew and target-change STOP'],
 'board_configuration_changed':False,'transient_unit_created':False,'loader_or_motion_executed':False,
 'hardware_follow_accepted':False,'physical_reference_or_direction_claimed':False}
(HERE/'ORIGINAL_AXIS_REUSE.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'output':str(HERE/'ORIGINAL_AXIS_REUSE.json'),'original25_match':result['original_25_files_verified'],
 'effective_zone':[geometry['left_ratio'],geometry['right_ratio']], 'original_follow_sha256':entries['continuous_follow']['sha256']}))
