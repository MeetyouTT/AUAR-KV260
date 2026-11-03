"""Public-PCM fixture and exact legacy controller assembly for paired A/B.

Importing this module does not load Gst, assets, sockets, devices or services.
The coordinator may reuse these helpers in B to match business/PCM work.
"""
from pathlib import Path
import hashlib
import importlib
import importlib.util
import json
import math
import shutil
import sys
import threading
import time
import wave

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_scenario(path):
    value=json.loads(Path(path).read_text(encoding='utf8'))
    if value.get('schema')!='aura.paired_ab.scenario.v1':raise ValueError('Scenario schema differs')
    if value.get('fps')!=16 or value.get('size')!=[423,438]:raise ValueError('Pair must be16fps/423x438')
    for key in ('duration_seconds','warmup_seconds'):
        if type(value.get(key)) not in (int,float) or not math.isfinite(value[key]) or value[key]<0:raise ValueError('Invalid '+key)
    if value['duration_seconds']<1:raise ValueError('Empty scenario')
    previous=-1
    for event in value['events']:
        at=event['at'];method=event['method'];args=event.get('args',[])
        if type(at) not in (int,float) or not math.isfinite(at) or not previous<=at<=value['duration_seconds']:raise ValueError('Unordered/out-of-range event')
        previous=at
        if method not in ('submit','event','toggle_pause','cancel'):raise ValueError('Non-fixture operation forbidden')
        if not isinstance(args,list):raise ValueError('Event args must be a list')
        if method=='submit' and (not 1<=len(args)<=3 or not isinstance(args[0],str) or len(args[0])>8000 or
            (len(args)>1 and args[1] not in ('neutral','friendly','happy','excited','sad','low')) or
            (len(args)>2 and args[2]!='')):raise ValueError('Invalid public PCM submit')
        if method=='event' and (len(args)!=1 or args[0] not in ('person_enter','wake','listen','vad_end','cancel','reset')):raise ValueError('Invalid isolated event')
        if method in ('toggle_pause','cancel') and args:raise ValueError('Unexpected event arguments')
    return value

def preflight(runtime,board_manifest,fresh_baseline,server_proof):
    runtime=Path(runtime).resolve(strict=True);aura=runtime/'aura'
    manifest=json.loads(Path(board_manifest).read_text(encoding='utf8'))
    baseline=json.loads(Path(fresh_baseline).read_text(encoding='utf8'))
    if runtime!=Path(manifest['runtime']).resolve(strict=True) or str(runtime)!=baseline['runtime']:
        raise ValueError('Not the pinned fresh r3 runtime')
    config_path=aura/'config/board_avatar_gtk.json'
    if sha(config_path)!=baseline['render_config_sha256']:raise ValueError('Old renderer config changed')
    config=json.loads(config_path.read_text(encoding='utf8'))
    if not config.get('native_avatar') or config.get('native_pixel_threads')!=3 or config.get('stable_avatar_fps')!=16:
        raise ValueError('Old native/threads/fps config differs')
    remote=config['portrait_offload']
    if not remote.get('enabled') or remote.get('fps')!=16:raise ValueError('Actual old remote16 mode required')
    proof=json.loads(Path(server_proof).read_text(encoding='utf8'))
    if proof.get('schema')!='aura.paired_ab.isolated_old_server.v1' or proof.get('status')!='READY_INDEPENDENT_PROCESS':raise ValueError('Independent old server is not ready')
    if proof['listen']!='192.168.50.1' or proof.get('allowed_peer')!='192.168.50.2':raise ValueError('Wrong isolated peer/interface')
    if proof['size']!=[423,438] or proof['revision']!=remote['revision']:raise ValueError('Old server revision/viewport differs')
    port=proof['isolated_port'];production_port=int(remote.get('port',8796))
    if type(port)is not int or not 1024<=port<=65535 or port in (8796,production_port):raise ValueError('Production portrait endpoint forbidden')
    if proof['production_port']!=production_port:raise ValueError('Production port metadata differs')
    hashes={}
    keys=set(baseline['source_hashes'])|{
        'tools/realtime_controller.py','board/runtime/portrait_offload.py','common/portrait_wire.py',
        'board/runtime/fsm.py','tools/demo_stage.py','tools/gstreamer_audio_engine.py'}
    for key in sorted(keys):
        expected=baseline['source_hashes'].get(key) or manifest['component_pins'][key]
        actual=sha(aura/key)
        if actual!=expected:raise ValueError('Fresh source changed: '+key)
        hashes[key]=actual
    library=aura/'tools/libaura_pixels.so'
    if sha(library)!=baseline['native_pixels_library']['sha256']:raise ValueError('Old native pixel/video library changed')
    hashes['tools/libaura_pixels.so']=sha(library)
    for key in ('tools/portrait_host.py','tools/portrait_renderer.py','common/portrait_wire.py'):
        if proof['source_hashes'][key]!=manifest['component_pins'][key]:raise ValueError('Independent server source differs')
    test_remote=dict(remote,port=port) # in-memory copy only; never writes selected/config.
    return dict(runtime=runtime,aura=aura,config=config,remote=test_remote,proof=proof,hashes=hashes,
        production_port=production_port,isolated_port=port,config_sha256=sha(config_path))

