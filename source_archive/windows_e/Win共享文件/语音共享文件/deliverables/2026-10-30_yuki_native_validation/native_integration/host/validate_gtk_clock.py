"""GTK/EGL + real GStreamer sink clock, synthetic PCM and fakesink only.

Exercises the running board's RealtimeController.portrait_frame entry through
the new LocalPortrait mailbox. Never loads its app, databases or network jobs.
"""
from pathlib import Path
from types import SimpleNamespace as S
import array,ctypes as C,hashlib,json,math,os,subprocess,sys,time,wave

PHASE=Path('/home/root/aura-yuki-validation-20261030/native_integration');BASE=PHASE.parent
pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
before={'pid':pid,'cmdline':Path('/proc',pid,'cmdline').read_bytes().replace(b'\0',b' ').decode()}
for value in Path('/proc',pid,'environ').read_bytes().split(b'\0'):
    key,sep,data=value.partition(b'=')
    if sep and key in (b'DISPLAY',b'XAUTHORITY'):os.environ[key.decode()]=os.fsdecode(data)
manifest=json.loads((PHASE/'board_source/manifest.json').read_text())
runtime=Path(manifest['runtime']);sys.path.insert(0,str(runtime/'aura'));sys.path.insert(0,str(PHASE/'host'))
from native_yuki import LocalPortrait,Control,create_gl_area
from tools.gstreamer_audio_engine import GstAudioEngine,build_pipeline
from tools.gstreamer_audio_worker import load_gst
from tools.realtime_controller import RealtimeController
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk,GLib

OUTPUT=PHASE/'results';OUTPUT.mkdir(exist_ok=True)
duration=float(sys.argv[1]) if len(sys.argv)>1 else 90
samples=array.array('h',(int(10000*(.5+.5*math.sin(i/24000*math.tau*2))*math.sin(i/24000*math.tau*220)) for i in range(24000*12)))
pcm=samples.tobytes();wav=OUTPUT/'public_synthetic_clock.wav'
with wave.open(str(wav),'wb') as stream:
    stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(24000);stream.writeframes(pcm)
digest=hashlib.sha256(wav.read_bytes()).hexdigest();gst,_=load_gst();observed={'caps':[],'bytes':0}
def no_device(gst,path,device):
    assert device=='NO_DEVICE_NATIVE_YUKI_TEST'
    pipeline,unopened=build_pipeline(gst,path,device);caps=pipeline.get_by_name('capsfilter')
    caps.unlink(unopened);pipeline.remove(unopened)
    sink=gst.ElementFactory.make('fakesink','no-audio-device');assert sink;sink.set_property('sync',True)
    pipeline.add(sink);assert caps.link(sink)
    def probe(pad,info):
        structure=pad.get_current_caps().get_structure(0)
        record={key:structure.get_value(key) for key in ('format','rate','channels')}
        if record not in observed['caps']:observed['caps'].append(record)
        observed['bytes']+=info.get_buffer().get_size();return gst.PadProbeReturn.OK
    caps.get_static_pad('src').add_probe(gst.PadProbeType.BUFFER,probe)
    return pipeline,sink
engine=GstAudioEngine(gst,'NO_DEVICE_NATIVE_YUKI_TEST',pipeline_factory=no_device)
class Output:
    def __init__(self):self.active=False;self.paused=False;self.ready=False;self.snapshot={}
    def read(self):
        self.snapshot=engine.poll();self.ready=self.snapshot.get('ready',False)
        if self.snapshot.get('done'):self.active=False
        if self.snapshot.get('error'):raise RuntimeError(self.snapshot['error'])
        return dict(self.snapshot,track='answer' if self.active else 'none')
    def position(self):return self.read().get('clock',0.)
