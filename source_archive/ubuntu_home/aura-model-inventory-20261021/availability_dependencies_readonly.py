import base64,hashlib,json,subprocess
from pathlib import Path
unit=Path('/etc/systemd/system/aura-camera-ui.service')
assert hashlib.sha256(unit.read_bytes()).hexdigest()=='a29082bae1d382d7a43505d5a1d3a51fa2203081423755900e9d72836385e343'
parent=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-sface-int8-9025bd49fe52-333217')
cfg=json.loads(Path('/home/root/aura-speech-motion-20261021/de989bf024a9/startup/config.json').read_text())
gui=Path(cfg['runtime']);gui=gui/'aura' if (gui/'aura/board').is_dir() else gui
paths={'camera_pipeline_metrics':parent/'aura/board/vision/pipeline_metrics.py',
 'gui_spoken_query':gui/'board/identity/spoken_query.py',
 'gui_render_performance':gui/'tools/render_performance.py'}
files={}
for name,p in paths.items():
 if not p.is_file():files[name]={'exists':False};continue
 raw=p.read_bytes();files[name]={'exists':True,'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
 if name!='gui_render_performance':files[name]['base64']=base64.b64encode(raw).decode()
print(json.dumps({'read_only':True,'gui_root':str(gui),'files':files,
 'gui_main_pid':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value']).decode().strip()}))
