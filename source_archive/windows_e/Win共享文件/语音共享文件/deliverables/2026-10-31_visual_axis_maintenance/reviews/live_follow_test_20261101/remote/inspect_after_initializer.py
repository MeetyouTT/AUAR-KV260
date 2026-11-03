# USE_SESSION_COMMON
current_guard();wide_active();verify_wide_files()
j=state();assert j['phase']=='INITIALIZATION_FAILED_NO_RETRY'
sys.path.insert(0,str(RELEASE/'driver'))
from vsrv_driver import VSRVDriver
from vsrv_transport import NativeRegisters
manifest=document(RELEASE/'candidate-manifest.json')
with NativeRegisters(RELEASE/'driver/libvsrv.so',manifest['payload_files']['libvsrv.so'],BOOT,manifest['runtime_files']) as io:
    device=VSRVDriver(io,0x10282601,BOOT)
    before=device.status();after=device.stop()
assert after['flags']==0 and after['lease_left_ms']==0
atomic(ROOT/'after-initializer-failed-stop.json',dict(before=before,after_stop=after,boot=BOOT))
j.update(current_stopped_readback=after,failed_initializer_stop_confirmed=True);save(j)
print(json.dumps(dict(status='INITIALIZER_FAILURE_STOP_CONFIRMED',before=before,after_stop=after,
    physical_observation_pending=True,automatic_following=False)))
