"""Measure existing facial frames for a Canvas layer preview. Writes JSON only."""
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np

HERE=Path(__file__).resolve().parent
SHARED=HERE.parent.parent
ANCHOR=SHARED/'aura/assets/avatar/idle_normal/000000.png'
RAW=SHARED/'deliverables/avatar_candidates/batch_003_guide_probe/raw/e2_rest_s421001_L124_guide62'


def load(path):
    im=cv2.imdecode(np.fromfile(str(path),dtype=np.uint8),cv2.IMREAD_UNCHANGED)
    if im is None: raise ValueError(str(path))
    return im


def main():
    anchor=load(ANCHOR)
    gray=cv2.cvtColor(anchor[:,:,:3],cv2.COLOR_BGR2GRAY)
    mask=np.zeros(gray.shape,np.uint8)
    mask[91:145,178:277]=255
    points=cv2.goodFeaturesToTrack(gray,100,.02,4,mask=mask)
    assert points is not None and len(points)>15
    records=[]
    for i in range(124):
        p=RAW/f'{i:06d}.png'
        raw=load(p)
        # Exactly the established waist-up framing, without writing a new bitmap.
        image=cv2.resize(raw[:891,:,:3],(464,480),interpolation=cv2.INTER_AREA)
        target=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        tracked,status,_=cv2.calcOpticalFlowPyrLK(gray,target,points,None,winSize=(15,15),maxLevel=2)
        back,back_status,_=cv2.calcOpticalFlowPyrLK(target,gray,tracked,None,winSize=(15,15),maxLevel=2)
        good=(status[:,0]>0)&(back_status[:,0]>0)&(np.linalg.norm(back[:,0]-points[:,0],axis=1)<.8)
        matrix,inliers=cv2.estimateAffinePartial2D(tracked[good,0],points[good,0],method=cv2.RANSAC,ransacReprojThreshold=1.1)
        assert matrix is not None and int(inliers.sum())>=8, (i,'insufficient facial registration')
        src=tracked[good,0][inliers[:,0]>0]
        dst=points[good,0][inliers[:,0]>0]
        residual=np.linalg.norm(cv2.transform(src[None],matrix)[0]-dst,axis=1)
        scale=float(np.hypot(matrix[0,0],matrix[1,0]))
        assert .93<scale<1.07 and float(np.sqrt(np.mean(residual**2)))<1.2,(i,scale)
        records.append({'frame':i,'matrix':matrix.tolist(),'inliers':int(inliers.sum()),
                        'rms':float(np.sqrt(np.mean(residual**2))),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    profile={'source':'E2 guide62 existing raw frames','width':464,'height':480,'cropHeight':891,'fps':24,
       'anchor':'/media/anchor.png','sourcePrefix':'/media/e2/',
       'mouth':{'cx':225,'cy':151,'rx':17,'ry':12,'solid':.68},
       'eyes':{'cx':226,'cy':126,'rx':35,'ry':15,'solid':.7},
       'clips':[[0,38],[80,118]],'blink':[40,54],
       'anchorSha256':hashlib.sha256(ANCHOR.read_bytes()).hexdigest(),'frames':records}
    (HERE/'profile.json').write_text(json.dumps(profile,indent=2),encoding='utf-8')
    print(json.dumps({'frames':len(records),'max_registration_rms':max(r['rms'] for r in records),
                      'min_inliers':min(r['inliers'] for r in records),'output':str(HERE/'profile.json')}))


if __name__=='__main__':main()