output=Output();core=S(talk_gen=1,emotion='neutral',fsm=S(state=S(label='IDLE')))
mailbox=LocalPortrait(output)
visual=RealtimeController.__new__(RealtimeController);visual.core=core;visual.output=output;visual.portrait_offload=mailbox;visual.last_meta=None
assets=PHASE/'runtime_assets'
profile=json.loads((assets/'source_profile.json').read_text())
assert hashlib.sha256((assets/'model.runtime.json').read_bytes()).hexdigest()==profile['files']['model.runtime.json']
config=dict(library=str(PHASE/'build_host/libaura_yuki.so'),model=str(assets/'model.runtime.json'),
  resx=str(assets/'yuk_0.ems.resx.json'),resource_root=str(assets),seed=1)
assert Gtk.init_check([])[0]
window=Gtk.Window();window.set_decorated(False);window.set_skip_taskbar_hint(True);window.set_skip_pager_hint(True);window.set_accept_focus(False)
window.set_default_size(423,438);window.set_opacity(0);window.move(-9000,-9000)
errors=[];area=create_gl_area(config,mailbox,on_error=errors.append);area.set_size_request(423,438);window.add(area)
state={'began':None,'paused':False,'resumed':False,'cancelled':False,'restarted':False,'first_rss_kib':None}
records=[];checks={};last_frame=0;setup=time.monotonic();last_sample_by_owner={};pause_positions=[];control_delays=[]
def rss():
    return int(next(x.split()[1] for x in Path('/proc/self/status').read_text().splitlines() if x.startswith('VmRSS:')))
def play(token):
    assert engine.command(dict(type='play',token=token,path=str(wav),sha256=digest));output.active=True;output.paused=False
    core.fsm.state.label='SPEAKING'
def observe_frame(stats):
    if state['began'] is None:return
    elapsed=stats['paint_at']-state['began'];owner=stats['owner'];sample=stats['audio_sample']
    previous=last_sample_by_owner.get(owner)
    if previous is not None and sample<previous:raise RuntimeError('Displayed audio sample rewound within owner')
    last_sample_by_owner[owner]=sample
    records.append(dict(at=elapsed,phase=core.fsm.state.label,output_clock=output.snapshot.get('clock',0.),paused=output.paused,**stats))
    if state.get('cancel_at') and elapsed<10 and stats['mouth']==0 and 'cancel_close_ms' not in checks:
        checks['cancel_close_ms']=(elapsed-state['cancel_at'])*1000
