"""Independent eyelid scheduling and audio-amplitude mouth selection.

Only existing local eye/mouth pixels are used. No new runtime FSM states.
"""
from __future__ import annotations
import bisect
import hashlib
import json
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image
from tools.mouth_compositor import aperture_score
from tools.pillow_compat import AFFINE,BICUBIC

AURA=Path(__file__).resolve().parents[1]
DELIVERY=AURA.parent/'deliverables'/'2026-10-06_voice_blink'


class BlinkSchedule:
    def __init__(self,seed=20261007):
        self.rng=random.Random(seed);self.starts=[1.3]
        while self.starts[-1]<3600:self.starts.append(self.starts[-1]+self.rng.uniform(3.2,5.8))
        self.duration=.29

    def phase(self,t):
        while t>=self.starts[-1]:self.starts.append(self.starts[-1]+self.rng.uniform(3.2,5.8))
        index=bisect.bisect_right(self.starts,t)-1
        if index<0:return None
        phase=t-self.starts[index]
        return phase if 0<=phase<self.duration else None


def warp(image,matrix,size=(464,480)):
    a,b,c=matrix[0];d,e,f=matrix[1];det=a*e-b*d
    if abs(det)<1e-8:raise ValueError('Singular eye transform')
    inverse=(e/det,-b/det,(b*f-e*c)/det,-d/det,a/det,(d*c-a*f)/det)
    # Eyelids occupy a small patch. Keep the original affine sampling while
    # avoiding a full portrait-sized bicubic warp on each blink frame.
    box=image.getbbox()
    result=Image.new('RGBA',size)
    if box is None:return result
    box=(max(0,box[0]-3),max(0,box[1]-3),min(image.width,box[2]+3),min(image.height,box[3]+3))
    corners=[(a*x+b*y+c,d*x+e*y+f) for x,y in
             ((box[0],box[1]),(box[2],box[1]),(box[2],box[3]),(box[0],box[3]))]
    left=max(0,math.floor(min(x for x,_ in corners))-3)
    top=max(0,math.floor(min(y for _,y in corners))-3)
    right=min(size[0],math.ceil(max(x for x,_ in corners))+3)
    bottom=min(size[1],math.ceil(max(y for _,y in corners))+3)
    if right<=left or bottom<=top:return result
    ia,ib,ic,id,ie,iff=inverse
    local=(ia,ib,ic+ia*left+ib*top-box[0],id,ie,iff+id*left+ie*top-box[1])
    patch=image.crop(box).transform((right-left,bottom-top),AFFINE,local,BICUBIC)
    result.paste(patch,(left,top))
    return result


class BlinkLayer:
    ALIASES={'talking_calm_reuse_v1':'idle_normal','talking_calm_reuse_v1_b':'idle_normal',
             'talking_high_reuse_v1':'talking_normal','talking_high_reuse_v1_b':'talking_normal',
             'talking_low_reuse_v1':'talking_low'}
    def __init__(self,root=DELIVERY):
        self.root=Path(root);self.profile=json.loads((self.root/'blink_profile.json').read_text(encoding='utf-8'))
        self.schedule=BlinkSchedule();self.images={}
        for name,data in self.profile['targets'].items():
            path=AURA/'assets/avatar'/name/'000000.png'
            if hashlib.sha256(path.read_bytes()).hexdigest()!=data['anchor_sha256']:raise ValueError('Blink anchor changed')
            frames=[]
            for record in data['layers']:
                path=self.root/record['file']
                if hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Blink layer changed')
                frames.append(Image.open(path).convert('RGBA'))
            self.images[name]=frames

    def overlay(self,asset,t,index=0):
        phase=self.schedule.phase(t);name=self.ALIASES.get(asset,asset)
        if phase is None or name not in self.images:return None,phase
        times=self.profile['times'];left=max(0,bisect.bisect_right(times,phase)-1);right=min(left+1,len(times)-1)
        alpha=(phase-times[left])/(times[right]-times[left]) if left!=right else 0
        patch=Image.blend(self.images[name][left],self.images[name][right],alpha)
        layer=Image.new('RGBA',(464,480));layer.paste(patch,self.profile['bounds'][:2])
        if asset not in self.ALIASES:
            poses=self.profile['targets'][name]['poses'];pose=poses[max(0,min(int(index),len(poses)-1))]['matrix']
            layer=warp(layer,pose)
        return layer,phase

    def apply(self,meta,t,core=None):
        layer,phase=self.overlay(meta['asset'],t,meta.get('index',0))
        result=dict(meta);result['blink_active']=layer is not None;result['blink_phase']=phase if layer is not None else None
        deferred=meta.get('portrait_offsets_deferred',False)
        if layer is not None:
            if not deferred and core is not None and core.idle_gain>0:
                from board.interaction.avatar_timing import idle_offsets
                layer=core._apply_offsets(layer,idle_offsets(t,gain=core.idle_gain))
            image=Image.alpha_composite(meta['image'],layer);image.putalpha(meta['image'].getchannel('A'));result['image']=image
        if deferred and core is not None and core.idle_gain>0:
            from board.interaction.avatar_timing import idle_offsets
            result['image']=core._apply_offsets(result['image'],idle_offsets(t,gain=core.idle_gain))
        result['portrait_offsets_deferred']=False
        return result


