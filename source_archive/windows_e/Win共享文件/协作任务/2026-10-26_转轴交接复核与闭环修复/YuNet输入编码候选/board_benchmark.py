"""Isolated synthetic input-adapter comparison; never opens model/device/DPU."""
import argparse,hashlib,json,signal,sys,time
from pathlib import Path
from types import SimpleNamespace
import cv2,numpy as np
from fast_yunet_input import FastYuNetNetwork,encode_blob_integer_nhwc,install


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root',type=Path,required=True)
    parser.add_argument('--iterations',type=int,default=20)
    parser.add_argument('--max-seconds',type=int,default=12)
    a=parser.parse_args()
    if not 5<=a.iterations<=20 or not 1<=a.max_seconds<=14:parser.error('Use5..20 iterations and1..14 seconds')
    sys.path.insert(0,str(a.runtime_root.resolve()))
    from board.vision import dpu_vision_runtime as runtime
    reference_path=Path(runtime.__file__)
    runtime.yunet_outputs=lambda x:x  # Both adapters get the identical fake output transform.
    cv2.setNumThreads(1)
    def deadline(*args):raise TimeoutError('Synthetic input-adapter benchmark deadline')
    signal.signal(signal.SIGALRM,deadline);signal.alarm(a.max_seconds)
    started=time.monotonic();rng=np.random.RandomState(733)
    guard=lambda:None;guard.source_expires_monotonic_ns=123456789
    guard_objects=[]
    def fake_schedule(source,check):
        guard_objects.append(check is guard);check();return source
    adapter=SimpleNamespace(native_critical=True,
        runner=SimpleNamespace(input_fix=7,inputs=[SimpleNamespace(dims=[1,320,320,3])]),
        detector=SimpleNamespace(net=object()),_admission_check=guard,_native_scheduled=fake_schedule)
    def reference_execute(source):return adapter._native_scheduled(runtime.encode(source,7),guard)
    old=runtime.YuNetNetwork(adapter.runner,execute=reference_execute)
    fast=FastYuNetNetwork(adapter,lambda x:x)
    rows={key:[] for key in ('reference_total','fast_total','reference_adapter','fast_adapter',
                            'reference_set_input','fast_set_input')}
    equal=0;output_hashes=[]
    for index in range(a.iterations):
        if time.monotonic()-started>a.max_seconds:raise TimeoutError('Benchmark budget')
        image=rng.randint(0,256,(480,640,3),dtype=np.uint8)
        if index==0:image[:]=255
        elif index==1:image[:]=0
        results={}
        pairs=(('reference',old),('fast',fast)) if index%2==0 else (('fast',fast),('reference',old))
        for name,network in pairs:
            began=time.monotonic_ns()
            blob=cv2.dnn.blobFromImage(cv2.resize(image,(320,320),interpolation=cv2.INTER_LINEAR))
            adapted=time.monotonic_ns();network.setInput(blob);set_end=time.monotonic_ns()
            results[name]=network.forward(['loc','conf','iou']);finished=time.monotonic_ns()
            rows[name+'_total'].append((finished-began)/1e6)
            rows[name+'_adapter'].append((finished-adapted)/1e6)
            rows[name+'_set_input'].append((set_end-adapted)/1e6)
        if not np.array_equal(results['reference'],results['fast']):raise AssertionError('Input bytes differ')
        equal+=1;output_hashes.append(hashlib.sha256(results['fast'].tobytes()).hexdigest())
    blob=np.arange(256,dtype=np.float32).repeat(1200).reshape(1,3,320,320)
    expected=runtime.encode(np.ascontiguousarray(blob.transpose(0,2,3,1)/256.),7)
    assert np.array_equal(expected,encode_blob_integer_nhwc(blob))
    rejected=0
    for value in (float('nan'),float('inf'),-1.,256.,.5):
        invalid=blob.copy();invalid.flat[0]=value
        try:fast.setInput(invalid)
        except ValueError:rejected+=1
        else:raise AssertionError('Unsupported sample domain accepted')
        assert fast.source is None
    class Legacy:
        def __init__(self):self.native_critical=False;self.detector=SimpleNamespace(net=object())
    install(Legacy,lambda x:x);legacy=Legacy();assert not isinstance(legacy.detector.net,FastYuNetNetwork)
    forbidden=[name for name in ('vart','xir','board.vision.native_binding','vsrv_driver','vsrv_transport') if name in sys.modules]
    assert not forbidden
    timings={}
    for key,values in rows.items():
        values=sorted(values);n=len(values)
        timings[key]=dict(samples=n,median_ms=round((values[(n-1)//2]+values[n//2])/2,3),maximum_ms=round(values[-1],3))
    signal.alarm(0)
    print(json.dumps(dict(status='FAST_INPUT_SYNTHETIC_PASS',elapsed_s=round(time.monotonic()-started,3),
        iterations=a.iterations,opencv=cv2.__version__,opencv_threads=cv2.getNumThreads(),timings=timings,
        checks=dict(all_frames_bit_equal=equal==a.iterations,all256_levels_equal=True,
            invalid_domains_rejected=rejected,exact_guard_object=all(guard_objects),legacy_network_unchanged=True,
            model_or_actuator_module_loaded=forbidden),
        runtime_source_sha256=hashlib.sha256(reference_path.read_bytes()).hexdigest(),
        output_sequence_sha256=hashlib.sha256(''.join(output_hashes).encode()).hexdigest(),
        scope='synthetic BGR resize/blob plus whole setInput/forward; real reference encode; both native execution and output layout use identical fake/identity; fast validation included; not inference or mechanical latency',
        DPU_opened=False,MMIO_opened=False,camera_opened=False)))


if __name__=='__main__':main()
