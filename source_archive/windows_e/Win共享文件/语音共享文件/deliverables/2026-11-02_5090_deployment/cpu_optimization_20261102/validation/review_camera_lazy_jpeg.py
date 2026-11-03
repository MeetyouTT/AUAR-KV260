"""Reproduce stale-request health races on actual v2; test local guard prototype."""
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import threading
import unittest

HERE=Path(__file__).resolve().parent
CAMERA=HERE.parent/'camera'
source=CAMERA/'candidate_v2/ui_camera_service.py'
raw=source.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='0bf23f511f6f85512603277b1496c704fcd792a4f1a0fc97854ead03441920bf'
spec=importlib.util.spec_from_file_location('independent_camera_candidate_tests',CAMERA/'test_lazy_jpeg.py')
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)

def run_suite():
    output=io.StringIO()
    result=unittest.TextTestRunner(stream=output,verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(helpers.LazyJpegTests))
    return {'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()}

def stale_request_race(old_mode,new_mode):
    state,frame,codec,_=helpers.setup_state(helpers.Codec(old_mode))
    resolve=frame.resolve;ready=threading.Event();release=threading.Event();values=[]
    # This gate models a scheduler pause immediately after resolve releases its
    # encoder lock, before CameraState reacquires its shared state lock.
    def delayed():
        result=resolve();ready.set()
        if not release.wait(2):raise RuntimeError('independent test gate timeout')
        return result
    frame.resolve=delayed
    worker=threading.Thread(target=lambda:values.append(state.preview(state.camera_epoch,1)))
    worker.start();assert ready.wait(1)
    newer=helpers.PreviewJpeg(helpers.image(63),helpers.Codec(new_mode),state._preview_encode_lock)
    state.publish_preview(2,950,newer)
    new_value=state.preview(state.camera_epoch,2)
    after_latest=bool(state.preview_error)
    release.set();worker.join(1);assert not worker.is_alive()
    after_stale=bool(state.preview_error)
    assert list(state.frames)==[1,2]  # The old request is retained, not evicted.
    return {'old_mode':old_mode,'new_mode':new_mode,'new_jpeg_available':new_value is not None,
        'error_after_latest_request':after_latest,'error_after_stale_request':after_stale,
        'stale_request_changed_latest_error':after_latest!=after_stale,
        'old_request_returned_jpeg':values[0] is not None}

before=run_suite();assert before['passed'] and before['tests']==20
races=[stale_request_race('ok','raise'),stale_request_race('raise','ok')]
assert all(row['stale_request_changed_latest_error'] for row in races)
text=raw.decode().replace('\r\n','\n')
old="            if error is not None:self.preview_error = error\n            if jpeg is not None:self.preview_error = ''"
new="            if self.frames and fid == next(reversed(self.frames)):\n                if error is not None:self.preview_error = error\n                if jpeg is not None:self.preview_error = ''"
assert text.count(old)==1
fixed=text.replace(old,new)
klass=next(n for n in ast.parse(fixed).body if isinstance(n,ast.ClassDef) and n.name=='CameraState')
namespace=dict(helpers.space)
exec(compile(ast.Module(body=[klass],type_ignores=[]),'<validation-only-latest-frame-guard>','exec'),namespace)
helpers.CameraState=namespace['CameraState']
after=run_suite();assert after['passed'] and after['tests']==20
fixed_races=[stale_request_race('ok','raise'),stale_request_race('raise','ok')]
assert not any(row['stale_request_changed_latest_error'] for row in fixed_races)
result={'status':'V2_BLOCKER_REPRODUCED_LOCAL_GUARD_PROTOTYPE_PASSES',
    'reviewed_candidate_sha256':hashlib.sha256(raw).hexdigest(),
    'original_suite_v2':before,'v2_race_results':races,
    'local_guard_prototype_existing_suite':after,'local_guard_prototype_races':fixed_races,
    'production_candidate_modified':False,'board_or_external_network_used':False,
    'synthetic_loopback_http_fixture_used':True,
    'raw_media_private_content_used':False,
    'required_fix':'Only the latest retained frame may update the global preview_error; older requests retain their own return and counters.'}
(HERE/'CAMERA_V2_INDEPENDENT_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
