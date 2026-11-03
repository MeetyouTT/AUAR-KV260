"""Read only the already-recorded finite command evidence after output is off."""
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='PHYSICAL_ANOMALY_ABORTED_OUTPUT_CLOSED'
report=document(ROOT/'initialization.json');events=report.get('events',[])
elapsed=[row['elapsed_ms'] for row in events if type(row.get('elapsed_ms')) in (int,float)]
width=[row['width_us'] for row in events if type(row.get('width_us')) is int]
targets=[row['target_us'] for row in events if type(row.get('target_us')) is int]
gaps=[b-a for a,b in zip(elapsed,elapsed[1:])]
h=get_json(8790,'/health')
assert h['pid']==j['restored_camera_pid'] and h['camera_error']==h['detector_error']==h['identity']['error']==''
print(json.dumps(dict(status='READ_ONLY_INITIALIZATION_COMMAND_DIAGNOSTIC',report_status=report.get('status'),
 events=len(events),commanded_pulse_values_us=sorted(set(targets)),observed_register_width_range_us=[min(width),max(width)] if width else None,
 first_event_elapsed_ms=elapsed[0] if elapsed else None,last_event_elapsed_ms=elapsed[-1] if elapsed else None,
 event_gap_range_ms=[min(gaps),max(gaps)] if gaps else None,
 first_output_was_new_1500us_reference_from_unknown_actual_position=True,
 physical_angle_or_mechanical_zero_calibrated=False,external_pwm_waveform_measured=False,
 servo_supply_voltage_or_current_measured=False,hardware_or_mechanical_root_cause_established=False,
 camera_owner=dict(pid=h['pid'],birth=j['restored_camera_birth']),camera_errors_clear=True,
 capture_frames=h.get('capture_frames'),detected_frames=h.get('detected_frames'),owner_fenced=h['dpu_schedule']['owner_fenced'],
 further_motion_performed=False,current_stopped_readback=j['current_stopped_readback'],mic_saved_enabled=False)))
