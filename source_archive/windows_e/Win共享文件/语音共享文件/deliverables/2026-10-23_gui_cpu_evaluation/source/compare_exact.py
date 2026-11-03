"""One asset initialization, exact native check, paired visuals, ABBA CPU."""
import base64, ctypes as C, hashlib, json, math, random, resource, statistics, sys, time, types
from pathlib import Path

ROOT=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136/gui-runtime')
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'aura'))
def progress(phase,**fields):
    with (PROFILE_OUTPUT/'progress.jsonl').open('a') as stream:
        stream.write(json.dumps({'phase':phase,'mono':time.monotonic(),**fields})+'\n')

for name,sha in BASELINE_PINS.items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
import numpy as np
from PIL import Image
from tools.native_pixels import NativePixels
from tools.realtime_facials import RealtimeFacials

def load(name,relative):
    module=types.ModuleType(name);module.__file__=str(ROOT/'aura'/relative)
    exec(compile(base64.b64decode(CANDIDATE[relative]),'candidate/'+relative,'exec'),module.__dict__)
    return module
new_pixels=load('exact_pixels','tools/native_pixels.py')
body=load('exact_body','tools/idle_body_compositor.py')
new=load('exact_facials','tools/realtime_facials.py');new.IdleBodyTrack=body.IdleBodyTrack

def native_check():
    # All 65,536 pairs, in every RGB lane; nonconstant alpha plus odd tails.
    old=NativePixels(ROOT/'aura/tools/libaura_pixels.so',threads=3)
    new=new_pixels.NativePixels(PROFILE_OUTPUT/'libaura_pixels.so',threads=3)
    original_a=old.lib.aura_pose_blend;original_b=new.lib.aura_pose_blend
    ptr=C.c_void_p;matrix=(C.c_double*6)(1,0,0,0,1,0)
    checked=0
    try:
        for width,height,transparent in ((256,256,False),(13,7,True)):
            y,x=np.mgrid[:height,:width]
            a=np.stack((x%256,y%256,(x+y)%256,((x*13+y*7)%256 if transparent else np.full_like(x,255))),axis=-1).astype('uint8')
            b=np.stack((y%256,x%256,(x*7+y*2)%256,((x*3+y*11)%256 if transparent else np.full_like(x,255))),axis=-1).astype('uint8')
            first=a.tobytes();second=b.tobytes();mixed=C.create_string_buffer(len(first))
            expected=C.create_string_buffer(width*height*3);actual=C.create_string_buffer(width*height*3)
            legacy=C.create_string_buffer(width*height*3)
            for alpha in (0.,.01,.1,.2,.3,.5,.6,.7,.9,.99,1.):
                assert old.lib.aura_blend(first,second,mixed,len(first),alpha)==0
                args=(width,height,matrix,width,height,255,255,255)
                assert old.lib.aura_pose(old.owner,mixed,*args,expected)==0
                assert new.lib.aura_pose_blend_exact(new.owner,first,second,alpha,*args,actual)==0
                diff=np.abs(np.frombuffer(expected.raw,dtype='uint8').astype('int16')-np.frombuffer(actual.raw,dtype='uint8'))
                if diff.any():
                    raise AssertionError(('native_exact_mismatch',width,height,alpha,int(diff.max()),int(np.count_nonzero(diff))))
                # Legacy entry points of the rebuilt library keep their pixels.
                assert original_a(old.owner,first,second,alpha,*args,expected)==0
                assert original_b(new.owner,first,second,alpha,*args,legacy)==0
                assert expected.raw==legacy.raw,('legacy_changed',width,height,alpha)
                checked+=width*height*3
        return {'cases':22,'exact_rgb_channel_comparisons':checked,'maximum_difference':0,'legacy_changed':False}
    finally:
        old.close();new.close()

progress('native_check_start')
result={'scope':'HEADLESS_SAME_INPUT_NOT_WHOLE_BOARD_GAIN','native_check':native_check(),
        'baseline_pins':BASELINE_PINS,'candidate_pins':CANDIDATE_PINS,
        'gates':{'pixel_max':2,'pixel_p99':1,'pixel_mean':.1,'idle_cpu_reduction':.10},
        'native_threads':3,'quality':[],'rounds':[]}
progress('native_check_done',**result['native_check'])
from tools.demo_script import create_demo_core
search=list(sys.path);core=create_demo_core('reuse');sys.path[:]=search
progress('core_ready')
old_pixels=NativePixels(ROOT/'aura/tools/libaura_pixels.so',threads=3)
exact_pixels=new_pixels.NativePixels(PROFILE_OUTPUT/'libaura_pixels.so',threads=3)
pixels={'baseline':old_pixels,'candidate':exact_pixels}
old_pixels.configure(core);baseline=RealtimeFacials(core)
exact_pixels.configure(core)
candidate=new.RealtimeFacials.__new__(new.RealtimeFacials)
candidate.__dict__.update(baseline.__dict__);candidate.body=body.IdleBodyTrack(core)
facials={'baseline':baseline,'candidate':candidate}
progress('facials_ready')

