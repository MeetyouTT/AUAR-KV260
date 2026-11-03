"""Bounded matched-input callback test on ARM; no camera/runner/DB is opened."""
import ast,gc,hashlib,json,os,statistics,threading,time,urllib.request
from pathlib import Path
from types import SimpleNamespace
import cv2
import numpy as np

SOURCE=Path('/home/root/aura-dpu-vision-20261021/runtime/81fdb11903abb71e-live-134783/aura/board/vision/ui_camera_service.py')
EXPECTED='890fea726de2c6d29581ab2ee4c36db5e36df52f3e84ee20cd634fc8961ec2ce'
OLD='image=np.frombuffer(data,dtype=np.uint8).reshape(h,w,3).copy()'
NEW='image=np.frombuffer(data,dtype=np.uint8).reshape(h,w,3)'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))

def health():
    with op.open('http://127.0.0.1:8790/health',timeout=3) as f:s=json.load(f)
    return {k:s.get(k) for k in ('pid','detected_frames','camera_error','detector_error','dpu_schedule')}

def callback(source):
    tree=ast.parse(source)
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='sample')
    module=ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[]))
    state=SimpleNamespace(identity=None,camera_error='',captured=lambda stamp:1)
    latest=[None];stop=threading.Event()
    ns={'np':np,'cv2':cv2,'Gst':SimpleNamespace(FlowReturn=SimpleNamespace(OK=0,EOS=1,ERROR=-1)),
        'millis':lambda:1234,'state':state,'condition':threading.Condition(),'latest':latest,'stop':stop}
    exec(compile(module,'<pinned actual callback>','exec'),ns)
    return ns['sample'],latest,state

def sink(raw):
    buffer=SimpleNamespace(extract_dup=lambda offset,size:raw,get_size=lambda:len(raw))
    caps=SimpleNamespace(get_structure=lambda index:SimpleNamespace(get_value=lambda key:{'width':640,'height':480}[key]))
    item=SimpleNamespace(get_buffer=lambda:buffer,get_caps=lambda:caps)
    return SimpleNamespace(emit=lambda name:item)

def measure(cb,item,count):
    start=time.monotonic_ns();cpu=time.process_time_ns()
    for _ in range(count):assert cb(item)==0
    end_cpu=time.process_time_ns();end=time.monotonic_ns()
    return {'calls':count,'wall_ms_per_call':(end-start)/1e6/count,'process_cpu_ms_per_call':(end_cpu-cpu)/1e6/count}

def main():
    raw_source=SOURCE.read_bytes();assert hashlib.sha256(raw_source).hexdigest()==EXPECTED
    source=raw_source.decode();assert source.count(OLD)==1
    candidate=source.replace(OLD,NEW,1)
    assert hashlib.sha256(candidate.encode()).hexdigest()=='d74e30250e94584217c90eba9efaed41413e72d64505eeecd20d7cce66e7de45'
    cv2.setNumThreads(1);before=health()
    data=((np.arange(640*480*3,dtype=np.uint32)*17+13)%256).astype(np.uint8).reshape(480,640,3)
    raw=data.tobytes();item=sink(raw)
    a,la,sa=callback(source);b,lb,sb=callback(candidate)
    assert a(item)==b(item)==0
    np.testing.assert_array_equal(la[0][2],lb[0][2])
    np.testing.assert_array_equal(lb[0][2],data[:,::-1,:])
    assert lb[0][2].flags.owndata and not np.shares_memory(lb[0][2],data)
    mutable=bytearray(raw);assert b(sink(mutable))==0;reference=lb[0][2].copy()
    mutable[:]=b'\0'*len(mutable);gc.collect();np.testing.assert_array_equal(lb[0][2],reference)
    assert b(sink(raw[:-1]))==-1 and sb.camera_error=='Unexpected BGR capture layout'
    # Fresh callback after the deliberate invalid-layout test.
    b,lb,sb=callback(candidate)
    for cb in (a,b):measure(cb,item,8)
    rows=[]
    for pair in range(6):
        row={'pair':pair,'order':['original','candidate'] if pair%2==0 else ['candidate','original']}
        for name in row['order']:
            row[name]=measure(a if name=='original' else b,item,40)
            time.sleep(.15)
        rows.append(row)
        current=health();assert current['pid']==before['pid'] and not current['camera_error'] and not current['detector_error']
    after=health();assert after['detected_frames']>before['detected_frames'] and after['pid']==before['pid']
    original=statistics.median(x['original']['process_cpu_ms_per_call'] for x in rows)
    optimized=statistics.median(x['candidate']['process_cpu_ms_per_call'] for x in rows)
    print(json.dumps({'scope':'SYNTHETIC_MATCHED_INPUT_ACTUAL_CALLBACK_ARM_MICROBENCHMARK_NO_PRODUCTION_CHANGE',
        'source_sha256':EXPECTED,'candidate_sha256':hashlib.sha256(candidate.encode()).hexdigest(),
        'opencv':cv2.__version__,'numpy':np.__version__,'benchmark_opencv_threads':1,
        'synthetic_input_bytes':len(raw),'pairs':rows,'tested_calls_per_variant':240,
        'median_original_process_cpu_ms_per_call':original,'median_candidate_process_cpu_ms_per_call':optimized,
        'median_process_cpu_reduction_fraction':1-optimized/original,
        'pixel_memory_and_layout_checks_passed':True,'existing_camera_before':before,'existing_camera_after':after,
        'limitations':['synthetic in-memory BGR; Gst extract_dup simulated and not timed as real driver copy',
            'existing live process runs concurrently; microbenchmark result is not whole-board CPU gain',
            'candidate production deployment and actual GStreamer lifetime acceptance remain unverified'],
        'camera_or_dpu_owner_opened':False,'biometric_data_used':False,'production_modified':False}),flush=True)

main()
