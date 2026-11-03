"""Compose readback from the same metadata probe and the original pure validator."""
import ast,json
from pathlib import Path
L=Path(__file__).parent
load=lambda p:json.loads(Path(p).read_bytes())
a=load(L/'apply.json');before=load(L/'preflight.json')
prefix='G=dict(G,startup_before_sha256='+repr(a['startup_after_sha256'])+')\nC=dict(C,pins=json.loads('+repr(json.dumps(a['component_sha256']))+'))\nPB=json.loads('+repr(json.dumps(before))+')\n'
source=(L/'preflight.py').read_text(encoding='utf-8').rsplit('print(json.dumps(',1)[0]
tail=r'''
TX=Path('/home/root/aura-5090-recovery-20261102-a6d4a069/original-follow-binding-185858-v1')
transaction=load(TX/'transaction.json')
assert transaction['startup_after_sha256']==sha(S) and transaction['component_sha256']==startup['component_sha256']
assert transaction['status']=='ORIGINAL_AXIS_CONFIG_RECONNECTED_GUI_STOPPED' and transaction['original_rated_range_validator_passed']
validator=A/'board/motion/rated_range_release.py';space={'__name__':'original_rated_range_metadata_readback'}
exec(compile(raw(validator),str(validator),'exec'),space)
assert space['rated_range_bounds'](release,manual,release_path.parent)==(500,2500)
assert {k:v for k,v in manual.items() if k not in ['boot_id','fdt_sha256','release_manifest','release_manifest_sha256']}=={k:v for k,v in PB['pan']['manual'].items() if k not in ['boot_id','fdt_sha256','release_manifest','release_manifest_sha256']}
assert manual['boot_id']==G['boot_id'] and manual['fdt_sha256']==C['context']['fdt_sha256']
assert {k:v for k,v in face.items() if k!='arguments'}=={k:v for k,v in PB['pan']['face'].items() if k!='arguments'}
changed_args={'context','human-evidence','zone-settings'}
assert {k:v for k,v in face['arguments'].items() if k not in changed_args}=={k:v for k,v in PB['pan']['face']['arguments'].items() if k not in changed_args}
assert face['arguments']['context']==str(restore/'wide-context.json') and load(face['arguments']['context'])==C['context']
assert face['arguments']['left-target-center-ratio']=='0.40' and face['arguments']['target-center-ratio']=='0.45' and face['arguments']['rearm-stability-ms']=='150'
assert face['arguments']['direction-evidence']==str(A/'config/pan_direction.current.json')
bookkeeping={'board_boot_id','updated_mono_ms','geometry_reused_from','geometry_reused_sha256','reuse_basis'}
assert {k:v for k,v in zone.items() if k not in bookkeeping}=={k:v for k,v in PB['zone'].items() if k not in bookkeeping}
assert zone['board_boot_id']==G['boot_id'] and zone['geometry_reused_sha256']==PB['zone_sha256']
assert direction['boot_id']==G['boot_id'] and direction['axis_camera_mirrored_control_polarity']==1 and direction['current_boot_motion_measured'] is False
predecessor=direction['predecessor_direction'];assert predecessor['sha256']==transaction['original_direction_predecessor_sha256']==sha(predecessor['path'])
assert load(predecessor['path'])==PB['pan']['direction']
auth=load(auth_path);assert auth['motor_power_state']=='OFF' and auth['motor_power_off_is_human_confirmation'] is True
assert auth['current_boot_motion_measured'] is False and auth['physical_calibration_claimed'] is False
assert '动力已接好' not in auth['current_user_mount_and_power_confirmation']
assert auth['predecessor_authorization']==PB['old_authorization_pin']
human=load(face['arguments']['human-evidence']);assert human['boot_id']==G['boot_id'] and human['actual_direction_evidence_sha256']==sha(A/'config/pan_direction.current.json')
old_release=load(PB['pan']['manual']['release_manifest'])
assert old_release['runtime_files']==release['runtime_files'] and old_release['payload_files']==release['payload_files']
assert all(sha(path)==value for path,value in release['runtime_files'].items())
assert all(sha(release_path.parent/name)==value for name,value in release['payload_files'].items())
before_startup=load(TX/'before/3-config.json')
assert {k:v for k,v in startup.items() if k!='component_sha256'}=={k:v for k,v in before_startup.items() if k!='component_sha256'}
changed={k for k,v in startup['component_sha256'].items() if before_startup['component_sha256'][k]!=v}
assert changed=={'config/pan_manual.local.json','config/pan_face.local.json','config/pan_direction.current.json'}
changed_files=[{'path':str(A/k),'before_sha256':before_startup['component_sha256'][k],'after_sha256':sha(A/k)} for k in sorted(changed)]
changed_files.append({'path':str(S),'before_sha256':transaction['startup_before_sha256'],'after_sha256':sha(S)})
print(json.dumps({'status':'ORIGINAL_PAN_METADATA_BINDING_VERIFIED_GUI_STOPPED','boot_id':G['boot_id'],'startup_path':str(S),'startup_sha256':sha(S),'component_sha256':startup['component_sha256'],'component_count':380,'unchanged_component_count':377,'changed_files':changed_files,'controller25_preserved':True,'all_parameters_and_geometry_preserved':True,'four_core_preserved':G['latest_identity_four_core'],'selected_face_binding':G['selected_face_binding'],'selected27_original_verify_passed':True,'camera_owner':G['camera_owner'],'camera_config':G['camera_config'],'GUI':gui,'camera_service':camera,'new_manual_release_path':str(release_path),'new_manual_release_sha256':sha(release_path),'original_rated_range_bounds':[500,2500],'original_rated_range_validator_passed':True,'context_path':str(restore/'wide-context.json'),'context_sha256':sha(restore/'wide-context.json'),'direction_sha256':sha(A/'config/pan_direction.current.json'),'direction_predecessor':predecessor,'direction_polarity':1,'current_boot_motion_measured':False,'physical_reference_measured':False,'reset1500_is_not_physical_center':True,'zone_path':str(zone_path),'zone_sha256':sha(zone_path),'zone_geometry_preserved':True,'motor_power_state':'OFF','MMIO_opened':False,'STOP_sent':False,'BIND_sent':False,'REFERENCE_sent':False,'ARM_sent':False,'COMMIT_sent':False,'services_changed':False,'transaction':str(TX),'transaction_sha256':sha(TX/'transaction.json'),'ready_for_root_first_GUI_start':True,'following_started':False,'observation_monotonic_ms':round(time.monotonic()*1000)}))
'''
code=prefix+source+tail
ast.parse(code)
with (L/'verify.py').open('x',encoding='utf-8',newline='\n') as f:f.write(code)
print(json.dumps({'readback_prepared':True,'no_MMIO_or_service_actions':True}))