class PreparedPcmJobs:
    """Completed public fixture job, with the real controller's result contract."""
    def __init__(self,root,pcm_path,envelope_path):
        self.root=Path(root);self.jobs={};self.sequence=0
        source=Path(pcm_path).resolve(strict=True)
        with wave.open(str(source),'rb') as stream:
            if (stream.getframerate(),stream.getnchannels(),stream.getsampwidth())!=(24000,1,2):raise ValueError('Public PCM must be24k mono PCM16')
            self.duration=stream.getnframes()/24000
        self.envelope=json.loads(Path(envelope_path).read_text(encoding='utf8'))
        hop=self.envelope['hop_seconds']
        if type(hop) not in (float,int) or not math.isfinite(hop) or hop<=0:raise ValueError('Invalid public envelope')
        for key in ('gains','levels'):
            samples=self.envelope[key]
            if not isinstance(samples,list) or len(samples)*hop<self.duration or any(type(x) not in (float,int) or not math.isfinite(x) or not 0<=x<=1 for x in samples):
                raise ValueError('Invalid public '+key)
        (self.root/'cache').mkdir(parents=True,exist_ok=True)
        self.path=self.root/'cache/public_pcm.wav';shutil.copyfile(source,self.path)
        self.digest=sha(self.path);self.envelope_sha256=sha(envelope_path)
    def submit(self,text,emotion):
        self.sequence+=1;key='public-'+str(self.sequence)
        job=dict(id=key,status='COMPLETE',text=text,emotion=emotion,result=dict(key='public_pcm',path=str(self.path),
            sha256=self.digest,cache_hit=True,duration_seconds=self.duration,envelope=self.envelope))
        self.jobs[key]=job;return job
    def get(self,key):return self.jobs[key]
    def cancel(self,key):self.jobs[key]=dict(self.jobs[key],status='CANCELLED')

