"""Only the public avatar frame endpoint; never the camera/full screen."""
import base64,hashlib,io,json,sys
from board_guard import H,capture,ssh
sys.path.insert(0,r'C:\Users\35870\.codex\visualizations\2026\10\26\01a1772c-f263-75f1-bfa1-9bd865e5caa9\animation-fps-deps')
from PIL import Image
b=capture();assert b['safe'] and not b['mismatches']
script=r'''
import base64,json,urllib.request
with urllib.request.urlopen('http://127.0.0.1:8783/api/frame',timeout=4) as r:
 assert r.headers.get_content_type()=='image/jpeg'
 raw=r.read(2000000);assert raw.startswith(b'\xff\xd8')
print(json.dumps({'image':base64.b64encode(raw).decode()}))
'''
data=json.loads(ssh('python3 -B -',script,timeout=12));raw=base64.b64decode(data['image']);im=Image.open(io.BytesIO(raw))
assert im.size[0]<=464 and im.size[1]<=480
im.save(H/'actual_avatar.png')
v=dict(status='PASS',source='existing UI /api/frame avatar only',size=im.size,image_sha256=hashlib.sha256(raw).hexdigest(),
 ui_pid=b['ui']['MainPID'],phase=b['state']['phase'],portrait=b['state']['portrait_offload'],camera_or_identity_pixels_saved=False)
(H/'avatar_capture.json').write_text(json.dumps(v,indent=2),encoding='utf-8');print(json.dumps(v))
