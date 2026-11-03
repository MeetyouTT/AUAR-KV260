import datetime,hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
result=subprocess.run([sys.executable,'-B',str(HERE/'test_lazy_jpeg.py')],capture_output=True,text=True,encoding='utf-8')
log=result.stdout+result.stderr
assert result.returncode==0,log
assert 'Ran 20 tests' in log and '\nOK\n' in log
with (HERE/'LOCAL_TESTS.log').open('x',encoding='utf-8') as stream:stream.write(log)
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests':20,'failures':0,'errors':0,
    'candidate_sha256':hashlib.sha256((HERE/'candidate_v2/ui_camera_service.py').read_bytes()).hexdigest(),
    'test_source_sha256':hashlib.sha256((HERE/'test_lazy_jpeg.py').read_bytes()).hexdigest(),
    'runtime':sys.executable,'real_cv2_available_in_this_runtime':False,
    'real_cv2_probe_pending_with_root':True,'board_calls_during_tests':False,
    'real_media_or_private_data_used':False}
with (HERE/'LOCAL_TESTS.json').open('x',encoding='utf-8') as stream:json.dump(receipt,stream,indent=2)
print(json.dumps(receipt))
