import datetime,hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
result=subprocess.run([sys.executable,'-B',str(HERE/'test_lazy_jpeg_v3.py')],capture_output=True,text=True,encoding='utf-8')
log=result.stdout+result.stderr
with (HERE/'LOCAL_TESTS_V3.log').open('x',encoding='utf-8') as stream:stream.write(log)
assert result.returncode==0,log
assert 'Ran 27 tests' in log and '\nOK\n' in log
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests':27,'failures':0,'errors':0,
    'candidate_sha256':hashlib.sha256((HERE/'candidate_v3/ui_camera_service.py').read_bytes()).hexdigest(),
    'test_source_sha256':hashlib.sha256((HERE/'test_lazy_jpeg_v3.py').read_bytes()).hexdigest(),
    'runtime':sys.executable,'real_cv2_available_in_this_runtime':False,
    'real_cv2_probe_pending_with_root':True,'board_calls_during_tests':False,
    'real_media_or_private_data_used':False}
with (HERE/'LOCAL_TESTS_V3.json').open('x',encoding='utf-8') as stream:json.dump(receipt,stream,indent=2)
print(json.dumps(receipt))
