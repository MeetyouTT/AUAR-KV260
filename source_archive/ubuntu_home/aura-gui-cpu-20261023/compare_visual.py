"""Same assets/seed/times, paired pixels and ABBA process-CPU measurements."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import resource
import statistics
import sys
import time

def progress(phase, **fields):
    row={'phase':phase,'monotonic':time.monotonic(),**fields}
    with (PROFILE_OUTPUT/'progress.jsonl').open('a') as stream:
        stream.write(json.dumps(row)+'\n')

progress('import_start')

ROOT=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136/gui-runtime')
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'aura'))
for name,expected in BASELINE_PINS.items():
    assert hashlib.sha256((ROOT/'aura'/name).read_bytes()).hexdigest()==expected
import numpy as np
from tools.demo_script import create_demo_core
from tools.native_pixels import NativePixels
from tools.realtime_facials import RealtimeFacials
import tools.idle_body_compositor as old_body
progress('import_done')


def load(name,relative):
    import types
    module=types.ModuleType(name)
    module.__file__=str(ROOT/'aura'/relative)
    source=base64.b64decode(CANDIDATE[relative])
    exec(compile(source,'candidate/'+relative,'exec'),module.__dict__)
    return module


body=load('cpu_candidate_body','tools/idle_body_compositor.py')
new=load('cpu_candidate_facials','tools/realtime_facials.py');new.IdleBodyTrack=body.IdleBodyTrack
search=list(sys.path);baseline=create_demo_core('reuse');sys.path[:]=search
progress('baseline_core_ready')
candidate=create_demo_core('reuse');sys.path[:]=search
progress('candidate_core_ready')
cores={'baseline':baseline,'candidate':candidate}
pixels={key:NativePixels(ROOT/'aura/tools/libaura_pixels.so',threads=3) for key in cores}
facials={}
for name,core in cores.items():
    core.rng=random.Random(20261023);pixels[name].configure(core)
    facials[name]=(RealtimeFacials if name=='baseline' else new.RealtimeFacials)(core)
    progress('facials_ready',variant=name)


def reset(name):
    cores[name].reset_playback();cores[name].rng=random.Random(20261023)
    facials[name].body.reset();facials[name].body.player.rng=random.Random(20261023)


def frame(name,state,t):
    core=cores[name];meta=core.display_frame(state,t)
    return facials[name].apply(meta,t,.8 if state.startswith('SPEAKING') else 0.,.7)


result={'scope':'HEADLESS_SAME_INPUT_PIXEL_AND_ABBA_CPU_NOT_WHOLE_BOARD_GAIN',
        'seed':20261023,'native_threads':3,
        'predeclared_gates':{'pixel_max_channel_difference':2,'pixel_p99_difference':1,
            'pixel_mean_difference':.1,'idle_cpu_minimum_reduction_fraction':.10},
        'quality':[],'rounds':[]}
try:
    for state,count in (('IDLE',48),('SPEAKING_NEUTRAL',16),('LISTENING',8),('ACK_NOD',8)):
        progress('quality_start',state=state)
        for name in cores:reset(name)
        maximum=p99=mean=0.;different=blink_frames=0
        for index in range(count):
            t=index*.125+.011
            a=frame('baseline',state,t);b=frame('candidate',state,t)
            assert a['image'].mode==b['image'].mode and a['image'].size==b['image'].size
            for key in ('asset','index','source_position','blink_active','blink_phase'):
                assert a.get(key)==b.get(key),(state,key)
            error=np.abs(np.asarray(a['image'],dtype=np.int16)-np.asarray(b['image'],dtype=np.int16))
            # Exact integer histogram avoids sorting millions of pixel channels.
            histogram=np.bincount(error.ravel(),minlength=256)
            cumulative=histogram.cumsum();rank=.99*(error.size-1)
            lo=int(np.floor(rank));hi=int(np.ceil(rank))
            low=int(np.searchsorted(cumulative,lo,side='right'))
            high=int(np.searchsorted(cumulative,hi,side='right'))
            frame_p99=low+(high-low)*(rank-lo)
            maximum=max(maximum,int(np.flatnonzero(histogram)[-1]));p99=max(p99,frame_p99)
            mean=max(mean,float(np.dot(histogram,np.arange(256))/error.size))
            different+=int(histogram[0]!=error.size);blink_frames+=int(a.get('blink_active',False))
            if index%8==7:progress('quality_progress',state=state,frames=index+1)
        result['quality'].append({'state':state,'frames':count,'max_channel_difference':maximum,
            'worst_frame_p99':p99,'worst_frame_mean':mean,'different_frames':different,'blink_frames':blink_frames})
        progress('quality_done',**result['quality'][-1])
    for round_no,name in enumerate(('baseline','candidate','candidate','baseline')):
        progress('cpu_round_start',round=round_no,variant=name)
        reset(name)
        for index in range(4):frame(name,'IDLE',index*.125+.011)
        walls=[];cpus=[]
        for index in range(48):
            t=(index+4)*.125+.011;before=time.monotonic();cpu=time.process_time()
            image=frame(name,'IDLE',t)['image']
            cpus.append((time.process_time()-cpu)*1000);walls.append((time.monotonic()-before)*1000)
        result['rounds'].append({'round':round_no,'variant':name,'frames':48,
            'cpu_total_ms':sum(cpus),'cpu_p50_ms':statistics.median(cpus),
            'wall_total_ms':sum(walls),'wall_p50_ms':statistics.median(walls),
            'last_sha256':hashlib.sha256(image.tobytes()).hexdigest()})
        progress('cpu_round_done',**result['rounds'][-1])
    sums={name:sum(r['cpu_total_ms'] for r in result['rounds'] if r['variant']==name) for name in cores}
    result['idle_cpu_reduction_fraction']=1-sums['candidate']/sums['baseline']
    result['quality_passed']=all(r['max_channel_difference']<=2 and r['worst_frame_p99']<=1
                                  and r['worst_frame_mean']<=.1 for r in result['quality'])
    result['cpu_gate_passed']=result['idle_cpu_reduction_fraction']>=.10
    result['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
finally:
    for pixel in pixels.values():pixel.close()
print(json.dumps(result))
