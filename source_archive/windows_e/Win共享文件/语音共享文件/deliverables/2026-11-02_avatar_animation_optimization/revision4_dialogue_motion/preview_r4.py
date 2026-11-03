"""Public synthetic dialogue storyboard, real character GLES; no audio devices."""
from pathlib import Path
import argparse,ctypes as C,hashlib,importlib.util,json,math,subprocess,time
from egl_preview import EGL
HERE=Path(__file__).resolve().parent;W,H=423,516
STORY=[
 (0,2,'IDLE',0,1),(2,3,'AWAKE',3,1),(3,6,'LISTENING',0,1),(6,9,'THINKING',0,1),
 (9,12,'SPEAKING_NEUTRAL',0,1),(12,13,'ACK_NOD',1,1),(13,16,'SPEAKING',0,1),
 (16,17,'DENY_SHAKE',2,2),(17,20,'SPEAKING_LOW',0,2),(20,21,'PUZZLED',4,3),
 (21,23,'SPEAKING_NEUTRAL',0,3),(23,24,'PAUSED',0,3),(24,25,'CANCELLED',0,3),(25,28,'IDLE',0,3)]
def percentile(a,q):return sorted(a)[int((len(a)-1)*q)]
def module(path):
 spec=importlib.util.spec_from_file_location('preview_native',path);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);return v
def guard(e):
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==e['boot_id']
 assert hashlib.sha256(Path(e['startup_path']).read_bytes()).hexdigest()==e['startup_sha256']
 assert subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value']).strip()==b'0'
 p=Path('/proc')/str(e['camera_owner']['pid'])
 assert p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==e['camera_owner']['birth_ticks']
 assert hashlib.sha256(p.joinpath('cmdline').read_bytes()).hexdigest()==e['camera_owner']['command_sha256']
def main():
 p=argparse.ArgumentParser();p.add_argument('variant',choices=('baseline','candidate'));p.add_argument('--capture',action='store_true');p.add_argument('--name',required=True);p.add_argument('--seconds',type=float,default=28);p.add_argument('--offset',type=float,default=0);p.add_argument('--pose',type=int,choices=(0,1),default=0);a=p.parse_args()
 e=json.loads((HERE/'expected.json').read_bytes());guard(e);rt=Path(e['runtime'])
 path=HERE/('candidate/runtime/tools/native_yuki.py' if a.variant=='candidate' else 'baseline/runtime/tools/native_yuki.py')
 m=module(path);lib=HERE/('build/libaura_yuki.so' if a.variant=='candidate' else 'backup/tools/libaura_yuki.so')
 out=HERE/'previews'/a.name;out.mkdir(parents=True,exist_ok=False)
 context=EGL();native=None;gl=C.CDLL('libGLESv2.so.2');gl.glFinish.argtypes=[];rows=[]
 try:
  assets=rt/'assets/yuki';native=m.Native(lib,assets/'model.runtime.json',assets/'yuk_0.ems.resx.json',assets,1)
  start=time.monotonic();identity=None;owner=0
  for i in range(round(a.seconds*16)):
   t=a.offset+i/16;story=next((v for v in STORY if v[0]<=t<v[1]),STORY[-1]);state=story[2];action=story[3];gen=story[4]
   audible=9<=t<23;paused=state=='PAUSED';track=1 if 9<=t<24 else 0
   if (gen,track)!=identity:identity=(gen,track);owner+=1
   now=10+i/16 if a.capture else time.monotonic()
   expression=(1 if state=='SPEAKING' else 3 if state=='SPEAKING_LOW' else 4 if state=='PUZZLED' else 0)
   policy=0x200 if track else 0x100 if state=='THINKING' else 0
   value=m.Control(owner,i+1,int(t*24000),24000,track,int(audible),int(paused),expression|policy,a.pose,.8,.5+.4*math.sin(t*7) if audible else 0,now)
   if a.variant=='candidate':
    token=(1 if state=='AWAKE' else 2 if state=='ACK_NOD' else 3 if state=='DENY_SHAKE' else 4 if state=='PUZZLED' else 0)
    value=m.DialogueControl(value,gen,token,m.MOTION_STATE[state],action)
   assert native.offer(value)
   beg=time.monotonic();stats=native.render(now,W,H);gl.glFinish();end=time.monotonic()
   rows.append(dict(t=t,state=state,finished_at=end-start,total_ms=(end-beg)*1000,**stats))
   if a.capture:native.capture(out/('%04d.png'%i),W,H)
   else:time.sleep(max(0,start+(i+1)/16-time.monotonic()))
  duration=[r['total_ms'] for r in rows[16:]];interval=[(b['finished_at']-c['finished_at'])*1000 for c,b in zip(rows[16:],rows[17:])]
  report=dict(variant=a.variant,pose=a.pose,capture=a.capture,frames=len(rows),timeline_seconds=a.seconds,offset=a.offset,
   actual_completed_fps=None if a.capture else (len(rows)-17)/(rows[-1]['finished_at']-rows[16]['finished_at']),
   complete_frame_ms={k:percentile(duration,q) for k,q in [('p50',.5),('p95',.95),('p99',.99),('max',1)]},
   actual_interval_ms=None if a.capture else {k:percentile(interval,q) for k,q in [('p50',.5),('p95',.95),('p99',.99),('max',1)]},
   renderer='Actual KV260 offscreen GLES2; original GUI stopped; camera owner retained',
   audio_device_opened=False,model_service_calls=0,physical_screen_recording=False,records=rows)
  (out/'report.json').write_text(json.dumps(report,indent=2));guard(e)
  print(json.dumps({k:v for k,v in report.items() if k!='records'}))
 finally:
  if native:native.close()
  context.close()
if __name__=='__main__':main()
