# USE_SESSION_COMMON
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='VISIBLE_OBSERVED_REPEAT_AWAITING_HUMAN'
sys.path.insert(0,str(RELEASE/'driver'))
from vsrv_driver import VSRVDriver
from vsrv_transport import NativeRegisters
m=document(RELEASE/'candidate-manifest.json')
with NativeRegisters(RELEASE/'driver/libvsrv.so',m['payload_files']['libvsrv.so'],BOOT,m['runtime_files']) as io:
    d=VSRVDriver(io,0x10282601,BOOT);before=d.status();after=d.stop()
assert after['flags']==0 and after['lease_left_ms']==0
h=get_json(8790,'/health')
assert h['pid']==j['restored_camera_pid']
j.update(phase='STOPPED_PHYSICAL_RESPONSE_NOT_CONFIRMED',current_stopped_readback=after,
    human_reply='没有转动，或出现异常',physical_response_confirmed=False,
    automatic_following_enabled=False,direction_qualified=False);save(j)
print(json.dumps(dict(status=j['phase'],before=before,after_stop=after,
    camera_pid=h['pid'],camera_error=bool(h['camera_error']),detector_error=bool(h['detector_error']),
    identity_ready=h['identity']['ready'],identity_error=bool(h['identity']['error']),
    primary_period_overruns=h['dpu_schedule'].get('primary_period_overruns'),
    owner_fenced=h['dpu_schedule'].get('owner_fenced'),automatic_following_enabled=False)))
