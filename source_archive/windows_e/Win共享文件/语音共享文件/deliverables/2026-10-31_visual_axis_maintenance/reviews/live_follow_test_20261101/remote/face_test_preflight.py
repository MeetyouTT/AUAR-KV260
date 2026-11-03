# USE_SESSION_COMMON
"""Bind the observed positive-pulse direction and inspect fresh anonymous face metadata."""
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='VISIBLE_POWERED_REPEAT_AWAITING_HUMAN'
assert int(systemd()['MainPID'])==j['restored_camera_pid']
human=dict(boot_id=BOOT,status='HUMAN_DIRECTION_CONFIRMED',
    source='direct user feedback in 01a195e4-58a7-72d3-b141-d5d373579f7f',
    user_quote='现在超我的左边，现在是中点、位置么',
    perspective='user facing the camera',positive_pulse_direction='towards the users left',
    pulse_sequence_us=[1505,1585,1505],trial_sha256=j['powered_repeat_receipt_sha256'],
    camera_moves_with_axis=True,axis_camera_mirrored_control_polarity=-1,
    physical_angle_measured=False,mechanical_zero_calibrated=False,
    physical_return_stop_observed=None,command_return_stop_verified=True)
atomic(ROOT/'current-direction-human.json',human)
h=get_json(8790,'/health');assert h['pid']==j['restored_camera_pid']
assert h['mirror_horizontal'] is True and h['camera_error']==h['detector_error']==''
samples=[]
for index in range(3):
    p=get_json(8790,'/v1/motion/face/observation')
    target=p.get('target') or {};box=target.get('box');width=p.get('frame_width')
    center=(box[0]+box[2]/2)/width if box and width else None
    samples.append(dict(state=p.get('state'),frame_width=p.get('frame_width'),frame_height=p.get('frame_height'),
        source_frame_id=p.get('source_frame_id'),source_age_ms=round(time.monotonic()*1000)-p['source_mono_ms'] if type(p.get('source_mono_ms')) is int else None,
        source_keys=sorted(p),target_present=bool(target),face_center_ratio=center,
        face_tracking=p.get('face_tracking')))
    time.sleep(.2)
j.update(direction_qualified=True,control_polarity=-1,direction_evidence_sha256=digest(ROOT/'current-direction-human.json'),
    physical_response_confirmed=True,phase='DIRECTION_BOUND_FACE_PREFLIGHT');save(j)
print(json.dumps(dict(status=j['phase'],mirror_horizontal=h['mirror_horizontal'],control_polarity=-1,
    direction_human_sha256=j['direction_evidence_sha256'],samples=samples,mechanical_zero_calibrated=False,
    identity_ready=h['identity']['ready'],owner_fenced=h['dpu_schedule'].get('owner_fenced'))))
