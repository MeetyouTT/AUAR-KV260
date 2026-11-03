import hashlib,json,sys,time,urllib.request
from pathlib import Path
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v10r15')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='da36c36a-ef4d-4122-8ad6-cfae3931303e'
assert hashlib.sha256((P/'deployment-manifest.json').read_bytes()).hexdigest()=='c72cfb9138889554b03cf224557dcb79bca1ee70b466a822fda3b09254bba2de'
assert all(hashlib.sha256(Path(x['destination']).read_bytes()).hexdigest()==x['sha256'] for x in json.loads((P/'deployment-manifest.json').read_text())['files'])
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def ui():
 with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:return json.load(f)['manual_pan']
before=ui();assert not before['automatic_following'] and before['state']=='FAULT'
sys.path.insert(0,str(P))
from face_stream import FaceStream
from input_timing import InputTiming
stream=FaceStream();timing=InputTiming();start=time.monotonic();last=None;events={}
try:
 while time.monotonic()-start<8:
  for kind,p in stream.drain():
   if kind=='packet':
    timing.observe(p,{'reason':'READONLY_NO_ADMISSION'},int(time.monotonic()*1000))
    if p.get('state')=='READY':last={'source_frame_id':p.get('source_frame_id'),'frame_width':p.get('frame_width'),'target':p.get('target')}
   else:events[kind]=events.get(kind,0)+1
  time.sleep(.01)
finally:stream.close()
after=ui();assert not after['automatic_following'] and after['state']=='FAULT'
print(json.dumps({'duration_s':round(time.monotonic()-start,3),'input':timing.snapshot(),'last_ready_face_geometry':last,
 'stream_events':events,'queue':stream.diagnostics(),'motor_commands':0,'MMIO_opened':False,'scope':'numeric face target only; no identity labels or image'}))
