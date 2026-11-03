"""Bind this boot's directly observed reference and direction, without motion."""
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='DIRECTION_ROUNDTRIP_AWAITING_HUMAN'
control=Path(j['bounded_control']);assert digest(control/'deployment-manifest.json')==j['bounded_control_manifest_sha256']
assert all(digest(row['destination'])==row['sha256'] for row in document(control/'deployment-manifest.json')['files'])
direction=dict(boot_id=BOOT,status='HUMAN_DIRECTION_CONFIRMED',axis_camera_mirrored_control_polarity=1,
 positive_pulse_direction='towards the user left when facing camera',source='current user observation relayed by primary chat',
 observed_roundtrip_sha256=j['direction_roundtrip_sha256'],physical_angle_measured=False,mechanical_zero_calibrated=False)
atomic(ROOT/'direction.json',direction)
zone=dict(schema='aura-face-zone-settings-1',board_boot_id=BOOT,target_kind='face',reference='face_center',
 mirror_horizontal=True,frame_width=640,frame_height=480,left_ratio=0.,viewport=[8,112,568,300],
 left_camera_ratio=.25,right_ratio=(84.+400.*.75)/568.)
atomic(ROOT/'zone.json',zone)
atomic(ROOT/'human.json',dict(boot_id=BOOT,mount_power_and_clearance_user_confirmed=True,initializer_physically_settled=True,
 current_direction_observed=True,physical_zero_calibrated=False,range_us=[1400,1600],test_duration_s=25))
h=get_json(8790,'/health');assert h['pid']==j['restored_camera_pid'] and h['identity']['ready'] is True
assert h['camera_error']==h['detector_error']==h['identity']['error']=='' and h['dpu_schedule']['owner_fenced'] is False
j.update(phase='READY_FOR_25_SECOND_ORIGINAL_BOUNDED_FOLLOW',active_test_control_polarity=1);save(j)
print(json.dumps(dict(status=j['phase'],duration_s=25,range_us=[1400,1600],polarity=1,camera_pid=h['pid'],
 stop_semantics='original full-pulse QUIESCE and final STOP; original image/anchor lease',motion_started=False)))
