"""Measured face-region template matching between YuNet detections, no prediction."""
import collections,threading,time


class FaceFlow:
    def __init__(self, face):
        self.face=face;self.condition=threading.Condition();self.frames=collections.OrderedDict()
        self.closed=False;self.latest=None;self.value=None;self.error='';self.processed=0
        self.reason='WAITING';self.elapsed_ms=0.
        self.thread=threading.Thread(target=self.work,name='aura-face-flow',daemon=True)
        self.thread.start()

    def offer(self,image,fid,stamp):
        with self.condition:
            if self.closed:return
            self.frames[fid]=(image,stamp)
            while len(self.frames)>16:self.frames.popitem(last=False)
            self.latest=(fid,stamp,image);self.condition.notify()

    def snapshot(self):
        with self.condition:return self.value,self.error

    def diagnostics(self):
        with self.condition:return dict(processed=self.processed,reason=self.reason,elapsed_ms=self.elapsed_ms,error=self.error)

    def close(self):
        with self.condition:self.closed=True;self.latest=None;self.frames.clear();self.condition.notify_all()
        self.thread.join(timeout=2)

    @staticmethod
    def seed(gray,box):
        import numpy as np
        x,y,w,h=box
        x0=max(0,int(x+w*.16));x1=min(gray.shape[1],int(x+w*.84))
        y0=max(0,int(y+h*.16));y1=min(gray.shape[0],int(y+h*.84))
        crop=gray[y0:y1,x0:x1]
        if min(crop.shape,default=0)<10 or float(np.std(crop))<8.:return None
        return crop.copy()

    @staticmethod
    def step(previous,current,template,box):
        import cv2,numpy as np
        if template is None:return None
        x,y,w,h=box;radius=min(64,max(16,int(max(w,h)*.6)))
        tx=max(0,int(x+w*.16));ty=max(0,int(y+h*.16))
        x0=max(0,tx-radius);y0=max(0,ty-radius)
        x1=min(current.shape[1],tx+template.shape[1]+radius)
        y1=min(current.shape[0],ty+template.shape[0]+radius)
        search=current[y0:y1,x0:x1]
        if search.shape[0]<template.shape[0] or search.shape[1]<template.shape[1]:return None
        scores=cv2.matchTemplate(search,template,cv2.TM_CCOEFF_NORMED)
        _,score,_,location=cv2.minMaxLoc(scores)
        if not np.isfinite(score) or score<.78:return None
        dx,dy=x0+location[0]-tx,y0+location[1]-ty
        updated=[float(x+dx),float(y+dy),float(w),float(h)]
        if updated[0]<0 or updated[1]<0 or updated[0]+w>current.shape[1] or updated[1]+h>current.shape[0]:return None
        refreshed=FaceFlow.seed(current,updated)
        if refreshed is None:return None
        return updated,refreshed

    def work(self):
        import cv2
        last_fid=None;anchor_id=None;gray=None;template=None;box=None;binding=None
        try:
            while True:
                with self.condition:
                    self.condition.wait_for(lambda:self.closed or self.latest is not None and self.latest[0]!=last_fid)
                    if self.closed:return
                    fid,stamp,image=self.latest;last_fid=fid
                began=time.monotonic();reason='NO_FACE'
                face=self.face
                with face.lock:
                    key=dict(face.key) if face.key else None;source=face.stamp;afid=face.tracker.last_frame
                    track=face.tracker.tracks.get(key['track_id']) if key else None
                    valid=(face.ready and not face.error and not face.fault_latched and face.count==1
                           and track is not None and track['visible'] and track['confirmed']
                           and track['frame_id']==afid and source is not None and 0<=stamp-source<face.ttl)
                    measured=[v/2. for v in track['box']] if valid else None;score=track['score'] if valid else None
                value=None
                if valid:
                    current=cv2.cvtColor(cv2.resize(image,(320,240)),cv2.COLOR_BGR2GRAY)
                    if (anchor_id!=afid or binding!=key or gray is None):
                        with self.condition:seed=self.frames.get(afid)
                        if seed is None:
                            gray=template=box=None;reason='MISSING_ANCHOR_FRAME'
                        else:
                            seed_image,seed_stamp=seed
                            gray=cv2.cvtColor(cv2.resize(seed_image,(320,240)),cv2.COLOR_BGR2GRAY)
                            box=measured;template=self.seed(gray,box);anchor_id=afid;binding=key
                            if afid==fid and template is not None and len(template)>=10:
                                value=dict(frame_id=fid,stamp=stamp,key=key,box=[v*2 for v in box],score=score,anchor_stamp=source)
                    if value is None and gray is not None:
                        step=self.step(gray,current,template,box)
                        if step is not None:
                            box,template=step
                            value=dict(frame_id=fid,stamp=stamp,key=key,box=[v*2 for v in box],score=score,anchor_stamp=source)
                        else:reason='FLOW_REJECTED'
                    if value is None:gray=template=box=None
                    else:gray=current
                else:gray=template=box=None;anchor_id=None;binding=None
                with self.condition:
                    self.value=value;self.processed+=1;self.reason='MEASURED' if value is not None else reason
                    self.elapsed_ms=round((time.monotonic()-began)*1000,3)
                with face._edge_signal:
                    face._edge_revision+=1;face._edge_signal.notify_all()
        except BaseException as exc:
            with self.condition:self.value=None;self.error=type(exc).__name__