class FakesinkOutput:
    """Real GstAudioEngine sink clock with no ALSA element or physical device.

    All engine calls are owned by the actual AvatarRenderWorker. GTK may read
    only cached_snapshot(); it never polls the audio engine concurrently.
    """
    def __init__(self,gst,engine_type,output_caps,startup_silence=1.):
        self.gst=gst;self.lock=threading.Lock();self.last={};self.caps=[];self.bytes=0
        self.active=self.paused=False;self.duration=0.;self.last_time=0.;self.token=0;self.finished_count=0
        def build(gst,path,device):
            if device!='PAIRED_PUBLIC_PCM_NO_DEVICE':raise ValueError('Physical audio forbidden')
            pipeline=gst.Pipeline.new('paired-public-pcm')
            elements=[]
            try:
                for name in ('filesrc','wavparse','audioconvert','audioresample','capsfilter','fakesink'):
                    item=gst.ElementFactory.make(name,name)
                    if item is None:raise RuntimeError('Missing fixture Gst element: '+name)
                    pipeline.add(item);elements.append(item)
                elements[0].set_property('location',str(path));elements[4].set_property('caps',gst.Caps.from_string(output_caps))
                elements[5].set_property('sync',True)
                for a,b in zip(elements,elements[1:]):
                    if not a.link(b):raise RuntimeError('Cannot link public PCM fakesink')
                def seen(pad,info):
                    item=pad.get_current_caps().get_structure(0)
                    caps={key:item.get_value(key) for key in ('format','rate','channels')}
                    with self.lock:
                        if caps not in self.caps:self.caps.append(caps)
                        self.bytes+=info.get_buffer().get_size()
                    return gst.PadProbeReturn.OK
                elements[4].get_static_pad('src').add_probe(gst.PadProbeType.BUFFER,seen)
                return pipeline,elements[5]
            except Exception:pipeline.set_state(gst.State.NULL);raise
        self.engine=engine_type(gst,'PAIRED_PUBLIC_PCM_NO_DEVICE',pipeline_factory=build,startup_silence_seconds=startup_silence)
    def read(self):
        value=dict(self.engine.poll(),track='answer' if self.active else 'none',
                   clock_source='GStreamer synchronous fakesink position query; no physical device')
        if value.get('error'):raise RuntimeError(value['error'])
        with self.lock:self.last=value
        return dict(value)
    def cached_snapshot(self):
        with self.lock:return dict(self.last,caps=list(self.caps),converted_bytes=self.bytes)
    @property
    def ready(self):return bool(self.read().get('ready'))
    @property
    def started_at(self):return self.read().get('started_at')
    def play(self,path,sha256=None):
        with wave.open(str(path),'rb') as stream:self.duration=stream.getnframes()/24000
        self.stop();self.token+=1;self.last_time=0.;self.active=True;self.paused=False
        if not self.engine.command(dict(type='play',token=self.token,path=str(path),sha256=sha256)):raise RuntimeError('Public PCM play rejected')
    def position(self):
        state=self.read()
        if self.active and not self.paused:self.last_time=min(self.duration,max(self.last_time,state['clock']))
        return self.last_time
    def pause(self,value):
        if not self.active:return
        self.position();self.paused=bool(value)
        if not self.engine.command(dict(type='pause',token=self.token,paused=self.paused)):raise RuntimeError('Public PCM pause rejected')
    def stop(self):
        self.position();self.token+=1;self.active=self.paused=False
        self.engine.command(dict(type='stop',token=self.token))
    def finished(self):
        if not self.active:return False
        state=self.read()
        if state.get('done'):self.last_time=self.duration;self.active=False;self.finished_count+=1;return True
        return False
    def close(self):self.engine.release()

def create_controller(plan,output,jobs,*,legacy_native_pixels=True):
    """Actual fresh core, native pixel setup and RealtimeController; no UI/jobs service."""
    aura=plan['aura'];sys.path.insert(0,str(aura))
    factory=importlib.import_module('tools.demo_script')
    controller_module=importlib.import_module('tools.realtime_controller')
    fsm=importlib.import_module('board.runtime.fsm')
    from board.interaction import avatar_board
    old_path=list(sys.path)
    try:core=factory.create_demo_core('reuse')
    finally:sys.path[:]=old_path
    # No device/social publication from this isolated experiment. The same rule
    # is used by the pinned Windows PortraitRenderer and must also be used in B.
    core.fsm=fsm.RuntimeFSM(publish_state_changes=False)
    tokens=avatar_board.load_tokens();background=tokens['colors']['panel_bg']
    pixels=None
    if legacy_native_pixels:
        pixels_module=importlib.import_module('tools.native_pixels')
        pixels=pixels_module.NativePixels(aura/'tools/libaura_pixels.so',background,(423,438),threads=3)
        pixels.configure(core)
    else:
        # Exactly the new UI's default-core/fallback setup; B's character
        # renderer is separate and must not inherit old NativePixels hooks.
        from tools.board_avatar_affine import configure_board_rendering
        configure_board_rendering(core,background)
    core.MAX_CACHED_SEQUENCES=plan['config']['cache_sequences']
    if legacy_native_pixels:
        for state in ('IDLE','PRESENT','LISTENING','THINKING','ACK_NOD','DENY_SHAKE','AWAKE','PUZZLED'):
            core.sequence(state);core.sop(state)
    controller=controller_module.RealtimeController(core,jobs,output)
    return controller,pixels,background

