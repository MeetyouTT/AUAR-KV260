"""Run only after the board's interactive testing window is released."""
import json,base64,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'2026-10-18_board_dialogue'))
from board_ssh import ssh
b=json.loads((HERE/'active_render_sources.json').read_text(encoding='utf-8-sig'))
job=r'''
import sys,json,time,statistics,ctypes as C
from pathlib import Path
import numpy as np
root=Path(ROOT);sys.path.insert(0,str(root/'aura'))
from tools.board_avatar_gtk import create_runtime_core
from tools.demo_script import create_demo_core
from tools.realtime_facials import RealtimeFacials
from tools.native_pixels import NativePixels
core=create_runtime_core(create_demo_core);core.MAX_CACHED_SEQUENCES=12;facials=RealtimeFacials(core)
native=NativePixels(LIB,'white',threads=2);native.lib.aura_pixels_resize_mode.argtypes=[C.c_void_p,C.c_int];native.configure(core)
states=('IDLE','LISTENING','THINKING','SPEAKING_NEUTRAL','SPEAKING','SPEAKING_LOW','ACK_NOD','DENY_SHAKE','AWAKE','PUZZLED');quality={1:[],2:[]};perf={}
for state in states:
 for t in (.3,1.31,1.42,3.4):
  native.lib.aura_pixels_resize_mode(native.owner,0);ref=facials.apply(core.frame_at(state,t),t,.7,.6)['image']
  for mode in (1,2):
   native.lib.aura_pixels_resize_mode(native.owner,mode);got=facials.apply(core.frame_at(state,t),t,.7,.6)['image']
   diff=np.abs(np.asarray(got,dtype=np.int16)-np.asarray(ref,dtype=np.int16));quality[mode].append({'state':state,'t':t,'mean':float(diff.mean()),'p99':float(np.percentile(diff,99)),'max':int(diff.max())})
for threads in (2,3):
 native.lib.aura_pixels_threads(threads)
 for mode in (0,1,2):
  native.lib.aura_pixels_resize_mode(native.owner,mode);wall=[];kernels=[]
  for i in range(72):
   t=4+i/24;start=time.monotonic();facials.apply(core.frame_at('IDLE',t),t,.7,.6);wall.append((time.monotonic()-start)*1000);kernels.append(native.cpu_times())
  wall.sort();perf[str((threads,mode))]={'p50':statistics.median(wall),'p95':wall[int(len(wall)*.95)],'max':max(wall),'kernel_cpu':{k:statistics.median(r[k] for r in kernels) for k in kernels[0]}}
native.close();print(json.dumps({'quality':quality,'performance':perf,'quality_accepted':{mode:all(r['mean']<=1.5 and r['p99']<=10 for r in rows) for mode,rows in quality.items()}}))
'''
remote=r'''
import json,subprocess,base64,os
from pathlib import Path
p=Path('/home/root/aura-render24-prototype-20261020/budget');p.mkdir(exist_ok=True);(p/'pixels.cpp').write_bytes(base64.b64decode(CPP))
flags=subprocess.check_output(['pkg-config','--cflags','--libs','gstreamer-app-1.0','gstreamer-video-1.0'],text=True).split()
r=subprocess.run(['g++','-O3','-DNDEBUG','-fPIC','-shared','-std=c++14',str(p/'pixels.cpp'),'-o',str(p/'pixels.so'),'-I/usr/include/opencv4','-lopencv_core','-lopencv_imgproc',*flags],capture_output=True,text=True,timeout=65);assert r.returncode==0,r.stderr
job=base64.b64decode(JOB).decode().replace('ROOT',repr(ROOTPATH),1).replace('LIB',repr(str(p/'pixels.so')),1);(p/'probe.py').write_text(job)
r=subprocess.run(['python3','-B',str(p/'probe.py')],capture_output=True,text=True,timeout=220,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
result={'code':r.returncode,'out':r.stdout,'error':r.stderr};(p/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''.replace('CPP',repr(base64.b64encode((HERE/'budget_prototype/native_pixels.cpp').read_bytes()).decode()),1).replace('JOB',repr(base64.b64encode(job.encode()).decode()),1).replace('ROOTPATH',repr(b['runtime']),1)
r=json.loads(ssh('python3 -B -',remote,timeout=310));(HERE/'budget_probe.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
