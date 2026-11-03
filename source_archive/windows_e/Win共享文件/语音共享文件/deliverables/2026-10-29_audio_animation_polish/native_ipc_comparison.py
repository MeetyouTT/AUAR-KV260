"""Actual ARM/GStreamer fakesink comparison; never opens ALSA/microphone/display."""
import base64,hashlib,json,sys,textwrap
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1]
sys.path.insert(0,str(P/'deliverables/2026-10-18_board_dialogue'));from board_ssh import ssh
b=json.loads((H/'baseline.json').read_text(encoding='utf-8'))
payload={}
for version,directory in [('before','board_source'),('candidate','candidate/board')]:
 for name in ('gstreamer_audio_worker.py','gstreamer_persistent_engine.py'):
  payload[version+'/'+name]=base64.b64encode((H/directory/'tools'/name).read_bytes()).decode()
script=r'''
import base64,fcntl,hashlib,json,math,os,sys,threading,time,types,urllib.request
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
root=Path(ROOT)/'aura';sys.path.insert(0,str(root))
for name in ('tools/gstreamer_audio_worker.py','tools/gstreamer_persistent_engine.py'):
 assert hashlib.sha256((root/name).read_bytes()).hexdigest()==PINS[name]
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as response:s=json.load(response)
assert s['phase']=='IDLE' and not s['playing'] and not s['handsfree_dialogue']['enabled']
import gi
gi.require_version('Gst','1.0')
from gi.repository import Gst
Gst.init(None)
modules={}
for key,value in SOURCES.items():
 module=types.ModuleType('lab_'+key.replace('/','_').replace('.','_'));module.__file__=str(root/'tools'/key.split('/')[-1])
 exec(compile(base64.b64decode(value),module.__file__,'exec'),module.__dict__);modules[key]=module
import array
samples=array.array('h',(round(8000*math.sin(2*math.pi*240*i/24000)) for i in range(24000*3)))
if sys.byteorder!='little':samples.byteswap()
pcm=samples.tobytes();expected=hashlib.sha256(pcm).hexdigest();results=[]
for version in ('before','candidate'):
 engine_module=modules[version+'/gstreamer_persistent_engine.py']
 worker_module=modules[version+'/gstreamer_audio_worker.py']
 arrivals=[];contents=hashlib.sha256();content_bytes=[0]
 def handoff(sink,buffer,pad):
  success,mapping=buffer.map(Gst.MapFlags.READ)
  assert success
  raw=bytes(mapping.data);buffer.unmap(mapping)
  if any(raw):
   arrivals.append((time.monotonic(),int(buffer.pts),int(buffer.duration)))
   contents.update(raw);content_bytes[0]+=len(raw)
 def factory(gst,device):
  pipeline=gst.Pipeline.new('aura-ipc-lab-'+version)
  source=gst.ElementFactory.make('appsrc','lab-source');sink=gst.ElementFactory.make('fakesink','lab-sink')
  source.set_property('caps',gst.Caps.from_string('audio/x-raw,format=S16LE,layout=interleaved,rate=24000,channels=1'))
  source.set_property('format',gst.Format.TIME);source.set_property('is-live',True)
  source.set_property('block',False);source.set_property('max-bytes',7680)
  sink.set_property('sync',True);sink.set_property('signal-handoffs',True);sink.connect('handoff',handoff)
  pipeline.add(source);pipeline.add(sink);assert source.link(sink)
  return pipeline,source,sink
 engine=engine_module.PersistentGstAudioEngine(Gst,'FAKESINK_NO_DEVICE',pipeline_factory=factory)
 deadline=time.monotonic()+3
 while not engine.poll()['device_ready']:
  assert not engine.error and time.monotonic()<deadline;time.sleep(.01)
 engine.take_references();readfd,writefd=os.pipe()
 pipe_size=fcntl.fcntl(writefd,getattr(fcntl,'F_SETPIPE_SZ',1031),4096);assert pipe_size==4096
 os.set_blocking(readfd,False);stop=threading.Event();started=time.monotonic();drained=[0]
 def reader():
  while not stop.is_set():
   elapsed=time.monotonic()-started
   # Controlled 240ms desktop-reader stalls on an owned laboratory pipe.
   if elapsed%.5<.24:stop.wait(.005);continue
   try:
    while True:drained[0]+=len(os.read(readfd,65536))
   except BlockingIOError:pass
   stop.wait(.002)
 consumer=threading.Thread(target=reader,daemon=True);consumer.start()
 publisher=worker_module.NonBlockingAudioPublisher(writefd) if version=='candidate' else None
 def emit(value):
  if publisher:publisher.publish(value);publisher.flush()
  else:os.write(writefd,('AUDIO '+json.dumps(value)+'\n').encode())
 engine.command({'type':'stream','token':1})
 for start in range(0,len(pcm)//2,480):
  engine.command({'type':'pcm','token':1,'start_sample':start,'pcm':base64.b64encode(pcm[start*2:(start+480)*2]).decode()})
 engine.command({'type':'end','token':1});poll_times=[];until=time.monotonic()+10
 try:
  while time.monotonic()<until:
   before=time.monotonic();snapshot=engine.poll();emit(dict(snapshot,kind='state'))
   for reference in engine.take_references():
    reference=dict(reference,kind='reference',pcm=base64.b64encode(reference['pcm']).decode());emit(reference)
   poll_times.append((time.monotonic()-before)*1000)
   assert not engine.error,engine.error
   if engine.done:break
   time.sleep(.01)
  assert engine.done and content_bytes[0]==len(pcm) and contents.hexdigest()==expected
  intervals=[(right[0]-left[0])*1000 for left,right in zip(arrivals,arrivals[1:])]
  pts_gaps=[max(0,right[1]-left[1]-left[2])/1e6 for left,right in zip(arrivals,arrivals[1:])]
  results.append({'version':version,'status':'PASS','pipe_bytes':pipe_size,'content_bytes':content_bytes[0],'pcm_sha256':contents.hexdigest(),
   'maximum_content_delivery_interval_ms':round(max(intervals),2),
   'delivery_intervals_over_80ms':sum(value>80 for value in intervals),
   'maximum_timestamp_gap_ms':round(max(pts_gaps),2),'maximum_poll_and_ipc_ms':round(max(poll_times),2),
   'publisher':publisher.snapshot() if publisher else None})
 finally:
  engine.release();stop.set();consumer.join(1);os.close(readfd);os.close(writefd)
assert results[0]['maximum_poll_and_ipc_ms']>100
assert results[1]['maximum_poll_and_ipc_ms']<results[0]['maximum_poll_and_ipc_ms']/2
assert results[1]['delivery_intervals_over_80ms']<results[0]['delivery_intervals_over_80ms']
print(json.dumps({'status':'PASS','scope':'native_GStreamer_fakesink_and_owned_pipe_backpressure',
 'results':results,'device_opened':False,'microphone_opened':False,'physical_playback':False,'motion_command_sent':False}))
'''.replace('BOOT',repr(b['boot'])).replace('ROOT',repr(b['runtime'])).replace('PINS',repr(b['pins'])).replace('SOURCES',repr(payload))
previous=H/'native_ipc_comparison.json'
if previous.exists():
 earlier=json.loads(previous.read_text(encoding='utf-8'))
 assert earlier['status']=='FAIL' and 'F_SETPIPE_SZ' in earlier['error']
 target=H/'native_ipc_comparison_setup_failure.json';assert not target.exists();previous.rename(target)
script="import json,traceback\ntry:\n"+textwrap.indent(script,' ')+"\nexcept Exception as exc:\n print(json.dumps({'status':'FAIL','results':globals().get('results',[]),'error':type(exc).__name__+': '+str(exc),'trace':traceback.format_exc()}))\n"
report={'status':'STARTING'}
try:
 raw=ssh('python3 -B -',script,timeout=45);report=json.loads(raw.strip().splitlines()[-1]);assert report['status']=='PASS'
except Exception as exc:report['status']='FAIL';report.setdefault('error',type(exc).__name__+': '+str(exc))
(H/'native_ipc_comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True))
raise SystemExit(0 if report['status']=='PASS' else 1)