area.frame_observer=observe_frame
def poll():
    global last_frame
    try:
        if errors:raise RuntimeError(errors[-1])
        now=time.monotonic()
        if not mailbox.ready:
            if now-setup>20:raise RuntimeError('GTK native context startup timed out')
            return True
        if state['began'] is None:state['began']=now;play(1)
        elapsed=now-state['began'];snapshot=output.read();position=output.position()
        if elapsed>=4 and not state['paused']:
            engine.command(dict(type='pause',token=1,paused=True));output.paused=True;state['paused']=True
        if output.paused and not state['resumed']:pause_positions.append(position)
        if elapsed>=5 and not state['resumed']:
            engine.command(dict(type='pause',token=1,paused=False));output.paused=False;state['resumed']=True
        if elapsed>=8 and not state['cancelled']:
            old=engine.pipeline;engine.command(dict(type='stop',token=2));output.active=False;output.ready=False
            mailbox.invalidate();core.talk_gen+=1;core.fsm.state.label='IDLE';state['cancelled']=True;state['cancel_at']=elapsed
            checks['cancel_releases_pipeline']=engine.pipeline is None and old.get_state(gst.SECOND)[1]==gst.State.NULL
            checks['old_audio_token_rejected']=not engine.command(dict(type='play',token=1,path=str(wav),sha256=digest))
        if elapsed>=10 and not state['restarted']:
            core.talk_gen+=1;play(3);state['restarted']=True;position=output.position()
        if not output.active:core.fsm.state.label='IDLE'
        face=min(5,int(elapsed//5));mailbox.set_expression(tuple(mailbox.FACE)[face] if elapsed<30 else None)
        mailbox.set_pose(1 if 32<=elapsed<45 else 0)
        # Level is derived from PCM at the ACTUAL sink sample position.
        index=max(0,min(len(samples)-1,int(position*24000)));start=max(0,index-240)
        level=min(1,math.sqrt(sum(v*v for v in samples[start:index+1])/max(1,index+1-start))/7000)
        RealtimeController.portrait_frame(visual,elapsed,1. if output.active else 0.,level)
        if elapsed>=6 and state['first_rss_kib'] is None:state['first_rss_kib']=rss()
        if elapsed>=duration:Gtk.main_quit();return False
        return True
    except Exception as error:errors.append(str(error));Gtk.main_quit();return False
window.show_all();GLib.timeout_add(10,poll)
try:Gtk.main()
finally:
    if area.native and not errors:
        area.egl.current();area.native.render(time.monotonic(),423,438);area.native.capture(OUTPUT/'gtk-final.png',423,438);area.egl.swap()
    window.destroy();engine.release()
after_pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
intervals=[(b.get('paint_at',b['at'])-a.get('paint_at',a['at']))*1000 for a,b in zip(records,records[1:])]
def p(q):
    v=sorted(intervals);return v[min(len(v)-1,int((len(v)-1)*q))] if v else 0
checks['pause_clock_span_ms']=(max(pause_positions)-min(pause_positions))*1000 if pause_positions else None
checks['production_ui_pid_unchanged']=before['pid']==after_pid
checks['converted_caps_correct']=observed['caps']==[dict(format='S16LE',rate=48000,channels=2)]
checks['all_six_faces_requested']=set(r.get('model_expression') for r in records)==set(range(6))
checks['both_pose_controls_requested']=set(r.get('model_pose') for r in records)=={0,1}
eyes=[r['eye'] for r in records];memory_delta=rss()-(state['first_rss_kib'] or rss())
passing=not errors and len(records)>duration*16 and p(.99)<62.5 and checks['production_ui_pid_unchanged'] and checks.get('cancel_releases_pipeline') and checks.get('old_audio_token_rejected') and checks.get('cancel_close_ms',1000)<100 and checks['pause_clock_span_ms'] is not None and checks['pause_clock_span_ms']<30 and checks['converted_caps_correct'] and checks['all_six_faces_requested'] and checks['both_pose_controls_requested']
def metrics(key):
    v=sorted(float(r[key]) for r in records if key in r)
    return {name:v[min(len(v)-1,int((len(v)-1)*q))] for name,q in [('p50',.5),('p95',.95),('p99',.99),('max',1)]} if v else {}
report=dict(status='PASS' if passing else 'FAIL',duration=records[-1]['at'] if records else 0,frames=len(records),
 actual_fps=(len(records)-1)/(records[-1]['at']-records[0]['at']) if len(records)>1 else 0,
 interval_ms=dict(p50=p(.5),p95=p(.95),p99=p(.99),max=p(1)),checks=checks,errors=errors,
 eye_range=[min(eyes),max(eyes)] if eyes else None,rss_delta_kib=memory_delta,device_opened=False,
 evaluate_ms=metrics('evaluate_ms'),submit_ms=metrics('submit_ms'),egl_swap_ms=metrics('egl_swap_ms'),gtk_callback_ms=metrics('gtk_callback_ms'),
 egl_bind_ms=metrics('egl_bind_ms'),native_call_ms=metrics('native_call_ms'),
 steady_pixel_readback=False,host='GTK DrawingArea with native EGL child using system display visual',
 window_visual=records[-1].get('window_visual') if records else None,
 window_rgba_bits=records[-1].get('window_rgba_bits') if records else None,
 source_clock='real GstAudioEngine synced fakesink position; no simulated or host clock used for mouth',
 controller_entry='current board RealtimeController.portrait_frame',window='mapped transparent non-focusing test window',
 source_profile=profile['profile_id'],production_deployed=False,physical_audio_or_touchscreen_acceptance=False)
report['frame_measurement']='every native swap submission callback, no latest-state polling loss; physical scanout not measured'
(OUTPUT/'gtk-clock.json').write_text(json.dumps(report,indent=2));(OUTPUT/'gtk-clock-samples.json').write_text(json.dumps(records))
print(json.dumps(report),flush=True)
if not passing:raise SystemExit(1)
