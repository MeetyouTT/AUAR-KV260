"""Isolated fixed-image v12/v13 comparison: no camera, DPU or actuator imports."""
import argparse,hashlib,importlib.util,json,statistics,sys,time
from pathlib import Path
from types import SimpleNamespace


def load(root,name):
    path=root/'face_flow.py'
    spec=importlib.util.spec_from_file_location(name,str(path))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.FaceFlow,hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-root',type=Path,required=True)
    parser.add_argument('--candidate-root',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--iterations',type=int,default=5)
    parser.add_argument('--budget-seconds',type=float,default=17.)
    args=parser.parse_args()
    if not 3<=args.iterations<=10 or not 3<=args.budget_seconds<=18:
        parser.error('Use 3..10 iterations and a 3..18 second in-process budget')
    began=time.monotonic()
    import cv2
    import numpy as np
    # This benchmark process has no business model; avoid changing global
    # OpenCV settings in the camera owner or using its threads.
    cv2.setNumThreads(1)
    baseline,baseline_sha=load(args.baseline_root.resolve(strict=True),'bench_baseline_flow')
    candidate,candidate_sha=load(args.candidate_root.resolve(strict=True),'bench_candidate_flow')
    def budget():
        if time.monotonic()-began>args.budget_seconds:
            raise TimeoutError('Synthetic benchmark budget exhausted; result incomplete')
    gray=np.zeros((240,320),np.uint8)
    patch=np.random.RandomState(44).randint(0,256,(90,90),dtype=np.uint8)
    gray[60:150,100:190]=cv2.GaussianBlur(patch,(3,3),0)
    box=[100.,60.,90.,90.]
    def transformed(degrees,scale,dx=7,dy=4):
        matrix=cv2.getRotationMatrix2D((145,105),degrees,scale)
        matrix[:,2]+=[dx,dy]
        return cv2.warpAffine(gray,matrix,(320,240))
    translation=transformed(0,1.)
    rotated=transformed(6,1.08)
    samples={'translation':translation,'rotation_scale':rotated,'absent_pixels':np.zeros_like(gray)}
    timings={};tests={};seeds={}
    for label,cls in [('baseline',baseline),('candidate',candidate)]:
        budget();start=time.monotonic();state=cls.seed(gray,box)
        seeds[label]=dict(elapsed_ms=round((time.monotonic()-start)*1000,3),
                          fixed_points=len(state.get('anchor_points',[])) if state.get('anchor_points') is not None else 0)
        for name,image in samples.items():
            elapsed=[];accepted=0;methods=[]
            for _ in range(args.iterations):
                budget();start=time.monotonic();value=cls.step(None,image,state,box)
                elapsed.append((time.monotonic()-start)*1000)
                if value is not None:
                    accepted+=1;methods.append(value[1]['method'])
            timings[label+'_'+name]=dict(iterations=len(elapsed),accepted=accepted,
                median_ms=round(statistics.median(elapsed),3),maximum_ms=round(max(elapsed),3),methods=sorted(set(methods)))
    tests['both_accept_real_translation']=(timings['baseline_translation']['accepted']==args.iterations
                                         and timings['candidate_translation']['accepted']==args.iterations)
    tests['fixed_ncc_rotation_reproducer']=(timings['baseline_rotation_scale']['accepted']==0)
    tests['candidate_rotation_current_pixels']=(timings['candidate_rotation_scale']['accepted']==args.iterations)
    tests['both_reject_absent_pixels']=(timings['baseline_absent_pixels']['accepted']==0
                                     and timings['candidate_absent_pixels']['accepted']==0)
    state=candidate.seed(gray,box)
    random=np.random.RandomState(4).randint(0,256,gray.shape,dtype=np.uint8)
    occluded=rotated.copy();occluded[60:155,140:200]=0
    for label,image in [('random_background',random),('partial_occluder',occluded),
                        ('excessive_transform',transformed(25,1.3)),('unbounded_displacement',transformed(5,1.05,dx=90))]:
        budget();tests['candidate_rejects_'+label]=candidate.step(None,image,state,box) is None
    current_box,current_state=box,state
    fixed=True
    for degrees,scale,dx in [(6,1.08,7),(8,1.10,10),(0,1.,20)]:
        budget();matched=candidate.step(None,transformed(degrees,scale,dx=dx),current_state,current_box)
        if matched is None:fixed=False;break
        current_box,current_state=matched
        fixed &= current_state['template'] is state['template'] and current_state['anchor_gray'] is state['anchor_gray']
    tests['repeated_matches_keep_real_anchor_pixels']=bool(fixed)
    # Run the exact flow contract without importing an application, model,
    # transport, report service or fake actuator.
    face=SimpleNamespace(clock=lambda:1001)
    flow=candidate(face,start=False);key={'camera_epoch':'synthetic','track_id':1,'track_generation':1}
    detector=dict(healthy=True,count=1,key=key,fid=1,stamp=1000,ttl=500,
                  continuity_key=key,box=box,score=.97)
    image=cv2.cvtColor(cv2.resize(gray,(640,480),interpolation=cv2.INTER_NEAREST),cv2.COLOR_GRAY2BGR)
    flow.offer(image,1,1000);initial,_=flow.measure(image,1,1000,detector)
    detector.update(count=0,key=None,box=None,fid=2,stamp=1400)
    image2=cv2.cvtColor(cv2.resize(rotated,(640,480),interpolation=cv2.INTER_NEAREST),cv2.COLOR_GRAY2BGR)
    flow.offer(image2,3,1498);live,_=flow.measure(image2,3,1498,detector)
    flow.offer(image2,4,1500);expired,reason=flow.measure(image2,4,1500,detector)
    tests['anchor_not_renewed_by_lk']=(initial is not None and live is not None
                                     and live['anchor_stamp']==1000 and live['stamp']==1498)
    tests['anchor_500ms_stops']=(expired is None and reason=='FACE_ANCHOR_EXPIRED')
    budget()
    result=dict(status='SYNTHETIC_BENCHMARK_PASS' if all(tests.values()) else 'SYNTHETIC_BENCHMARK_FAILED',
        scope='single isolated process, synthetic fixed pixels only; no camera, model/DPU, HTTP or motor access',
        elapsed_s=round(time.monotonic()-began,3),opencv=cv2.__version__,opencv_threads=cv2.getNumThreads(),
        baseline_sha256=baseline_sha,candidate_sha256=candidate_sha,seeds=seeds,timings=timings,tests=tests,
        hardware_accessed=False,physical_follow_validated=False)
    print(json.dumps(result,separators=(',',':')))
    return 0 if all(tests.values()) else 2


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        print(json.dumps({'status':'SYNTHETIC_BENCHMARK_ERROR','error':type(error).__name__+': '+str(error),
                          'physical_follow_validated':False,'hardware_accessed':False}))
        raise SystemExit(3)
