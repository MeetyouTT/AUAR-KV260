"""Real ARM/GLES2 diagnostic and continuous-render checks, never live deployment."""
from pathlib import Path
import ctypes as C
import json,math,statistics,sys,time
from PIL import Image,ImageChops

PHASE=Path('/home/root/aura-yuki-validation-20261030/native_integration')
BASE=PHASE.parent
sys.path.insert(0,str(BASE/'probe_build'))
from gles2_capture import EGL
from native_yuki import Native,Control

def percentile(values,q):
    values=sorted(values);return values[min(len(values)-1,int((len(values)-1)*q))] if values else 0

def diagnostics():
    output=PHASE/'results';output.mkdir(exist_ok=True)
    context=EGL()
    try:
        api=C.CDLL(str(PHASE/'build_host/libaura_yuki.so'))
        api.yuki_diagnostic_geometry.argtypes=[C.c_char_p]*4+[C.c_int]*2;api.yuki_diagnostic_geometry.restype=C.c_int
        api.yuki_diagnostic_error.restype=C.c_char_p
        api.yuki_diagnostic_parameters.argtypes=[C.c_char_p]*5+[C.c_int]*2;api.yuki_diagnostic_parameters.restype=C.c_int
        fixtures=[]
        for name in ('motion_self','sprite_self','ordinary_child','other_stencil'):
            root=PHASE/'mask_fixtures'/name;path=output/(name+'-native.png')
            ok=api.yuki_diagnostic_geometry(*(str(x).encode() for x in (root/'model.json',root/'model.resx.json',root,path)),423,438)
            if not ok:raise RuntimeError(api.yuki_diagnostic_error().decode())
            reference=PHASE/'mask_fixtures'/(name.replace('_','-')+'-reference-lossless.png')
            a=Image.open(reference).convert('RGB');b=Image.open(path).convert('RGB')
            delta=ImageChops.difference(a,b);histogram=delta.histogram();pixels=a.width*a.height
            mae=sum((i%256)*n for i,n in enumerate(histogram))/(pixels*3)
            # Large filled interiors distinguish the semantic rules independently of AA edges.
            interior_errors=0;interior_checked=0
            for y in range(3,a.height-3):
                for x in range(3,a.width-3):
                    value=a.getpixel((x,y))
                    if all(a.getpixel((x+dx,y+dy))==value for dx in range(-2,3) for dy in range(-2,3)):
                        interior_checked+=1
                        if max(abs(v-w) for v,w in zip(value,b.getpixel((x,y))))>2:interior_errors+=1
            fixtures.append(dict(name=name,mae=mae,interior_errors=interior_errors,interior_checked=interior_checked,
                pass_=interior_errors==0 and mae<.8))
        (output/'mask-comparison.json').write_text(json.dumps({'fixtures':fixtures,'pass':all(x['pass_'] for x in fixtures),
          'original_engine_reference':True,'same_PSB_JSON_generated_inputs':True},indent=2))
        for expression in ('normal','smile','angry','sad','concern','shy'):
            parameters=PHASE/('controlled-'+expression+'-parameters.json')
            if not parameters.exists():continue
            ok=api.yuki_diagnostic_parameters(*(str(x).encode() for x in (BASE/'inputs/ems/yuk_0.ems.json',
              BASE/'inputs/ems/yuk_0.ems.resx.json',BASE/'inputs/ems',parameters,output/('controlled-'+expression+'-native.png'))),423,438)
            if not ok:raise RuntimeError(api.yuki_diagnostic_error().decode())
        # Reuse the unchanged exported frames: this isolates C++ GLES2 port from new core semantics.
        api.yuki_diagnostic_frames.argtypes=[C.c_char_p]*5+[C.c_int]*2;api.yuki_diagnostic_frames.restype=C.c_int
        for filename,directory in (('candidate-frames.json','cpp-port-baseline'),('static-reference-frames.json','cpp-port-static'),
          ('native_integration/results/native-frames.json','candidate-captures'),('native_integration/results/native-static-frames.json','candidate-static')):
            source=BASE/filename
            if not source.exists():continue
            dest=output/directory
            count=api.yuki_diagnostic_frames(*(str(x).encode() for x in (BASE/'inputs/ems/yuk_0.ems.json',BASE/'inputs/ems/yuk_0.ems.resx.json',BASE/'inputs/ems',source,dest)),423,438)
            if count<=0:raise RuntimeError(api.yuki_diagnostic_error().decode())
        print(json.dumps({'diagnostics':'complete','mask_pass':all(x['pass_'] for x in fixtures)}),flush=True)
    finally:context.close()

