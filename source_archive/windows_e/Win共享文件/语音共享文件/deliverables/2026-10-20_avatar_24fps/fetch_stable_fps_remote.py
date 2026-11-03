import json,subprocess,re,base64
from pathlib import Path
value=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'],text=True)
cfgpath=Path(re.search(r'--config (\S+) ',value).group(1));cfg=json.loads(cfgpath.read_text());root=Path(cfg['runtime'])
names=['aura/tools/realtime_controller.py','aura/tools/streaming_controller.py','aura/tools/board_avatar_gtk.py','aura/tools/board_avatar_worker.py','aura/tools/native_pixels.py','aura/tools/native_pixels.cpp','aura/tools/board_camera_preview.py','aura/config/board_avatar_gtk.json']
print(json.dumps({'runtime':str(root),'config_path':str(cfgpath),'files':{n:base64.b64encode((root/n).read_bytes()).decode() for n in names}}))