def reset(name,gain=1.):
    pixels[name].configure(core);core.idle_gain=gain
    core.reset_playback();core.rng=random.Random(20261023)
    f=facials[name];f.body.reset();f.body.player.rng=random.Random(20261023)
    f.envelope=f.closing=f.last_asset=None;f.last_gain=f.last_level=0.

def frame(name,state,t,gain):
    meta=core.display_frame(state,t)
    return facials[name].apply(meta,t,gain,.7)

def record(meta):
    keys=('asset','index','source_position','display_state','transitioning','blink_active','blink_phase',
          'body_asset','body_index','body_source_position','body_face_matrix')
    return {key:meta.get(key) for key in keys}

def compare_case(label,schedule,idle_gain=1.):
    images=[];metadata=[];reset('baseline',idle_gain)
    for state,t,gain in schedule:
        meta=frame('baseline',state,t,gain);images.append(np.asarray(meta['image']).copy());metadata.append(record(meta))
    reset('candidate',idle_gain);maximum=p99=mean=0.;different=blinks=0
    for i,(state,t,gain) in enumerate(schedule):
        meta=frame('candidate',state,t,gain);assert record(meta)==metadata[i],(label,i,'metadata')
        actual=np.asarray(meta['image']);assert actual.shape==images[i].shape
        error=np.abs(images[i].astype('int16')-actual.astype('int16'))
        histogram=np.bincount(error.ravel(),minlength=256);cum=histogram.cumsum();rank=.99*(error.size-1)
        lo=int(math.floor(rank));hi=int(math.ceil(rank))
        low=int(np.searchsorted(cum,lo,side='right'));high=int(np.searchsorted(cum,hi,side='right'))
        maximum=max(maximum,int(np.flatnonzero(histogram)[-1]));p99=max(p99,low+(high-low)*(rank-lo))
        mean=max(mean,float(np.dot(histogram,np.arange(256))/error.size));different+=int(histogram[0]!=error.size)
        blinks+=int(meta['blink_active'])
    row={'case':label,'frames':len(schedule),'maximum_difference':maximum,'worst_frame_p99':p99,
         'worst_frame_mean':mean,'different_frames':different,'blink_frames':blinks,'metadata_equal':True}
    result['quality'].append(row);progress('quality_done',**row)

try:
    for state,count in (('IDLE',32),('SPEAKING_NEUTRAL',16),('LISTENING',8),('ACK_NOD',8)):
        compare_case(state,[(state,i*.125+.011,.8 if state.startswith('SPEAKING') else 0.) for i in range(count)])
    compare_case('IDLE_EFFECTS_OFF',[('IDLE',i*.125+.011,0.) for i in range(8)],0.)
    compare_case('SPEAKING_EXIT_TO_IDLE',
                 [('SPEAKING_NEUTRAL',i*.125+.011,.8) for i in range(12)]+
                 [('IDLE',i*.125+.011,0.) for i in range(12,28)])
    compare_case('SPEAKING_POOL_ROTATION',
                 [('SPEAKING_NEUTRAL',i*.125+.011,.8) for i in range(64)])
    for round_no,name in enumerate(('baseline','candidate','candidate','baseline')):
        reset(name)
        for i in range(4):frame(name,'IDLE',i*.125+.011,0.)
        cpu=[];wall=[]
        for i in range(32):
            start=time.monotonic();used=time.process_time()
            last=frame(name,'IDLE',(i+4)*.125+.011,0.)
            cpu.append((time.process_time()-used)*1000);wall.append((time.monotonic()-start)*1000)
        row={'round':round_no,'variant':name,'frames':32,'cpu_total_ms':sum(cpu),'cpu_p50_ms':statistics.median(cpu),
             'wall_total_ms':sum(wall),'wall_p50_ms':statistics.median(wall),
             'last_sha256':hashlib.sha256(last['image'].tobytes()).hexdigest()}
        result['rounds'].append(row);progress('cpu_round_done',**row)
    sums={name:sum(r['cpu_total_ms'] for r in result['rounds'] if r['variant']==name) for name in pixels}
    result['idle_cpu_reduction_fraction']=1-sums['candidate']/sums['baseline']
    result['quality_passed']=all(q['maximum_difference']<=2 and q['worst_frame_p99']<=1 and q['worst_frame_mean']<=.1 for q in result['quality'])
    result['cpu_gate_passed']=result['idle_cpu_reduction_fraction']>=.10
    result['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result['asset_sharing']='One core and read-only MouthBank/BlinkLayer; playback and transient state reset per variant; independent native buffers and body players.'
finally:
    old_pixels.close();exact_pixels.close()
print(json.dumps(result))
