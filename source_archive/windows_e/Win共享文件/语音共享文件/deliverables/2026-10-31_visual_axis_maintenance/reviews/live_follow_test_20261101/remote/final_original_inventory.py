# USE_SESSION_COMMON
"""Final read-only source/owner/state receipt after the user accepted the corrected original following."""
j=state();STARTUP_SHA=j['original_committed_startup_sha256'];current_guard();wide_active();verify_wide_files()
assert STARTUP_SHA=='226b5a20f0089f5c534b1d540dd3605d805c17f7f1bd371a6ab5b3a4b287ad15'
assert digest(BUSINESS/'production_source_manifest.json')==j['original_committed_manifest_sha256']=='8ff79452570385921e06c098b5d42c2ea1ef5dfb84d81dfa7f53a9295373d0e8'
startup=document(BUSINESS/'startup/config.json');pins=startup['component_sha256']
assert len(pins)==380 and all(digest(BUSINESS/'runtime/aura'/p)==h for p,h in pins.items())
manual=document(BUSINESS/'runtime/aura/config/pan_manual.local.json')
face=document(manual['face_follow_config']);root=Path(face['release_root'])
assert root==Path('/home/root/aura-pan-wide-20261028/control-10282601')
assert digest(root/'deployment-manifest.json')==face['manifest_sha256']=='5c8206ee626c91c9f311ee870245813e169ac14e554e2579554c74489066f562'
m=document(root/'deployment-manifest.json');assert len(m['files'])==25
assert all(digest(r['destination'])==r['sha256'] for r in m['files'])
direction=document(face['arguments']['direction-evidence']);assert direction['axis_camera_mirrored_control_polarity']==1
v=get_json(8783,'/api/state');h=get_json(8790,'/health');pan=v['manual_pan'];rb=pan.get('readback') or {}
assert h['pid']==j['restored_camera_pid'] and h['identity']['ready'] is True
assert h['camera_error']==h['detector_error']==h['identity']['error']==''
assert h['dpu_schedule']['owner_fenced'] is False
owners={}
unit=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=MainPID','--value'],capture_output=True,text=True,timeout=5)
supervisor=int(unit.stdout.strip());gtk=document(BUSINESS/'runtime/launch.json')['pid']
for role,pid in (('camera',h['pid']),('supervisor',supervisor),('gtk',gtk)):
    proc=Path('/proc')/str(pid)
    owners[role]=dict(pid=pid,birth_ticks=int((proc/'stat').read_text().rsplit(')',1)[1].split()[19]),command_sha256=digest(proc/'cmdline'))
assert digest(BUSINESS/'runtime/aura/tools/face_pan_controls.py')=='3ebb1b32368c8f12864e0f13da68853e4d9653e4279eada124eb337c5ca9d7ee'
pub=document('/home/root/aura-board-business-20261030/control-production-v1/state.json')
assert pub['phase']=='COMMITTED' and pub['guard_removed'] is True
assert pub['axis_original_rebind']['state']==pub['axis_direction_rebind']['state']=='APPLIED'
closed=pan.get('automatic_following') is False and rb.get('flags')==0 and rb.get('lease_left_ms')==0
result=dict(schema='aura-original-follow-final-1',boot=BOOT,startup_sha256=STARTUP_SHA,
    manifest_sha256=j['original_committed_manifest_sha256'],configuration_sha256=digest(BUSINESS/'runtime/aura/config/board_avatar_gtk.json'),
    component_pins=380,all_component_bytes_match=True,original_controller_files=25,original_controller_unchanged=True,
    original_controller_manifest_sha256=face['manifest_sha256'],gui_follow_source_unchanged=True,
    control_polarity=1,manual_bounds_us=[manual['manual_minimum_us'],manual['manual_maximum_us']],
    manual_state=pan.get('state'),automatic_following=pan.get('automatic_following'),pulse_us=pan.get('pulse_us'),
    readback=rb,output_closed=closed,owners=owners,page=v.get('ui_page'),
    listening_state=v['handsfree_dialogue']['state'],listening_enabled=v['handsfree_dialogue']['enabled'],
    microphone_open=v['handsfree_dialogue']['microphone_open'],playing=v.get('playing'),
    runtime_fault_count=v.get('runtime_faults',{}).get('count'),identity_backend=h['identity']['backend'],
    identity_ready=h['identity']['ready'],identity_error=False,primary_period_overruns=h['dpu_schedule']['primary_period_overruns'],
    owner_fenced=False,firmware=firmware(),vart_exact_wide=True,fdt_sha256=digest('/sys/firmware/fdt'),
    face_readback=document(BUSINESS/'runtime/aura/config/board_avatar_gtk.json')['board_business']['face_readback'],
    publication_guard_removed=True,previous_transaction_histories_preserved=True,
    latest_actual_follow_report=j['original_gui_test_report'],latest_actual_follow_report_sha256=j['original_gui_test_report_sha256'],
    user_feedback='差不多额',physical_acceptance='USER_APPROXIMATE_ACCEPTANCE',mechanical_zero_calibrated=False,
    measured_shaft_angle=False,long_stability_verified=False)
atomic(ROOT/'final-original-inventory.json',result)
j.update(phase='ORIGINAL_FOLLOW_TEST_COMPLETE_USER_APPROXIMATE_ACCEPTANCE',final_inventory_sha256=digest(ROOT/'final-original-inventory.json'),
    active_follow_control_polarity=1,user_final_feedback='差不多额');save(j)
print(json.dumps(result))
