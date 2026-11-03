import base64,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
job=r'''
import sys,time,json,os
from pathlib import Path
import gi
gi.require_version('Gtk','3.0');gi.require_version('GdkX11','3.0')
from gi.repository import Gtk,Gdk,GdkX11,GLib
sys.path.insert(0,'/home/root/aura-voice-barge-in-20261020/candidate-667b70d586ca/runtime/aura')
from tools.native_video import NativeVideo
from PIL import Image
library=sys.argv[1];window=Gtk.Window();window.set_accept_focus(False);window.realize();window.get_window().set_override_redirect(True);window.move(-2500,-2500)
area=Gtk.DrawingArea();area.set_size_request(423,438);window.add(area);window.show_all()
handle=GdkX11.X11Window.get_xid(area.get_window());Gdk.Display.get_default().sync()
video=NativeVideo(library,(423,438));video.attach(handle)
raw=Image.open('/home/root/aura-render24-20261020/candidate-45f9f5cd2aaa/IDLE.png').convert('RGB').tobytes()
start=time.monotonic();cpu=time.process_time();rows=[];sequence=0
def push():
 global sequence
 b=time.monotonic();sequence+=1;video.push(raw,sequence);rows.append((time.monotonic()-b)*1000)
 if time.monotonic()-start<15:return True
 rows.sort();report={'process_cpu_percent':(time.process_time()-cpu)/(time.monotonic()-start)*100,'push_p50_ms':rows[len(rows)//2],'push_p95_ms':rows[int(len(rows)*.95)]}
 try:report['sink']=video.read()
 except Exception as exc:report['error']=str(exc)
 video.close();window.destroy();Gtk.main_quit();print(json.dumps(report));return False
GLib.timeout_add(42,push);Gtk.main()
'''
remote=r'''
import subprocess,json,base64,os
from pathlib import Path
p=Path('/home/root/aura-render24-prototype-20261020/direct-display');p.mkdir(exist_ok=True)
(p/'direct.cpp').write_bytes(base64.b64decode(SOURCE));(p/'probe.py').write_bytes(base64.b64decode(JOB))
flags=subprocess.check_output(['pkg-config','--cflags','--libs','gstreamer-app-1.0','gstreamer-video-1.0'],text=True).split()
r=subprocess.run(['g++','-O3','-DNDEBUG','-fPIC','-shared','-std=c++14',str(p/'direct.cpp'),'-o',str(p/'direct.so'),'-I/usr/include/opencv4','-lopencv_core','-lopencv_imgproc',*flags],capture_output=True,text=True,timeout=60)
assert r.returncode==0,r.stderr
env=dict(os.environ,DISPLAY=':0',PYTHONDONTWRITEBYTECODE='1');results={}
for name,lib in [('original','/home/root/aura-voice-barge-in-20261020/candidate-667b70d586ca/runtime/aura/tools/libaura_pixels.so'),('direct',str(p/'direct.so'))]:
 try:
  r=subprocess.run(['python3','-B',str(p/'probe.py'),lib],env=env,capture_output=True,text=True,timeout=25);results[name]={'code':r.returncode,'out':r.stdout,'error':r.stderr}
 except subprocess.TimeoutExpired as exc:results[name]={'code':124,'out':str(exc.stdout),'error':str(exc.stderr)}
 (p/'results.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results))
'''.replace('SOURCE',repr(base64.b64encode((HERE/'direct_bgrx.cpp').read_bytes()).decode())).replace('JOB',repr(base64.b64encode(job.encode()).decode()))
r=json.loads(ssh('python3 -B -',remote,timeout=140));(HERE/'direct_probe.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