def aperture_levels(pcm,rate=24000,hop=.01):
    """Smooth acoustic intensity, without claiming a phoneme transcript."""
    audio=np.asarray(pcm,dtype=float)/32768.0;n=max(1,round(rate*hop));window=n*2
    if audio.ndim!=1 or not len(audio):raise ValueError('Expected nonempty mono PCM')
    starts=np.arange(0,len(audio),n);ends=np.minimum(starts+window,len(audio))
    cumulative=np.concatenate(([0.0],np.cumsum(audio*audio)))
    rms=np.sqrt((cumulative[ends]-cumulative[starts])/np.maximum(1,ends-starts))
    reference=max(.025,float(np.percentile(rms,85)))
    target=np.clip((rms/reference)**.65,0,1)
    result=[];level=0
    for value in target:
        rate_factor=.45 if value>level else .26
        level+=rate_factor*(value-level);result.append(round(level,5))
    return result


def interpolate(values,t,hop=.01):
    p=max(0,t/hop);i=int(p)
    if i>=len(values):return 0.0
    a=values[i];b=values[i+1] if i+1<len(values) else 0
    return a+(b-a)*(p-i)


class MouthBank:
    def __init__(self,core):
        self.core=core;self.keys={}
        for name,frames in core._reuse_frames.items():
            candidates=[]
            for i,image in enumerate(frames):
                score=aperture_score(image)
                candidates.append((score,i))
            top=max(score for score,_ in candidates)
            keys=[(0,core._reuse_anchors[name])]
            for desired in (.25,.50,.75,1):
                score,i=min(candidates,key=lambda row:abs(row[0]-top*desired))
                if score>keys[-1][0]:keys.append((score,frames[i]))
            if len(keys)<2:raise ValueError('No open mouth key: '+name)
            self.keys[name]=[(score/top,image) for score,image in keys]

    def image(self,name,level,gain):
        keys=self.keys[name];levels=[row[0] for row in keys];p=max(0,min(1,level))
        right=min(bisect.bisect_left(levels,p),len(keys)-1);left=max(0,right-1)
        span=levels[right]-levels[left]
        alpha=(p-levels[left])/span if span else 0
        image=Image.blend(keys[left][1],keys[right][1],alpha)
        return Image.blend(self.core._reuse_anchors[name],image,max(0,min(1,gain)))


class FacialController:
    def __init__(self,core,plan):
        self.core=core;self.plan=plan;self.eyes=BlinkLayer();self.mouths=MouthBank(core)
        self.levels={name:aperture_levels(pcm) for name,pcm in plan.clips.items()}

    def apply(self,meta,t):
        row=self.plan.utterance_at(t);result=dict(meta)
        # A cancelled utterance retains its final aperture through the existing
        # 180ms closing gain, rather than falling back to another loop phase.
        tail=next((u for u in reversed(self.plan.utterances) if u['interrupted'] and u['end']<=t<u['end']+.18),None)
        active=row or tail
        if active and meta['asset'] in self.mouths.keys and (tail or not meta.get('transitioning')):
            elapsed=t-active['start'] if row else active['end']-active['start']-1/24000
            level=interpolate(self.levels[active['scene']],elapsed)
            image=self.mouths.image(meta['asset'],level,meta.get('speech_gain',1))
            if self.core.idle_gain>0:
                from board.interaction.avatar_timing import idle_offsets
                image=self.core._apply_offsets(image,idle_offsets(t,gain=self.core.idle_gain))
            result['image']=image;result['mouth_level']=level
        else:result['mouth_level']=0
        return self.eyes.apply(result,t,self.core)
