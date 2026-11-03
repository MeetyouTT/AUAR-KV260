"""Measure existing emotional mouths against their own stable anchors; JSON only."""
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np

from preview_script import AURA

HERE=Path(__file__).resolve().parent


def load(path):
    image=cv2.imdecode(np.fromfile(str(path),np.uint8),cv2.IMREAD_UNCHANGED)
    if image is None:raise ValueError(str(path))
    return image


def main():
    specs={
        'talking_high_reuse_v1':('talking_normal','talking_normal',5,30),
        'talking_high_reuse_v1_b':('talking_normal_b','talking_normal',8,30),
        'talking_low_reuse_v1':('talking_low','talking_low',5,28),
    }
    out={'mouth':{'cx':225,'cy':151,'rx':19,'ry':13,'solid':.7},'assets':{}}
    for name,(source,anchor_name,start,end) in specs.items():
        anchor_path=AURA/'assets/avatar'/anchor_name/'000000.png'
        anchor=load(anchor_path)
        gray=cv2.cvtColor(anchor[:,:,:3],cv2.COLOR_BGR2GRAY)
        mask=np.zeros(gray.shape,np.uint8)
        # Hairline and nose bridge stay available when the source eyes blink.
        mask[65:145,172:282]=255
        mask[112:134,196:257]=0
        points=cv2.goodFeaturesToTrack(gray,120,.015,3,mask=mask)
        assert points is not None and len(points)>12
        records=[]
        for i in range(start,end+1):
            path=AURA/'assets/avatar'/source/f'{i:06d}.png'
            image=load(path);target=cv2.cvtColor(image[:,:,:3],cv2.COLOR_BGR2GRAY)
            tracked,status,_=cv2.calcOpticalFlowPyrLK(gray,target,points,None,winSize=(21,21),maxLevel=3)
            back,back_status,_=cv2.calcOpticalFlowPyrLK(target,gray,tracked,None,winSize=(21,21),maxLevel=3)
            good=(status[:,0]>0)&(back_status[:,0]>0)&(np.linalg.norm(back[:,0]-points[:,0],axis=1)<.8)
            matrix,inliers=cv2.estimateAffinePartial2D(tracked[good,0],points[good,0],method=cv2.RANSAC,ransacReprojThreshold=1.1)
            assert matrix is not None and inliers is not None and int(inliers.sum())>=8,(name,i,'features')
            src=tracked[good,0][inliers[:,0]>0];dst=points[good,0][inliers[:,0]>0]
            residual=np.linalg.norm(cv2.transform(src[None],matrix)[0]-dst,axis=1)
            rms=float(np.sqrt(np.mean(residual**2)));scale=float(np.hypot(matrix[0,0],matrix[1,0]))
            assert rms<1.2 and .92<scale<1.08,(name,i,rms,scale)
            records.append({'frame':i,'matrix':matrix.tolist(),'rms':rms,'inliers':int(inliers.sum()),
                            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        out['assets'][name]={'source':source,'anchor':anchor_name,'anchorSha256':hashlib.sha256(anchor_path.read_bytes()).hexdigest(),'frames':records}
    (HERE/'emotion_profile.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps({name:{'frames':len(spec['frames']),'max_rms':max(row['rms'] for row in spec['frames'])} for name,spec in out['assets'].items()},indent=2))


if __name__=='__main__':main()
