"""Extract existing eyelid motion into a masked, retargeted local eye layer."""
import hashlib
import json
import math
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image,ImageDraw

HERE=Path(__file__).resolve().parent
REUSE=HERE.parent/'2026-10-06_avatar_reuse'
SHARED=HERE.parent.parent;AURA=SHARED/'aura'
RAW=SHARED/'deliverables/avatar_candidates/batch_003_guide_probe/raw/e2_rest_s421001_L124_guide62'
FRAMES=[42,44,45,46,47,49,51]
TIMES=[0,.055,.09,.13,.165,.225,.29]
TARGETS=['idle_normal','idle_present','idle_listening','idle_thinking','talking_normal','talking_low']
BOUNDS=(178,105,277,143)


def matrix_between(source,target):
    gray=cv2.cvtColor(np.array(source)[:,:,:3],cv2.COLOR_RGB2GRAY)
    other=cv2.cvtColor(np.array(target)[:,:,:3],cv2.COLOR_RGB2GRAY)
    mask=np.zeros(gray.shape,np.uint8);mask[66:145,173:282]=255;mask[111:138,184:269]=0
    points=cv2.goodFeaturesToTrack(gray,120,.012,3,mask=mask)
    tracked,status,_=cv2.calcOpticalFlowPyrLK(gray,other,points,None,winSize=(21,21),maxLevel=3)
    back,valid,_=cv2.calcOpticalFlowPyrLK(other,gray,tracked,None,winSize=(21,21),maxLevel=3)
    good=(status[:,0]>0)&(valid[:,0]>0)&(np.linalg.norm(back[:,0]-points[:,0],axis=1)<.9)
    matrix,inliers=cv2.estimateAffinePartial2D(points[good,0],tracked[good,0],method=cv2.RANSAC,ransacReprojThreshold=1.2)
    if matrix is None or inliers is None or int(inliers.sum())<8:raise ValueError('Eye retarget registration failed')
    src=points[good,0][inliers[:,0]>0];dst=tracked[good,0][inliers[:,0]>0]
    residual=np.linalg.norm(cv2.transform(src[None],matrix)[0]-dst,axis=1)
    rms=float(np.sqrt(np.mean(residual**2)))
    if rms>1.3:raise ValueError(f'Eye registration residual {rms}')
    return matrix,rms


def warp(image,matrix):
    a,b,c=matrix[0];d,e,f=matrix[1];det=a*e-b*d
    inverse=(e/det,-b/det,(b*f-e*c)/det,-d/det,a/det,(d*c-a*f)/det)
    return image.transform((464,480),Image.Transform.AFFINE,inverse,Image.Resampling.BICUBIC)


def main():
    profile=json.loads((REUSE/'profile.json').read_text(encoding='utf-8'))
    neutral=Image.open(AURA/'assets/avatar/idle_normal/000000.png').convert('RGBA')
    sources=[];fingerprints=[]
    for i in FRAMES:
        path=RAW/f'{i:06d}.png';record=profile['frames'][i]
        if hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Source changed')
        raw=Image.open(path).convert('RGBA');raw=raw.crop((0,0,864,891)).resize((464,480),Image.Resampling.BOX)
        sources.append(warp(raw,record['matrix']))
        fingerprints.append({'frame':i,'sha256':record['sha256']})
    mask=Image.new('L',(464,480),0);pixels=mask.load()
    # Two separate ellipses exclude eyebrows, nose and the mouth.
    for cx,cy,rx,ry in [(208,125,18,12),(244,126,18,12)]:
        for y in range(cy-ry,cy+ry+1):
            for x in range(cx-rx,cx+rx+1):
                r=math.hypot((x+.5-cx)/rx,(y+.5-cy)/ry)
                u=max(0,min(1,(1-r)/.23));pixels[x,y]=max(pixels[x,y],round(255*u*u*(3-2*u)))
    layers=HERE/'eyes';layers.mkdir(parents=True,exist_ok=True)
    targets={};tiles=[]
    for name in TARGETS:
        base=Image.open(AURA/'assets/avatar'/name/'000000.png').convert('RGBA')
        m,rms=matrix_between(neutral,base)
        data=[]
        transformed_mask=warp(mask,m)
        for index,source in enumerate(sources):
            aligned=warp(source,m);aligned.putalpha(transformed_mask)
            if index in (0,len(sources)-1):aligned.putalpha(Image.new('L',base.size,0))
            path=layers/f'{name}_{index}.png';aligned.crop(BOUNDS).save(path)
            data.append({'file':f'eyes/{path.name}','sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
            composed=Image.alpha_composite(base,aligned)
            composed.putalpha(base.getchannel('A'))
            tiles.append((f'{name} {FRAMES[index]}',composed))
            assert np.array_equal(np.array(composed)[:,:,3],np.array(base)[:,:,3])
            outside=np.array(transformed_mask)==0
            assert np.array_equal(np.array(composed)[outside],np.array(base)[outside])
        # Original non-speaking frames may move slightly; track the eye patch
        # to each original source frame, without doing optical flow at runtime.
        poses=[]
        for p in sorted((AURA/'assets/avatar'/name).glob('*.png')):
            frame=Image.open(p).convert('RGBA');pose,residual=matrix_between(base,frame)
            poses.append({'matrix':pose.tolist(),'rms':residual})
        targets[name]={'anchor_sha256':hashlib.sha256((AURA/'assets/avatar'/name/'000000.png').read_bytes()).hexdigest(),
                       'retarget_rms':rms,'layers':data,'poses':poses}
    report={'version':1,'source_frames':FRAMES,'source_hashes':fingerprints,'times':TIMES,'duration':.29,
            'bounds':BOUNDS,'targets':targets,'mask_policy':'separate eyes only; eyebrows/mouth/body/alpha preserved',
            'scheduler':{'seed':20261007,'min_gap':3.2,'max_gap':5.8,'first_blink':1.3}}
    (HERE/'blink_profile.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    sheet=Image.new('RGB',(7*160,len(TARGETS)*145),'#FCFCF3');draw=ImageDraw.Draw(sheet)
    for i,(label,image) in enumerate(tiles):
        x=i%7*160;y=i//7*145;sheet.paste(image.crop((174,93,279,166)).convert('RGB').resize((160,120)),(x,y));draw.text((x+2,y+122),label,fill='#283540')
    sheet.save(HERE/'blink_review.png')
    print(json.dumps({'targets':len(targets),'frames_per_target':7,'max_retarget_rms':max(t['retarget_rms'] for t in targets.values()),
                      'max_pose_rms':max(p['rms'] for t in targets.values() for p in t['poses']),'outside_mask_difference':0,'alpha_difference':0}),flush=True)


if __name__=='__main__':main()
