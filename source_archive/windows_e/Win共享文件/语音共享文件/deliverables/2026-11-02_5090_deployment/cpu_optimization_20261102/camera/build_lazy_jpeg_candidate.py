"""Build one camera-source candidate from its exact deployed bytes."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
original=HERE/'baseline/9d714b9bd00e__ui_camera_service.py'
raw=original.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='9d714b9bd00ea1da12088fa1e22100d7bdb689d0cac10332c3933b31e4f4d2df'
before=raw.decode('utf-8');after=before

def replace(old,new):
    global after
    assert after.count(old)==1,old[:100]
    after=after.replace(old,new)

provider='''class _PreviewJpeg:
    """One immutable painted BGR frame, encoded only for a JPEG request.

    The preview loop transfers its owned image here after publishing raw BGR.
    CameraState retains at most eight frames. Retiring a frame never waits for
    an encoder: only the one active encoder may retain one extra image.
    """
    def __init__(self, image, cv2, encode_lock):
        if (image.shape != (480, 640, 3) or image.dtype.name != 'uint8'
                or not image.flags.c_contiguous or not image.flags.owndata):
            raise ValueError('Expected an owned contiguous 640x480 BGR preview')
        self._image = image
        self._cv2 = cv2
        self._encode_lock = encode_lock
        self._lock = threading.Lock()
        self._retired = threading.Event()
        self._jpeg = None
        self._error = None

    def retire(self):
        self._retired.set()
        if self._lock.acquire(blocking=False):
            try:
                self._image = self._jpeg = None
            finally:
                self._lock.release()

    def resolve(self):
        with self._lock:
            if self._retired.is_set():
                return None, 'retired', None
            if self._error is not None:
                return None, 'failed_cached', self._error
            if self._jpeg is not None:
                return self._jpeg, 'cached', None
        # Match the original single preview encoder's concurrency bound.
        # Queued frames keep no per-frame lock, so eviction can free them.
        with self._encode_lock:
            with self._lock:
                if self._retired.is_set():
                    return None, 'retired', None
                if self._error is not None:
                    return None, 'failed_cached', self._error
                if self._jpeg is not None:
                    return self._jpeg, 'cached', None
                image = self._image
                self._image = None
                try:
                    ok, encoded = self._cv2.imencode('.jpg', image,
                        [self._cv2.IMWRITE_JPEG_QUALITY, 72])
                    if not ok or encoded.nbytes > 256*1024:
                        raise ValueError('Preview encoding failed or exceeded size limit')
                    jpeg = encoded.tobytes()
                except Exception as exc:
                    self._error = str(exc)[:150]
                    return None, 'failed', self._error
                finally:
                    image = None
                if self._retired.is_set():
                    return None, 'encoded_retired', None
                self._jpeg = jpeg
                return jpeg, 'encoded', None


'''
replace('class CameraState:\n',provider+'class CameraState:\n')
replace("        self.raw_preview = False\n", "        self.raw_preview = False\n        self._preview_encode_lock = threading.Lock()\n        self.preview_jpeg_encodes = self.preview_jpeg_cache_hits = self.preview_jpeg_failures = 0\n")
replace('''            while len(self.frames)>8:self.frames.popitem(last=False)
''','''            while len(self.frames)>8:
                _, (_, retired) = self.frames.popitem(last=False)
                if isinstance(retired, _PreviewJpeg):retired.retire()
''')
old='''    def preview(self,epoch,fid):
        with self.lock:
            value = self.frames.get(fid)
            if (epoch != self.camera_epoch or value is None or not 0<=self.clock()-value[0]<1000
                    or self.camera_error):return None
            return value[1]
'''
new='''    def preview(self,epoch,fid):
        with self.lock:
            value = self.frames.get(fid)
            if (epoch != self.camera_epoch or value is None or not 0<=self.clock()-value[0]<1000
                    or self.camera_error):return None
            frame = value[1]
            if not isinstance(frame, _PreviewJpeg):return frame
        # Encoding never holds the shared capture/identity state lock.
        jpeg, outcome, error = frame.resolve()
        with self.lock:
            if outcome in ('encoded','encoded_retired'):self.preview_jpeg_encodes += 1
            elif outcome == 'cached':self.preview_jpeg_cache_hits += 1
            elif outcome == 'failed':self.preview_jpeg_failures += 1
            if (epoch != self.camera_epoch or self.frames.get(fid) is not value
                    or not 0<=self.clock()-value[0]<1000 or self.camera_error):return None
            if error is not None:self.preview_error = error
            if jpeg is not None:self.preview_error = ''
            return jpeg
'''
replace(old,new)
replace("                'preview_frames':self.preview_frames,'preview_hz':round(self.preview_frames/seconds,2),\n", "                'preview_frames':self.preview_frames,'preview_hz':round(self.preview_frames/seconds,2),\n                'preview_jpeg_mode':'on_request_cache','preview_jpeg_encodes':self.preview_jpeg_encodes,\n                'preview_jpeg_cache_hits':self.preview_jpeg_cache_hits,'preview_jpeg_failures':self.preview_jpeg_failures,\n")
replace('''                    ok,encoded=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,72])
                    if not ok or encoded.nbytes>256*1024:raise ValueError('Preview encoding failed or exceeded size limit')
                    state.publish_preview(fid,stamp,encoded.tobytes())
''','''                    state.publish_preview(fid,stamp,_PreviewJpeg(image,cv2,state._preview_encode_lock))
''')
tree_before=ast.parse(before);tree_after=ast.parse(after)
run_before=next(node for node in tree_before.body if isinstance(node,ast.FunctionDef) and node.name=='run')
run_after=next(node for node in tree_after.body if isinstance(node,ast.FunctionDef) and node.name=='run')
for name in ('sample','inference'):
    a=next(node for node in ast.walk(run_before) if isinstance(node,ast.FunctionDef) and node.name==name)
    b=next(node for node in ast.walk(run_after) if isinstance(node,ast.FunctionDef) and node.name==name)
    assert ast.dump(a)==ast.dump(b),name+' must be unchanged'
compile(after,str(original),'exec')
candidate=HERE/'candidate_v2';candidate.mkdir(exist_ok=True)
destination=candidate/'ui_camera_service.py'
with destination.open('xb') as stream:stream.write(after.encode('utf-8'))
with (HERE/'LAZY_JPEG_V2.diff').open('x',encoding='utf-8') as stream:
    stream.writelines(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='deployed/ui_camera_service.py',tofile='candidate/ui_camera_service.py'))
report={'baseline_sha256':hashlib.sha256(raw).hexdigest(),'candidate_sha256':hashlib.sha256(after.encode()).hexdigest(),
    'changed_files':['board/vision/ui_camera_service.py'],'capture_callback_ast_identical':True,'inference_ast_identical':True,
    'quality':72,'jpeg_limit_bytes':256*1024,'cached_frame_limit':8,'jpeg_ttl_ms':1000,
    'owned_bgr_bytes_per_frame':640*480*3,'owned_bgr_cache_max_bytes':8*640*480*3,
    'active_encoder_max_extra_bgr_bytes':640*480*3,
    'publishing_frame_max_extra_bgr_bytes':640*480*3,'board_mutations':False}
with (HERE/'CANDIDATE_MANIFEST_V2.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report))
