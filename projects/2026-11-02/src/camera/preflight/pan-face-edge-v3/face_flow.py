"""Measured face-region optical flow between YuNet detections, no prediction."""
import collections,threading,time


class FaceFlow:
    def __init__(self, face):
        self.face=face;self.condition=threading.Condition();self.frames=collections.OrderedDict()
        self.closed=False;self.latest=None;self.value=None;self.error='';self.processed=0
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

    def close(self):
        with self.condition:self.closed=True;self.latest=None;self.frames.clear();self.condition.notify_all()
        self.thread.join(timeout=2)

    @staticmethod
    def seed(gray,box):
        import cv2,numpy as np
        x,y,w,h=box
        mask=np.zeros(gray.shape,dtype=np.uint8)
        # Features stay inside the face; background cannot carry a lost face.
        x0=max(0,int(x+w*.12));x1=min(gray.shape[1],int(x+w*.88))
        y0=max(0,int(y+h*.12));y1=min(gray.shape[0],int(y+h*.88))
        mask[y0:y1,x0:x1]=255
        return cv2.goodFeaturesToTrack(gray,maxCorners=48,qualityLevel=.03,minDistance=5,mask=mask,blockSize=5)

    @staticmethod
    def step(previous,current,points,box):
        import cv2,numpy as np
        if points is None or len(points)<10:return None
        args=dict(winSize=(21,21),maxLevel=3,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,20,.03))
        forward,valid,error=cv2.calcOpticalFlowPyrLK(previous,current,points,None,**args)
        if forward is None:return None
        back,ok,_=cv2.calcOpticalFlowPyrLK(current,previous,forward,None,**args)
        if back is None:return None
        good=(valid.reshape(-1)>0)&(ok.reshape(-1)>0)&(error.reshape(-1)<25)
        good &= np.linalg.norm((back-points).reshape(-1,2),axis=1)<1.5
        if good.sum()<10 or good.mean()<.65:return None
        old=points[good].reshape(-1,2);new=forward[good].reshape(-1,2)
        displacement=new-old;delta=np.median(displacement,axis=0)
        keep=np.linalg.norm(displacement-delta,axis=1)<3.
        if keep.sum()<10 or keep.mean()<.75:return None
        old,new=old[keep],new[keep]
        # Reject collapse onto a small texture patch and large sudden jumps.
        x,y,w,h=box
        if (np.linalg.norm(delta)>min(w,h)*.35 or np.ptp(new[:,0])<w*.25
                or np.ptp(new[:,1])<h*.25):return None
        shift=np.median(new-old,axis=0)
        updated=[float(x+shift[0]),float(y+shift[1]),float(w),float(h)]
        if updated[0]<0 or updated[1]<0 or updated[0]+w>640 or updated[1]+h>480:return None
        return updated,new.reshape(-1,1,2).astype(np.float32)

    def work(self):
        import cv2
        last_fid=None;anchor_id=None;gray=None;points=None;box=None;binding=None
        try:
            while True:
                with self.condition:
                    self.condition.wait_for(lambda:self.closed or self.latest is not None and self.latest[0]!=last_fid)
                    if self.closed:return
                    fid,stamp,image=self.latest;last_fid=fid
                face=self.face
                with face.lock:
                    key=dict(face.key) if face.key else None;source=face.stamp;afid=face.tracker.last_frame
                    track=face.tracker.tracks.get(key['track_id']) if key else None
                    valid=(face.ready and not face.error and not face.fault_latched and face.count==1
                           and track is not None and track['visible'] and track['confirmed']
                           and track['frame_id']==afid and source is not None and 0<=stamp-source<500)
                    measured=list(track['box']) if valid else None;score=track['score'] if valid else None
                value=None
                if valid:
                    current=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
                    if (anchor_id!=afid or binding!=key or gray is None):
                        with self.condition:seed=self.frames.get(afid)
                        if seed is None:
                            gray=points=box=None
                        else:
                            seed_image,seed_stamp=seed
                            gray=cv2.cvtColor(seed_image,cv2.COLOR_BGR2GRAY)
                            box=measured;points=self.seed(gray,box);anchor_id=afid;binding=key
                            if afid==fid and points is not None and len(points)>=10:
                                value=dict(frame_id=fid,stamp=stamp,key=key,box=box,score=score,anchor_stamp=source)
                    if value is None and gray is not None:
                        step=self.step(gray,current,points,box)
                        if step is not None:
                            box,points=step
                            value=dict(frame_id=fid,stamp=stamp,key=key,box=box,score=score,anchor_stamp=source)
                    if value is None:gray=points=box=None
                    else:gray=current
                else:gray=points=box=None;anchor_id=None;binding=None
                with self.condition:self.value=value;self.processed+=1
                with face._edge_signal:
                    face._edge_revision+=1;face._edge_signal.notify_all()
        except BaseException as exc:
            with self.condition:self.value=None;self.error=type(exc).__name__
