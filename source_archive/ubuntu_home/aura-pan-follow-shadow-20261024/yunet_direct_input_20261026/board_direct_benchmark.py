"""Bounded fake-native, complete detector A/B. Never opens a model or device."""
import argparse,hashlib,json,statistics,sys,time,types
from pathlib import Path
import cv2
import numpy as np


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--runtime-root',type=Path,required=True)
    parser.add_argument('--iterations',type=int,default=20)
    parser.add_argument('--max-seconds',type=float,default=12)
    args=parser.parse_args()
    assert 2<=args.iterations<=20 and 1<=args.max_seconds<=14
    sys.path.insert(0,str(args.runtime_root));cv2.setNumThreads(1)
    from board.vision import dpu_vision_runtime as rt,reference_faces as ref
    from fast_yunet_input import FastYuNetNetwork
    from direct_yunet_input import install
    def measured(name,function,*a,**kw):return function(*a,**kw)
    original_check=ref.checked_net
    ref.checked_net=lambda *a,**kw:None
    rng=np.random.RandomState(73)
    values={}
    for i,shape in enumerate([(5,5,51),(10,10,34),(40,40,51),(20,20,34)]):
        value=rng.uniform(-.5,.5,(1,)+shape).astype(np.float32)
        row=value.reshape(-1,17);row[:,14]=4;row[:,15]=-4;row[:,16]=.5
        positive=np.arange(min(12,len(row)))*max(1,len(row)//13)
        row[positive,14]=-4;row[positive,15]=4;row[positive,16]=1
        values[str(i)]=value
    class Adapter:
        def __init__(self):
            self.native_critical=True
            self.runner=types.SimpleNamespace(input_fix=7,inputs=[types.SimpleNamespace(dims=[1,320,320,3])])
            self._admission_check=lambda:None
            self.guard_seen=None;self.input_seen=None
            self.detector=ref.YuNetCompat('never-opened')
            self.detector.net=FastYuNetNetwork(self,rt.yunet_outputs,measured)
        def _native_scheduled(self,source,check):
            self.guard_seen=check;self.input_seen=source
            check()
            return values
    try:
        previous=Adapter()
        install(Adapter,rt.yunet_outputs,measured,ref.YuNetCompat,ref.bgr_image)
        direct=Adapter()
    finally:ref.checked_net=original_check
    rows=[];began=time.monotonic()
    for i in range(args.iterations):
        if time.monotonic()-began>=args.max_seconds:break
        image=rng.randint(0,256,(480,640,3),dtype=np.uint8)
        if i%3==1:image=image[:,::-1]
        if i==0:image=np.resize(np.arange(256,dtype=np.uint8),image.shape)
        outputs={};timings={};cpus={}
        order=[('v16',previous),('direct',direct)]
        if i%2:order.reverse()
        for name,adapter in order:
            wall=time.monotonic_ns();cpu=time.thread_time_ns()
            outputs[name]=adapter.detector.detect(image)
            cpus[name]=(time.thread_time_ns()-cpu)/1e6
            timings[name]=(time.monotonic_ns()-wall)/1e6
            assert adapter.guard_seen is adapter._admission_check
        assert np.array_equal(previous.input_seen,direct.input_seen)
        assert np.array_equal(outputs['v16'],outputs['direct'])
        rows.append(dict(index=i,wall_ms=timings,thread_cpu_ms=cpus,
                         input_byte_equal=True,face_rows_byte_equal=True,face_count=len(outputs['direct'])))
    assert len(rows)>=2
    print(json.dumps(dict(status='PAIRED_COMPLETE_FAKE_DETECT_EQUAL',iterations=len(rows),
        elapsed_s=round(time.monotonic()-began,3),cv2=cv2.__version__,
        reference_sha256=hashlib.sha256(Path(ref.__file__).read_bytes()).hexdigest(),
        runtime_sha256=hashlib.sha256(Path(rt.__file__).read_bytes()).hexdigest(),
        medians={kind:{name:round(statistics.median(row[kind][name] for row in rows),3)
                       for name in ('v16','direct')} for kind in ('wall_ms','thread_cpu_ms')},
        rows=rows,dpu_jobs=0,motor_commands=0,model_opened=False,
        scope='paired full resize/input/layout/decode/NMS with same fake native outputs; not real inference or physical latency')))


if __name__=='__main__':main()
