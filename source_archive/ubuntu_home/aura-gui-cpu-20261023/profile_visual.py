"""Fixed avatar times; no GTK/audio/camera/model runtimes or production writes."""
import cProfile
import hashlib
import io
import json
import os
from pathlib import Path
import pstats
import resource
import statistics
import sys
import time

ROOT=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136/gui-runtime')
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'aura'))
from tools.demo_script import create_demo_core
search=list(sys.path)
core=create_demo_core('reuse');sys.path[:]=search
from tools.native_pixels import NativePixels
from tools.realtime_facials import RealtimeFacials

pixels=NativePixels(ROOT/'aura/tools/libaura_pixels.so',threads=3)
pixels.configure(core);facials=RealtimeFacials(core)
report={'scope':'ISOLATED_FIXED_TIME_PIXEL_PROFILE_NOT_PRODUCTION_THREAD_CPU',
        'runtime':str(ROOT),'native_threads':3,'no_audio_camera_model_work':True,'states':[]}
try:
    for state in ('IDLE','SPEAKING_NEUTRAL'):
        core.reset_playback();facials.body.reset()
        for index in range(4):
            t=index*.125+.011;meta=core.display_frame(state,t)
            facials.apply(meta,t,.8 if state.startswith('SPEAKING') else 0.,.7)
        wall=[];cpu=[];stages={'core_frame':[],'facials':[]}
        profile=cProfile.Profile();profile.enable()
        for index in range(24):
            t=(index+4)*.125+.011;began=time.monotonic();used=time.process_time()
            meta=core.display_frame(state,t);mid=time.monotonic()
            image=facials.apply(meta,t,.8 if state.startswith('SPEAKING') else 0.,.7)['image']
            end=time.monotonic()
            wall.append((end-began)*1000);cpu.append((time.process_time()-used)*1000)
            stages['core_frame'].append((mid-began)*1000);stages['facials'].append((end-mid)*1000)
        profile.disable();stream=io.StringIO();pstats.Stats(profile,stream=stream).sort_stats('cumtime').print_stats(20)
        report['states'].append({'state':state,'frames':24,'wall_p50_ms':statistics.median(wall),
            'cpu_p50_ms':statistics.median(cpu),'wall_max_ms':max(wall),
            'stage_p50_ms':{k:statistics.median(v) for k,v in stages.items()},
            'native_last_cpu_stage':pixels.cpu_times(),'profile':stream.getvalue(),
            'last_image_sha256':hashlib.sha256(image.tobytes()).hexdigest()})
    report['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
finally:
    pixels.close()
print(json.dumps(report))
