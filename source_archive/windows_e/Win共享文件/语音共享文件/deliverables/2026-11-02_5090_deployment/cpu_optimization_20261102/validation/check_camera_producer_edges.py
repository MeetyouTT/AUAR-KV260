"""Local producer-error and repeated-frame ownership boundary reproductions."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import threading

HERE=Path(__file__).resolve().parent
CAMERA=HERE.parent/'camera'
raw=(CAMERA/'candidate_v2/ui_camera_service.py').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='0bf23f511f6f85512603277b1496c704fcd792a4f1a0fc97854ead03441920bf'
text=raw.decode().replace('\r\n','\n')
spec=importlib.util.spec_from_file_location('camera_edges_test_helpers',CAMERA/'test_lazy_jpeg.py')
helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)

def install(code):
    klass=next(n for n in ast.parse(code).body if isinstance(n,ast.ClassDef) and n.name=='CameraState')
    namespace=dict(helpers.space)
    exec(compile(ast.Module(body=[klass],type_ignores=[]),'<validation-only-camera-state>','exec'),namespace)
    helpers.CameraState=namespace['CameraState']

def producer_failed(state):
    if hasattr(state,'preview_failed'):state.preview_failed('synthetic newer raw publication failed')
    else:
        with state.lock:state.preview_error='synthetic newer raw publication failed'

def error_after_request_started():
    state,frame,_,_=helpers.setup_state()
    resolve=frame.resolve;ready=threading.Event();release=threading.Event();values=[]
    def delayed():
        value=resolve();ready.set()
        if not release.wait(2):raise RuntimeError('local gate timeout')
        return value
    frame.resolve=delayed
    worker=threading.Thread(target=lambda:values.append(state.preview(state.camera_epoch,1)))
    worker.start();assert ready.wait(1)
    producer_failed(state);release.set();worker.join(1);assert not worker.is_alive()
    return {'request_returned_old_valid_jpeg':values[0] is not None,
            'newer_producer_error_preserved':bool(state.preview_error)}

def error_before_cached_request():
    state,_,_,_=helpers.setup_state()
    assert state.preview(state.camera_epoch,1) is not None
    producer_failed(state)
    value=state.preview(state.camera_epoch,1)
    return {'request_returned_old_valid_jpeg':value is not None,
            'newer_producer_error_preserved':bool(state.preview_error)}

def duplicate_frame_waiters():
    state,_,codec,_=helpers.setup_state();retained=[];threads=[]
    state._preview_encode_lock.acquire()
    try:
        for index in range(12):
            frame=state.frames[1][1];retained.append(frame)
            resolve=frame.resolve;entered=threading.Event()
            def waiting(resolve=resolve,entered=entered):
                entered.set();return resolve()
            frame.resolve=waiting
            worker=threading.Thread(target=lambda:state.preview(state.camera_epoch,1));threads.append(worker);worker.start()
            assert entered.wait(1)
            state.publish_preview(1,950,helpers.PreviewJpeg(helpers.image(index),codec,state._preview_encode_lock))
        retained_images=sum(frame._image is not None for frame in retained)
        result={'cached_frames':len(state.frames),'retired_waiter_owned_images':retained_images,
            'total_owned_images_while_no_encoder_active':retained_images+sum(frame._image is not None for _,frame in state.frames.values())}
    finally:
        state._preview_encode_lock.release()
        for worker in threads:worker.join(2);assert not worker.is_alive()
    result['unneeded_old_encodes']=codec.calls
    return result

def run():return {'producer_error_after_start':error_after_request_started(),
    'producer_error_before_cached_request':error_before_cached_request(),'same_fid_waiters':duplicate_frame_waiters()}

baseline=run()
old="            if error is not None:self.preview_error = error\n            if jpeg is not None:self.preview_error = ''"
latest="            if self.frames and fid == next(reversed(self.frames)):\n                if error is not None:self.preview_error = error\n                if jpeg is not None:self.preview_error = ''"
assert text.count(old)==1
install(text.replace(old,latest));latest_only=run()
assert not latest_only['producer_error_after_start']['newer_producer_error_preserved']
assert not latest_only['producer_error_before_cached_request']['newer_producer_error_preserved']
assert latest_only['same_fid_waiters']['retired_waiter_owned_images']==12

fixed=text.replace("        self._preview_encode_lock = threading.Lock()",
    "        self._preview_encode_lock = threading.Lock()\n        self._preview_revision = self._preview_published_revision = 0")
old_publish="        with self.lock:\n            self.frames[fid] = (stamp,jpeg)"
new_publish="        with self.lock:\n            previous = self.frames.get(fid)\n            if previous is not None and previous[1] is not jpeg and isinstance(previous[1], _PreviewJpeg):\n                previous[1].retire()\n            self._preview_revision += 1\n            self._preview_published_revision = self._preview_revision\n            self.frames[fid] = (stamp,jpeg)"
assert fixed.count(old_publish)==1;fixed=fixed.replace(old_publish,new_publish)
needle="            frame = value[1]"
assert fixed.count(needle)==1;fixed=fixed.replace(needle,needle+"\n            revision = self._preview_revision")
fixed=fixed.replace(old,"            if (self.frames and fid == next(reversed(self.frames))\n                    and revision == self._preview_revision == self._preview_published_revision):\n                if error is not None:self.preview_error = error\n                if jpeg is not None:self.preview_error = ''")
needle="    def observed(self,fid,stamp,observation,inference_ms):"
assert fixed.count(needle)==1
fixed=fixed.replace(needle,"    def preview_failed(self,error):\n        with self.lock:\n            self._preview_revision += 1\n            self.preview_error = str(error)[:150]\n\n"+needle)
install(fixed);guarded=run()
assert guarded['producer_error_after_start']['newer_producer_error_preserved']
assert guarded['producer_error_before_cached_request']['newer_producer_error_preserved']
assert guarded['same_fid_waiters']['retired_waiter_owned_images']==0
assert guarded['same_fid_waiters']['unneeded_old_encodes']==0
result={'status':'PRODUCER_AND_DUPLICATE_FID_BLOCKERS_REPRODUCED_PROTOTYPE_PASSES',
    'reviewed_candidate_sha256':hashlib.sha256(raw).hexdigest(),
    'v2':baseline,'latest_fid_guard_only':latest_only,'publication_revision_and_retirement_prototype':guarded,
    'actual_loop_unique_fid_source_evidence':[
        'CameraState.captured increments capture_frames under state.lock and returns that value',
        'run.sample stores returned fid into latest tuple',
        'run.preview requires packet fid > previous and assigns previous=fid before painting'],
    'production_files_modified':False,'board_or_external_network_used':False,
    'synthetic_arrays_only':True}
(HERE/'CAMERA_PRODUCER_EDGE_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
