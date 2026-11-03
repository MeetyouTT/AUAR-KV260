"""Target CPU timing on synthetic pixels; no actuator or DPU access."""
import json,sys,time
from pathlib import Path
sys.path.insert(0,'/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/face-source-v7')
import cv2,numpy as np
from face_flow import FaceFlow
gray=np.zeros((240,320),np.uint8);gray[60:150,100:190]=np.random.RandomState(3).randint(0,256,(90,90),dtype=np.uint8)
box=[100.,60.,90.,90.];state=FaceFlow.seed(gray,box);moved=cv2.warpAffine(gray,np.float32([[1,0,8],[0,1,-3]]),(320,240));times=[]
for _ in range(40):
 t=time.monotonic();result=FaceFlow.step(gray,moved,state,box);times.append((time.monotonic()-t)*1000)
 assert result is not None and abs(result[0][0]-108)<.5
times.sort();print(json.dumps({'status':'FAST_FACE_V7_SYNTHETIC_CPU_BENCH','median_ms':times[len(times)//2],'p95_ms':times[int(len(times)*.95)],'maximum_ms':max(times),'cv_threads':cv2.getNumThreads(),'real_dpu_jobs':0,'physical_actuator_access':False}))
assert times[int(len(times)*.95)]<30,'Measurement too slow for live source deadline'
