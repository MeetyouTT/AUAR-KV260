import base64,gzip,hashlib,json,urllib.request
from pathlib import Path
unit=hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()
assert unit=='29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
root=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136/gui-runtime')
names=('tools/realtime_controller.py','tools/streaming_controller.py','tools/realtime_facials.py',
 'tools/facial_layers.py','tools/native_pixels.py','board/interaction/avatar_player.py','tools/board_avatar_worker.py')
files={}
for n in names:
 p=root/'aura'/n
 if not p.is_file():continue
 raw=p.read_bytes();files[n]={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:'+str(port)+path,timeout=3) as r:return json.load(r)
u=get(8783,'/api/state');h=get(8790,'/health');renderer=u.get('avatar_renderer') or {}
out={'read_only':True,'unit_sha256':unit,'gui_root':str(root),'files':files,
 'camera_pid':h['pid'],'yolo_hz':h['detection_hz'],'optional':h['dpu_schedule']['optional'],
 'identity_ready':h['identity']['ready'],'feature_status':h['identity'].get('feature_status'),
 'ui':{k:u.get(k) for k in ('phase','playing','paused','audio_output_state')},
 'renderer_profile':renderer.get('profile'),'renderer_timings_ms':renderer.get('timings_ms'),
 'presentation':renderer.get('presentation')}
raw=json.dumps(out,separators=(',',':')).encode()
print(json.dumps({'gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode(),'source_files':len(files)}))
