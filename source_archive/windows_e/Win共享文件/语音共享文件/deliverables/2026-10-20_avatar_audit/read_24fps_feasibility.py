"""Low-load read-only inventory; no benchmark, window, microphone or service change."""
import hashlib,json,re,shutil,subprocess,time,urllib.request
from pathlib import Path
def get():return json.load(urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4))
unit=subprocess.check_output(['systemctl','cat','aura-avatar-ui.service'],text=True)
cfg=Path(re.search(r'--config (\S+)',unit).group(1));root=Path(json.loads(cfg.read_text())['runtime'])
rows=[]
for _ in range(3):
 s=get();rows.append({k:s.get(k) for k in ('phase','asset','playing','paused','visual_time','avatar_renderer','avatar_display','ui_tick_ms')});time.sleep(.5)
import cv2
info=cv2.getBuildInformation()
plugins={}
inspect=shutil.which('gst-inspect-1.0')
if inspect:
 for name in ('appsrc','ximagesink','glimagesink'):
  result=subprocess.run([inspect,name],capture_output=True,text=True,timeout=5)
  plugins[name]={'available':result.returncode==0,'summary':result.stdout[:500] if result.returncode==0 else result.stderr[:300]}
files=['aura/tools/board_avatar_worker.py','aura/tools/board_avatar_affine.py','aura/tools/board_avatar_gtk.py','aura/tools/realtime_facials.py','aura/tools/facial_layers.py','deliverables/2026-10-06_avatar_reuse/preview_script.py']
print(json.dumps({'runtime':str(root),'unit':unit,'rows':rows,'opencv_build':info,'opencv_threads_default_in_probe_only':cv2.getNumThreads(),
 'tools':{n:shutil.which(n) for n in ('gcc','g++','cc','pkg-config','gst-inspect-1.0')},'plugins':plugins,
 'memory':Path('/proc/meminfo').read_text(),'source_hashes':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in files},
 'avatar_config':json.loads((root/'aura/config/board_avatar_gtk.json').read_text())},ensure_ascii=True))
