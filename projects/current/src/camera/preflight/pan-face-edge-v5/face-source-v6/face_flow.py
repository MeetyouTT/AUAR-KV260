"""Current-frame face-only feature tracking, with visible edge clipping."""
import collections,threading,time


class FaceFlow:
    def __init__(self,face):
        self.face=face;self.condition=threading.Condition();self.frames=collections.OrderedDict()
        self.closed=False;self.latest=self.value=None;self.error='';self.processed=0;self.reason='WAITING';self.elapsed_ms=0.
        self.thread=threading.Thread(target=self.work,name='aura-face-measure-v6',daemon=True);self.thread.start()
    def offer(self,image,fid,stamp):
        with self.condition:
            if self.closed:return
            self.frames[fid]=(image,stamp)
            while len(self.frames)>16:self.frames.popitem(last=False)
            self.latest=(fid,stamp,image);self.condition.notify()
    def snapshot(self):
        with self.condition:return self.value,self.error
    def diagnostics(self):
        with self.condition:return dict(processed=self.processed,reason=self.reason,elapsed_ms=self.elapsed_ms,error=self.error,version=6)
    def close(self):
        with self.condition:self.closed=True;self.latest=None;self.frames.clear();self.condition.notify_all()
        self.thread.join(timeout=2)
    @staticmethod
    def clipped(box,shape):
        x,y,w,h=box;left=max(0.,x);top=max(0.,y);right=min(float(shape[1]),x+w);bottom=min(float(shape[0]),y+h)
        if (w<=0 or h<=0 or right-left<24 or bottom-top<24
                or (right-left)/w<.55 or (bottom-top)/h<.6):return None
        return [left,top,right-left,bottom-top]
    @staticmethod
    def seed(gray,box):
        import cv2,numpy as np
        if FaceFlow.clipped(box,gray.shape) is None:return None
        x,y,w,h=box;x0=max(0,int(x+w*.16));x1=min(gray.shape[1],int(x+w*.84));y0=max(0,int(y+h*.16));y1=min(gray.shape[0],int(y+h*.84))
        crop=gray[y0:y1,x0:x1]
        if min(crop.shape,default=0)<10 or float(np.std(crop))<8:return None
        mask=np.zeros_like(gray);mask[y0:y1,x0:x1]=255
        points=cv2.goodFeaturesToTrack(gray,48,.02,3,mask=mask,blockSize=3)
        return {'template':crop.copy(),'points':points,'method':'FACE_DETECTION_ANCHOR'}
    @staticmethod
    def step(previous,current,state,box):
        import cv2,numpy as np
        if state is None:return None
        x,y,w,h=box;points=state['points'];updated=None;method=None
        if points is not None and len(points)>=8:
            kw=dict(winSize=(15,15),maxLevel=3,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,20,.02))
            forward,ok,_=cv2.calcOpticalFlowPyrLK(previous,current,points,None,**kw)
            if forward is not None:
                backward,back,_=cv2.calcOpticalFlowPyrLK(current,previous,forward,None,**kw)
                if backward is not None:
                    good=(ok.ravel()==1)&(back.ravel()==1)&(np.linalg.norm(backward-points,axis=2).ravel()<1.2)
                    moves=(forward-points).reshape(-1,2)[good]
                    if len(moves)>=8 and len(moves)>=len(points)*.6:
                        delta=np.median(moves,axis=0);inliers=np.linalg.norm(moves-delta,axis=1)<2.5
                        if int(inliers.sum())>=8 and float(inliers.mean())>=.7 and max(abs(delta))<=64:
                            candidate=[float(x+delta[0]),float(y+delta[1]),float(w),float(h)]
                            refreshed=FaceFlow.seed(current,candidate)
                            if refreshed is not None:
                                old=state['template'];patch=cv2.resize(refreshed['template'],(old.shape[1],old.shape[0]))
                                score=float(cv2.matchTemplate(old,patch,cv2.TM_CCOEFF_NORMED)[0,0])
                                if np.isfinite(score) and score>=.55:updated=candidate;method='FACE_LK_FORWARD_BACKWARD'
        if updated is None:
            template=state['template'];radius=min(64,max(16,int(max(w,h)*.6)))
            tx=max(0,int(x+w*.16));ty=max(0,int(y+h*.16));x0=max(0,tx-radius);y0=max(0,ty-radius)
            search=current[y0:min(current.shape[0],ty+template.shape[0]+radius),x0:min(current.shape[1],tx+template.shape[1]+radius)]
            if search.shape[0]<template.shape[0] or search.shape[1]<template.shape[1]:return None
            _,score,_,loc=cv2.minMaxLoc(cv2.matchTemplate(search,template,cv2.TM_CCOEFF_NORMED))
            if not np.isfinite(score) or score<.78:return None
            updated=[float(x+x0+loc[0]-tx),float(y+y0+loc[1]-ty),float(w),float(h)];method='FACE_TEMPLATE_MATCH'
        refreshed=FaceFlow.seed(current,updated)
        if refreshed is None:return None
        refreshed['method']=method
        return updated,refreshed
    def work(self):
        import cv2
        last_fid=None;anchor_id=None;gray=tracked=box=binding=None;previous_stamp=None
        try:
            while True:
                with self.condition:
                    self.condition.wait_for(lambda:self.closed or self.latest is not None and self.latest[0]!=last_fid)
                    if self.closed:return
                    fid,stamp,image=self.latest;last_fid=fid
                began=time.monotonic();reason='NO_FACE';face=self.face
                with face.lock:
                    key=dict(face.key) if face.key else None;source=face.stamp;afid=face.tracker.last_frame
                    track=face.tracker.tracks.get(key['track_id']) if key else None
                    valid=(face.ready and not face.error and not face.fault_latched and face.count==1
                        and track is not None and track['visible'] and track['confirmed'] and track['frame_id']==afid
                        and source is not None and 0<=stamp-source<min(face.ttl,500))
                    measured=[v/2. for v in track['box']] if valid else None;score=track['score'] if valid else None
                value=None
                if valid:
                    current=cv2.cvtColor(cv2.resize(image,(320,240)),cv2.COLOR_BGR2GRAY)
                    if anchor_id!=afid or binding!=key or gray is None or previous_stamp is None or stamp-previous_stamp>=200:
                        with self.condition:seed=self.frames.get(afid)
                        if seed is None:gray=tracked=box=None;reason='MISSING_ANCHOR_FRAME'
                        else:
                            seed_image,seed_stamp=seed;gray=cv2.cvtColor(cv2.resize(seed_image,(320,240)),cv2.COLOR_BGR2GRAY)
                            box=measured;tracked=self.seed(gray,box);anchor_id=afid;binding=key;previous_stamp=seed_stamp
                            if afid==fid and tracked is not None:
                                clipped=self.clipped(box,current.shape)
                                value=dict(frame_id=fid,stamp=stamp,key=key,box=[v*2 for v in clipped],score=score,anchor_stamp=source)
                    if value is None and gray is not None:
                        result=self.step(gray,current,tracked,box)
                        if result is not None:
                            box,tracked=result;clipped=self.clipped(box,current.shape)
                            value=dict(frame_id=fid,stamp=stamp,key=key,box=[v*2 for v in clipped],score=score,anchor_stamp=source)
                        else:reason='FACE_MEASUREMENT_REJECTED'
                    if value is not None:gray=current;previous_stamp=stamp;reason=tracked['method']
                else:gray=tracked=box=None;anchor_id=None;binding=None;previous_stamp=None
                with self.condition:
                    self.value=value;self.processed+=1;self.reason=reason;self.elapsed_ms=round((time.monotonic()-began)*1000,3)
                with face._edge_signal:face._edge_revision+=1;face._edge_signal.notify_all()
        except BaseException as exc:
            with self.condition:self.value=None;self.error=type(exc).__name__+': '+str(exc)[:100]