def candidate_sources(aura=None,manifest_path=None,yuki_root_path=None):
    """Validate the exact candidate Python overlay without importing/GL work."""
    paired=Path(__file__).resolve().parent
    aura=Path(aura or paired.parent/'ui_candidate/aura').resolve(strict=True)
    manifest_path=Path(manifest_path or paired.parent/'ui_candidate/manifest.json')
    manifest=json.loads(Path(manifest_path).read_text(encoding='utf8'))
    hashes={};root=aura;config=dict(manifest['native_config_example'],enabled=True,fps=16,seed=1)
    if yuki_root_path is not None:
        proof=json.loads(Path(yuki_root_path).read_text(encoding='utf8'))
        root=Path(proof['root']).resolve(strict=True);config=dict(proof['config'])
        if config.get('enabled')is not True or config.get('fps')!=16 or config.get('seed')!=1:
            raise ValueError('Yuki root must explicitly select enabled16fps/seed1')
        if not isinstance(proof.get('files'),dict) or not proof['files']:raise ValueError('Empty Yuki root file manifest')
        for relative,expected in proof['files'].items():
            path=(root/relative).resolve(strict=True)
            if not path.is_relative_to(root) or not path.is_file():raise ValueError('Yuki root file escapes isolated root')
            actual=sha(path)
            if actual!=expected:raise ValueError('Yuki root file changed: '+relative)
            hashes[relative]=actual
        for relative in ('tools/native_yuki.py','tools/egl_window.py',config['library'],config['model'],config['resx']):
            if relative not in proof['files']:raise ValueError('Missing pinned Yuki root file: '+relative)
        hashes['@yuki-root.json']=sha(yuki_root_path)
    paths={}
    for key in ('tools/board_avatar_worker.py','tools/native_yuki.py','tools/egl_window.py'):
        owner=aura if key.endswith('board_avatar_worker.py') else root
        path=(owner/key).resolve(strict=True)
        if not path.is_relative_to(owner):raise ValueError('Candidate Python source escapes isolated aura')
        hashes[key]=sha(path)
        if hashes[key]!=manifest['files'][key]:raise ValueError('Candidate source changed: '+key)
        paths[Path(key).stem]=path
    hashes['@candidate-manifest.json']=sha(manifest_path)
    return root,hashes,config,paths

def load_candidate_tools(paths):
    """Overlay only these process-local modules; source/runtime files stay read-only."""
    package=importlib.import_module('tools')
    result={}
    for key in ('egl_window','native_yuki','board_avatar_worker'):
        name='tools.'+key;path=paths[key]
        spec=importlib.util.spec_from_file_location(name,path)
        module=importlib.util.module_from_spec(spec);sys.modules[name]=module
        spec.loader.exec_module(module);setattr(package,key,module);result[key]=module
    return result

def swap_tail_stats(times,stats,now):
    """Same239-interval quantile formula as pinned NativeVideo; diagnostic only."""
    values=tuple(times)
    out=dict(pushed=float(stats.get('frames',0)),received=float(stats.get('frames',0)),
             sequence=float(stats.get('frames',0)),fps=0.,p50_ms=0.,p95_ms=0.,p99_ms=0.,max_ms=0.,
             age_ms=(now-values[-1])*1000 if values else 0.,ring_samples=len(values))
    if len(values)>1:
        intervals=sorted((b-a)*1000 for a,b in zip(values,values[1:]))
        n=len(intervals)
        out.update(fps=(len(values)-1)/(values[-1]-values[0]),p50_ms=intervals[n//2],
                   p95_ms=intervals[min(n-1,int(n*.95))],p99_ms=intervals[min(n-1,int(n*.99))],max_ms=intervals[-1])
    return out
