import base64,gzip,hashlib,json,subprocess,urllib.request
from pathlib import Path
root=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136/gui-runtime')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha('/etc/systemd/system/aura-camera-ui.service')=='29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512'
files={}
for name in ('tools/board_avatar_gtk.py','tools/board_camera_preview.py','tools/native_video.py',
             'tools/native_pixels.cpp','tools/native_pixels.py','tools/board_avatar_worker.py','tools/board_avatar_pan.py'):
    p=root/'aura'/name
    if p.is_file():
        raw=p.read_bytes();files[name]={'sha256':sha(p),'base64':base64.b64encode(raw).decode()}
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
    with op.open('http://127.0.0.1:'+str(port)+path,timeout=4) as r:return json.load(r)
u=get(8783,'/api/state');h=get(8790,'/health')
out={'files':files,'gui_root':str(root),'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
     'camera_pid':h['pid'],'detection_hz':h['detection_hz'],'optional':h['dpu_schedule']['optional'],
     'recovery':h['dpu_schedule']['yunet_recovery'],'owner_fenced':h['dpu_schedule']['owner_fenced'],
     'feature_inference':h['identity']['feature_inference'],'identity_ready':h['identity']['ready'],
     'ui':{key:u.get(key) for key in ('phase','playing','paused','audio_output_state','avatar_display')},
     'ui_keys':list(u),'renderer_profile':u.get('avatar_renderer',{}).get('profile'),
     'library_sha256':sha(root/'aura/tools/libaura_pixels.so'),
     'gui_pid':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value']).decode().strip()}
raw=json.dumps(out,separators=(',',':')).encode()
print(json.dumps({'gzip_base64':base64.b64encode(gzip.compress(raw,mtime=0)).decode()}))
