# USE_SESSION_COMMON
"""Validate this boot's ID/STOP and short camera liveness; never ARM or COMMIT."""
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='CAMERA_RESTORED_ON_WIDE'
assert int(systemd()['MainPID'])==j['restored_camera_pid']
context=dict(boot_id=BOOT,fdt_sha256=digest('/sys/firmware/fdt'),firmware_name=firmware())
atomic(ROOT/'wide-context.json',context)
assert digest(RELEASE/'bench_identity_stop.py')=='c9e91f74336c1e73d7c60408739abc8537b80066eb666a1a79e32b81d7d267aa'
output=ROOT/'id-stop.json';assert not output.exists()
args=['/usr/bin/python3','-B',str(RELEASE/'bench_identity_stop.py'),'--execute','--confirmation','ID_STOP_ONLY',
    '--manifest',str(RELEASE/'candidate-manifest.json'),'--manifest-sha256',MANIFEST_SHA,
    '--context',str(ROOT/'wide-context.json'),'--output',str(output)]
p=subprocess.run(args,capture_output=True,text=True,timeout=10)
assert p.returncode==0
receipt=document(output)
assert receipt['identity_stop_passed'] is True
assert receipt['ARM_sent'] is False and receipt['COMMIT_sent'] is False
first=get_json(8790,'/health');time.sleep(2);last=get_json(8790,'/health')
assert first['pid']==last['pid']==j['restored_camera_pid']
assert last['camera_error']==last['detector_error']==last['identity']['error']==''
assert last['identity']['ready'] is True
assert last['capture_frames']>first['capture_frames'] and last['detected_frames']>first['detected_frames']
schedule=last['dpu_schedule'];status=schedule.get('native',schedule)
j.update(phase='WIDE_ID_STOP_CAMERA_PROGRESS_VERIFIED',id_stop_sha256=digest(output),
    context_sha256=digest(ROOT/'wide-context.json'));save(j)
print(json.dumps(dict(status=j['phase'],before=receipt.get('before'),after_stop=receipt.get('after_stop'),
    stop_api_wall_ms=receipt.get('stop_api_wall_ms'),id_stop_sha256=j['id_stop_sha256'],
    camera_pid=last['pid'],capture_delta=last['capture_frames']-first['capture_frames'],
    detection_delta=last['detected_frames']-first['detected_frames'],
    face_detector_delta=last['identity']['face_targets']['processed']-first['identity']['face_targets']['processed'],
    identity_processed_delta=last['identity']['processed']-first['identity']['processed'],
    camera_error=False,detector_error=False,identity_ready=True,identity_error=False,
    schedule_top_keys=sorted(schedule),schedule_native_keys=sorted(status),
    ARM_sent=False,COMMIT_sent=False,physical_position_verified=False)))