def continuous(seconds=90):
    output=PHASE/'results';output.mkdir(exist_ok=True)
    context=EGL();native=None
    try:
        assets=PHASE/'runtime_assets'
        native=Native(PHASE/'build_host/libaura_yuki.so',assets/'model.runtime.json',assets/'yuk_0.ems.resx.json',assets)
        gl=C.CDLL('libGLESv2.so.2');gl.glFinish.argtypes=[]
        started=time.monotonic();deadline=started;records=[];sequence=0;owner=1;last_stage=None;checks={}
        while time.monotonic()-started<seconds:
            now=time.monotonic();elapsed=now-started;stage=int(elapsed//10)
            if stage!=last_stage:owner+=1;last_stage=stage
            sequence+=1;playing=stage%3!=2
            value=Control(owner,sequence,int((elapsed%10)*24000),24000,1,int(playing),0,stage%6,0,1.,.45+.45*math.sin(elapsed*6),now)
            assert native.offer(value)
            if sequence==10:
                checks['duplicate_sequence_rejected']=not native.offer(value)
                old=Control(owner-1,sequence+9999,value.audio_sample,24000,1,1,0,0,0,1.,1.,now)
                checks['old_owner_rejected']=not native.offer(old)
            render_start=time.monotonic();stats=native.render(now,423,438);gl.glFinish();done=time.monotonic()
            records.append(dict(at=done-started,total_ms=(done-render_start)*1000,playing=playing,**stats))
            deadline+=1/24
            if deadline<done:deadline=done
            delay=deadline-time.monotonic()
            if delay>0:time.sleep(delay)
        native.capture(output/'continuous-final.png',423,438)
        intervals=[(b['at']-a['at'])*1000 for a,b in zip(records,records[1:])]
        complete=[r['total_ms'] for r in records];evaluate=[r['evaluate_ms'] for r in records]
        closed=[r['mouth']==0 for r in records if not r['playing']]
        report=dict(status='PASS' if checks and all(checks.values()) and all(closed) and percentile(intervals,.99)<62.5 else 'FAIL',
          scope='native continuous offscreen GLES2, GPU completed; GTK/audio checked separately',duration=records[-1]['at'],frames=len(records),
          actual_fps=(len(records)-1)/(records[-1]['at']-records[0]['at']),
          interval_ms={q:percentile(intervals,p) for q,p in [('p50',.5),('p95',.95),('p99',.99),('max',1)]},
          gpu_complete_frame_ms={q:percentile(complete,p) for q,p in [('p50',.5),('p95',.95),('p99',.99),('max',1)]},
          evaluate_ms={q:percentile(evaluate,p) for q,p in [('p50',.5),('p95',.95),('p99',.99),('max',1)]},
          idle_mouth_closed=all(closed),checks=checks,final=records[-1],pixel_readback_in_timed_loop=False,production_deployed=False)
        (output/'continuous.json').write_text(json.dumps(report,indent=2));(output/'continuous-samples.json').write_text(json.dumps(records))
        print(json.dumps(report),flush=True)
        if report['status']!='PASS':raise SystemExit(1)
    finally:
        if native:native.close()
        context.close()

if __name__=='__main__':
    if sys.argv[1]=='diagnostics':diagnostics()
    elif sys.argv[1]=='continuous':continuous(float(sys.argv[2]) if len(sys.argv)>2 else 90)
    else:raise ValueError('Unknown validation mode')
