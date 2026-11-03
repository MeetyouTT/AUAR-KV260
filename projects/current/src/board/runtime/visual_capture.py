"""Read the existing camera owner's immutable JPEG; never open another camera."""
import hashlib,json,time,urllib.request
from urllib.parse import urlencode
from board.interaction.ui_contract import validate_snapshot
from common.visual_question import MAX_JPEG,validate_jpeg

def current_frame(boot_id,*,is_current=lambda:True):
    def check():
        if not is_current():raise InterruptedError('Cancelled image question')
    check()
    with urllib.request.urlopen('http://127.0.0.1:8790/v1/ui/status',timeout=1) as r:raw=r.read(131073)
    if len(raw)>131072:raise ValueError('Visual snapshot exceeds bound')
    now=round(time.monotonic()*1000)
    value=validate_snapshot(json.loads(raw),boot_id,now);ref=value.get('preview')
    if (value['source_kind']!='actual' or value['modules']['camera']['state']!='READY' or not ref
        or not 0<=now-ref['captured_mono_ms']<750):raise ValueError('Fresh camera frame unavailable')
    check()
    path='http://127.0.0.1:8790/v1/ui/preview.jpg?'+urlencode({k:ref[k] for k in ('camera_epoch','frame_id')})
    with urllib.request.urlopen(path,timeout=1) as r:
        if (r.headers.get('X-Aura-Boot-Id')!=boot_id or r.headers.get('X-Aura-Camera-Epoch')!=ref['camera_epoch']
            or r.headers.get('X-Aura-Frame-Id')!=str(ref['frame_id'])):raise ValueError('Camera frame owner changed')
        jpeg=r.read(MAX_JPEG+1)
    check()
    frame=dict(ref,board_boot_id=boot_id,observed_mono_ms=round(time.monotonic()*1000),sha256=hashlib.sha256(jpeg).hexdigest())
    validate_jpeg(frame,jpeg)
    return frame,jpeg

