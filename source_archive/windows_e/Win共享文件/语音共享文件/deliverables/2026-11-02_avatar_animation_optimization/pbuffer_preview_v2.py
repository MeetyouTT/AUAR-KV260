"""One character-only offscreen GLES owner; no audio/camera/model/business I/O."""
from pathlib import Path
import argparse,ctypes as C,json,math,os,time,sys
HERE=Path(__file__).resolve().parent
W,H=423,516
class EGL:
 def __init__(self):
  I,U,P=C.c_int,C.c_uint,C.c_void_p
  env=json.loads((HERE/'display_environment.json').read_bytes())
  assert set(env)<=set(('DISPLAY','XAUTHORITY')) and 'DISPLAY' in env
  os.environ.update(env)
  self.x=C.CDLL('libX11.so.6');self.x.XOpenDisplay.argtypes=[C.c_char_p];self.x.XOpenDisplay.restype=P;self.x.XCloseDisplay.argtypes=[P]
  self.e=C.CDLL('libEGL.so.1')
  for name,result,args in [('eglGetDisplay',P,[P]),('eglInitialize',I,[P,C.POINTER(I),C.POINTER(I)]),('eglBindAPI',I,[U]),('eglChooseConfig',I,[P,C.POINTER(I),C.POINTER(P),I,C.POINTER(I)]),('eglCreatePbufferSurface',P,[P,P,C.POINTER(I)]),('eglCreateContext',P,[P,P,P,C.POINTER(I)]),('eglMakeCurrent',I,[P,P,P,P]),('eglDestroyContext',I,[P,P]),('eglDestroySurface',I,[P,P]),('eglTerminate',I,[P])]:
   f=getattr(self.e,name);f.restype=result;f.argtypes=args
  self.xd=self.x.XOpenDisplay(None);assert self.xd
  self.d=self.e.eglGetDisplay(self.xd);assert self.e.eglInitialize(self.d,C.byref(I()),C.byref(I()));assert self.e.eglBindAPI(0x30A0)
  attrs=(I*13)(0x3033,1,0x3040,4,0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3038);cfg=P();count=I()
  assert self.e.eglChooseConfig(self.d,attrs,C.byref(cfg),1,C.byref(count)) and count.value
  self.s=self.e.eglCreatePbufferSurface(self.d,cfg,(I*5)(0x3057,W,0x3056,H,0x3038));self.c=self.e.eglCreateContext(self.d,cfg,None,(I*3)(0x3098,2,0x3038))
  assert self.s and self.c and self.e.eglMakeCurrent(self.d,self.s,self.s,self.c)
 def close(self):
  self.e.eglMakeCurrent(self.d,None,None,None);self.e.eglDestroyContext(self.d,self.c);self.e.eglDestroySurface(self.d,self.s);self.e.eglTerminate(self.d);self.x.XCloseDisplay(self.xd)
def percentile(values,q):
 a=sorted(values);return a[int((len(a)-1)*q)]
def main():
 p=argparse.ArgumentParser();p.add_argument('variant',choices=('baseline','candidate_physics'));p.add_argument('--capture',action='store_true');p.add_argument('--name',required=True);p.add_argument('--seconds',type=float,default=12);args=p.parse_args()
 e=json.loads((HERE/'expected.json').read_bytes());rt=Path(e['runtime'])
 assert json.loads(os.popen('systemctl show aura-avatar-ui.service -p MainPID --value').read() or '0')==0
 sys.path.insert(0,str(rt/'tools'));from native_yuki import Native,Control
 library=HERE/'backup/tools/libaura_yuki.so' if args.variant=='baseline' else HERE/'revision2b/libaura_yuki.so'
 out=HERE/'previews'/args.name;out.mkdir(parents=True,exist_ok=False)
 context=EGL();native=None;gl=C.CDLL('libGLESv2.so.2');gl.glFinish.argtypes=[]
 records=[]
 try:
  assets=rt/'assets/yuki';native=Native(library,assets/'model.runtime.json',assets/'yuk_0.ems.resx.json',assets,seed=1)
  start=time.monotonic();deadline=start
  for i in range(round(args.seconds*16)):
   t=i/16;now=10+t if args.capture else time.monotonic();answer=6<=t<10
   seq=i+1;sample=int(t*24000);v=Control(1,seq,sample,24000,int(answer),int(answer),0,0x200 if answer else 0,0,.8,.5+.4*math.sin(t*7) if answer else 0,now)
   assert native.offer(v);beg=time.monotonic();s=native.render(now,W,H);gl.glFinish();end=time.monotonic()
   records.append(dict(t=t,finished_at=end-start,total_ms=(end-beg)*1000,**s))
   if args.capture:native.capture(out/('%04d.png'%i),W,H)
   else:
    deadline=start+(i+1)/16;time.sleep(max(0,deadline-time.monotonic()))
  durations=[x['total_ms'] for x in records[16:]];intervals=[(b['finished_at']-a['finished_at'])*1000 for a,b in zip(records[16:],records[17:])]
  report=dict(variant=args.variant,capture=args.capture,frames=len(records),timeline_seconds=args.seconds,
      deterministic_16fps_replay=args.capture,actual_completed_fps=None if args.capture else (len(records)-17)/(records[-1]['finished_at']-records[16]['finished_at']),
      complete_frame_ms={k:percentile(durations,q) for k,q in [('p50',.5),('p95',.95),('p99',.99),('max',1)]},
      actual_interval_ms=None if args.capture else {k:percentile(intervals,q) for k,q in [('p50',.5),('p95',.95),('p99',.99),('max',1)]},
      evaluate_ms={k:percentile([x['evaluate_ms'] for x in records[16:]],q) for k,q in [('p50',.5),('p95',.95)]},
      scope='Real KV260 offscreen character GLES, camera retained, production GUI stopped; synthetic public audio envelope only',
      audio_device_opened=False,camera_or_people_captured=False,records=records)
  (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='records'}))
 finally:
  if native:native.close()
  context.close()
if __name__=='__main__':main()
