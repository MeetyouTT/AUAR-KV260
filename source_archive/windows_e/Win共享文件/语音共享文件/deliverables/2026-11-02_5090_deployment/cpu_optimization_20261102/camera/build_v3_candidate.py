"""Build the reviewed correction from immutable v2; no board operations."""
import ast,difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
base=(HERE/'baseline/9d714b9bd00e__ui_camera_service.py').read_bytes()
v2=(HERE/'candidate_v2/ui_camera_service.py').read_bytes()
assert hashlib.sha256(v2).hexdigest()=='0bf23f511f6f85512603277b1496c704fcd792a4f1a0fc97854ead03441920bf'
text=v2.decode('utf-8')
def change(old,new):
    global text
    assert text.count(old)==1,old[:120]
    text=text.replace(old,new)
change('''    def resolve(self):
        with self._lock:
            if self._retired.is_set():
                return None, 'retired', None
            if self._error is not None:
                return None, 'failed_cached', self._error
            if self._jpeg is not None:
                return self._jpeg, 'cached', None
''','''    def resolve(self):
''')
change('''        self._preview_encode_lock = threading.Lock()
''','''        self._preview_encode_lock = threading.Lock()
        self._preview_producer_failed = False
''')
change('''    def publish_preview(self,fid,stamp,jpeg):
        with self.lock:
            self.frames[fid] = (stamp,jpeg)
''','''    def publish_preview(self,fid,stamp,jpeg):
        with self.lock:
            previous = self.frames.get(fid)
            if previous is not None and previous[1] is not jpeg and isinstance(previous[1], _PreviewJpeg):
                previous[1].retire()
            self.frames[fid] = (stamp,jpeg)
''')
change('''            self.preview_frames += 1
            self.preview_error = ''
''','''            self.preview_frames += 1
            self._preview_producer_failed = False
            self.preview_error = ''

    def preview_failed(self,error):
        with self.lock:
            self._preview_producer_failed = True
            self.preview_error = str(error)[:150]
''')
change('''            if error is not None:self.preview_error = error
            if jpeg is not None:self.preview_error = ''
''','''            if (not self._preview_producer_failed and self.frames
                    and fid == next(reversed(self.frames))):
                if error is not None:self.preview_error = error
                if jpeg is not None:self.preview_error = ''
''')
change('''                    with state.lock:state.preview_error=str(exc)[:150]
''','''                    state.preview_failed(exc)
''')
compile(text,'<camera-lazy-jpeg-v3>','exec')
root=HERE/'candidate_v3';root.mkdir(exist_ok=True)
destination=root/'ui_camera_service.py'
with destination.open('xb') as stream:stream.write(text.encode())
with (HERE/'LAZY_JPEG_V3.diff').open('x',encoding='utf-8') as stream:
    stream.writelines(difflib.unified_diff(base.decode().splitlines(keepends=True),text.splitlines(keepends=True),fromfile='deployed/ui_camera_service.py',tofile='candidate_v3/ui_camera_service.py'))
report={'revision':3,'baseline_sha256':hashlib.sha256(base).hexdigest(),'rejected_v2_sha256':hashlib.sha256(v2).hexdigest(),
    'candidate_sha256':hashlib.sha256(text.encode()).hexdigest(),'changed_files':['board/vision/ui_camera_service.py'],
    'producer_health_failure_flag':True,'latest_fid_and_tuple_identity_guard':True,
    'same_fid_replacement_retires_previous_provider':True,'global_encoder_before_frame_lock':True,
    'quality':72,'jpeg_limit_bytes':256*1024,'cached_frame_limit':8,'jpeg_ttl_ms':1000,
    'owned_bgr_cache_max_bytes':8*640*480*3,'active_encoder_max_extra_bgr_bytes':640*480*3,
    'publishing_frame_max_extra_bgr_bytes':640*480*3,'board_mutations':False}
with (HERE/'CANDIDATE_MANIFEST_V3.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report))
