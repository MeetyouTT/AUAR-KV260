# USE_SESSION_COMMON
"""Stop through the existing GUI owner; never open a second motor register owner."""
j=state();STARTUP_SHA=j['original_committed_startup_sha256'];current_guard();wide_active()
before=get_json(8783,'/api/state')
conn=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
try:
    conn.request('POST','/api/command',body=json.dumps({'type':'pan_stop'}),
        headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
    response=conn.getresponse();raw=response.read(100000)
    assert response.status==200
finally:conn.close()
end=time.monotonic()+10
while time.monotonic()<end:
    after=get_json(8783,'/api/state');pan=after.get('manual_pan',{});r=pan.get('readback') or {}
    if pan.get('automatic_following') is False and pan.get('state')=='READY' and r.get('flags')==0 and r.get('lease_left_ms')==0:break
    time.sleep(.2)
else:raise RuntimeError('Original owner STOP not yet confirmed; no configuration change')
manual=document(BUSINESS/'runtime/aura/config/pan_manual.local.json')
face=document(Path(manual['face_follow_config']))
direction=document(Path(face['arguments']['direction-evidence']))
j.update(phase='ORIGINAL_STOPPED_DIRECTION_CORRECTION_REQUESTED',current_stopped_readback=r,
    user_direction_correction='转轴转动方向反了');save(j)
print(json.dumps(dict(status=j['phase'],before_automatic_following=before.get('manual_pan',{}).get('automatic_following'),
    before_follow_report=before.get('manual_pan',{}).get('face_follow',{}).get('report'),
    manual_pan={k:pan.get(k) for k in ('state','pulse_us','target_us','automatic_following','left_sign','readback')},
    direction_polarity=direction['axis_camera_mirrored_control_polarity'],
    original_controller_root=face['release_root'],page=after.get('ui_page'),
    runtime_fault_count=after.get('runtime_faults',{}).get('count'))))
