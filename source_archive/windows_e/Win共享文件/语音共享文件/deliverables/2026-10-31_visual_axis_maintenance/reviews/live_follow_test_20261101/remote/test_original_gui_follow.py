# USE_SESSION_COMMON
"""Exercise the existing GUI follow button and STOP, using only its unchanged original controller."""
import signal
j=state();STARTUP_SHA=j['original_committed_startup_sha256'];current_guard();wide_active();verify_wide_files()
assert j['phase']=='ORIGINAL_ENTRY_READY'
assert digest(BUSINESS/'runtime/aura/tools/face_pan_controls.py')=='3ebb1b32368c8f12864e0f13da68853e4d9653e4279eada124eb337c5ca9d7ee'
manual=document(BUSINESS/'runtime/aura/config/pan_manual.local.json')
face=document(manual['face_follow_config']);controller=Path(face['release_root'])
assert controller==Path('/home/root/aura-pan-wide-20261028/control-10282601')
assert digest(controller/'deployment-manifest.json')==face['manifest_sha256']=='5c8206ee626c91c9f311ee870245813e169ac14e554e2579554c74489066f562'
manifest=document(controller/'deployment-manifest.json')
assert len(manifest['files'])==25 and all(digest(r['destination'])==r['sha256'] for r in manifest['files'])
direction=Path(face['arguments']['direction-evidence']);assert document(direction)['axis_camera_mirrored_control_polarity']==1

def command(kind,**fields):
    conn=http.client.HTTPConnection('127.0.0.1',8783,timeout=5)
    try:
        conn.request('POST','/api/command',body=json.dumps(dict(type=kind,**fields)),
            headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
        response=conn.getresponse();raw=response.read(100000)
        assert response.status==200
        return json.loads(raw)
    finally:conn.close()

first=get_json(8783,'/api/state');health_before=get_json(8790,'/health')
assert health_before['pid']==j['restored_camera_pid'] and health_before['identity']['ready'] is True
command('ui_page',page='vision')
time.sleep(5)
live=get_json(8783,'/api/state');already=live['manual_pan'].get('automatic_following') is True
if not already:command('pan_face_follow')
samples=[];stop_error=None;report_path=None
try:
    until=time.monotonic()+15
    while time.monotonic()<until:
        v=get_json(8783,'/api/state');pan=v['manual_pan'];follow=pan.get('face_follow',{})
        report_path=follow.get('report') or report_path
        samples.append(dict(mono_ms=round(time.monotonic()*1000),state=pan.get('state'),
            automatic_following=pan.get('automatic_following'),pulse_us=pan.get('pulse_us'),
            commands_accepted=follow.get('commands_accepted'),phase=follow.get('phase'),reason=follow.get('reason')))
        h=v['handsfree_dialogue'];assert h['state']=='PAUSED' and h['enabled'] is False and h['microphone_open'] is False
        time.sleep(.5)
finally:
    try:command('pan_stop')
    except Exception as exc:
        stop_error=type(exc).__name__
        # Send TERM only to this exact original runner/report pair. Never
        # replace an uncertain owner or create a competing register client.
        if report_path:
            for path in Path('/proc').iterdir():
                if not path.name.isdigit():continue
                try:
                    argv=(path/'cmdline').read_bytes().decode().split('\0')
                    if argv[:3]==['/usr/bin/python3','-B',str(controller/'run_face_motion.py')] and report_path in argv:
                        os.kill(int(path.name),signal.SIGTERM)
                except (OSError,UnicodeError):pass
end=time.monotonic()+10
while time.monotonic()<end:
    last=get_json(8783,'/api/state');pan=last['manual_pan'];rb=pan.get('readback') or {}
    if pan.get('automatic_following') is False and pan.get('state')=='READY' and rb.get('flags')==0 and rb.get('lease_left_ms')==0:break
    time.sleep(.2)
else:raise RuntimeError('Original GUI STOP/readback not confirmed')
report_path=pan.get('face_follow',{}).get('report') or report_path
path=Path(report_path);assert controller/'runs' in path.parents and not path.is_symlink()
report=document(path)
assert report['consumer_manifest_sha256']==face['manifest_sha256']
assert report['control_polarity']==1 and report['direction_evidence_sha256']==digest(direction)
result=report.get('result',{});stopped=result.get('stopped',{})
assert stopped.get('flags')==0 and stopped.get('lease_left_ms')==0
health_after=get_json(8790,'/health');assert health_after['pid']==health_before['pid']
assert health_after['camera_error']==health_after['detector_error']==health_after['identity']['error']==''
identity=get_json(8790,'/v1/ui/status').get('modules',{}).get('identity',{}).get('state')
numeric={k:value for k,value in result.items() if type(value) in (bool,int,float)}
j.update(phase='ORIGINAL_GUI_DIRECTION_TEST_STOPPED',current_stopped_readback=rb,
    active_follow_control_polarity=1,original_gui_test_report=str(path),original_gui_test_report_sha256=digest(path),
    original_gui_test_controller_manifest_sha256=face['manifest_sha256']);save(j)
print(json.dumps(dict(status=j['phase'],controller='ORIGINAL_UNCHANGED_25_FILES',control_polarity=1,
    controller_status=report.get('status'),error_present=bool(report.get('error')),
    result_state=result.get('state'),result_reason=result.get('reason'),metrics=numeric,
    stopped=stopped,gui_final_readback=rb,gui_manual_state=pan['state'],gui_following=pan['automatic_following'],
    runtime_fault_count=last.get('runtime_faults',{}).get('count'),identity_state=identity,
    microphone_open=last['handsfree_dialogue']['microphone_open'],listening_state=last['handsfree_dialogue']['state'],
    native_period_overruns_before=health_before['dpu_schedule']['primary_period_overruns'],
    native_period_overruns_after=health_after['dpu_schedule']['primary_period_overruns'],
    owner_fenced=health_after['dpu_schedule']['owner_fenced'],input_summary=report.get('input_summary'),
    report_path=str(path),report_sha256=digest(path),samples=samples,stop_api_error=stop_error)))
