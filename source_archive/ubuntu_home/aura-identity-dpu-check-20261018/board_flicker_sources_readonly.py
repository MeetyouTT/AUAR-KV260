"""Export only active rendering sources and non-personal runtime diagnostics."""
import base64,hashlib,json,subprocess,urllib.request
from pathlib import Path
pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
argv=(Path('/proc')/pid/'cmdline').read_bytes().decode().split('\0')
cpath=Path(argv[argv.index('--config')+1]);config=json.loads(cpath.read_text());runtime=Path(config['runtime']);root=runtime/'aura'
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'artifacts':{},'sources':{},'files_modified':0,'movement_commands_sent':0}
for rel in ['tools/native_video.py','tools/native_pixels.py','tools/native_pixels.cpp','tools/board_avatar_worker.py','tools/board_avatar_gtk.py','tools/x11_foreground.py','tools/board_screen_capture.py','config/board_avatar_gtk.json']:
 p=root/rel
 if not p.exists():continue
 raw=p.read_bytes();v['sources'][rel]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
 v['artifacts'][p.name]={'sha256':hashlib.sha256(raw).hexdigest(),'base64':base64.b64encode(raw).decode()}
for name in ['avatar_user_settings.json','launch.json']:
 p=runtime/name
 if name=='launch.json' and p.exists():
  launch=json.loads(p.read_text());log=Path(launch['log'])
  if log.exists():v['renderer_messages']=[s for s in log.read_text(errors='replace').splitlines() if any(k in s for k in ['GStreamer','Gtk-CRITICAL','Gdk-WARNING','X Error','FOREGROUND','VIDEO_RENDER'])][-20:]
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8783/api/state',timeout=2) as response:state=json.load(response)
v['ui']={k:state.get(k) for k in ['phase','ui_page','ui_layer','avatar_display','ui_tick_ms','error']}
print(json.dumps(v),flush=True)
