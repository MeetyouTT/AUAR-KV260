"""Camera-shared face targets, independent of body tracking and identity scores."""
import copy
import math
import threading
import time
from board.interaction.ui_contract import millis
from board.vision.reference_core import FaceTracks


class FaceTargetService:
    def __init__(self, factory, on_face, camera_epoch, *, lock=None, clock=millis,
                 interval_ms=200, ttl_ms=1000, minimum_score=.9, minimum_pixels=48):
        self.factory,self.on_face,self.camera_epoch=factory,on_face,camera_epoch
        self.lock=lock or threading.RLock();self.condition=threading.Condition(self.lock)
        self.clock,self.interval,self.ttl=clock,interval_ms,ttl_ms
        self.minimum_score,self.minimum_pixels=minimum_score,minimum_pixels
        self.tracker=FaceTracks(camera_epoch,lost_s=1.,confirm_observations=2)
        self.pending=None;self.thread=None;self.closed=False;self.ready=False;self.error=''
        self.key=None;self.stamp=None;self.count=0;self.tracks=[]
        self.previous_visible=set();self.generations={};self.processed=self.discarded=0;self.last_ms=None
        self.owner_sequence=0

    def start(self):
        with self.condition:
            if self.thread is not None:raise RuntimeError('Face targets already started')
            self.thread=threading.Thread(target=self.work,name='camera-face-targets',daemon=True);self.thread.start()

    def offer(self,image,fid,stamp):
        with self.condition:
            if self.closed:return
            self.pending=(image,fid,stamp);self.condition.notify()

    def current_target(self):
        with self.lock:
            return copy.deepcopy(self.key) if (self.ready and not self.error and self.stamp is not None
                and 0<=self.clock()-self.stamp<self.ttl) else None

    def view(self):
        with self.lock:
            fresh=self.ready and not self.error and self.stamp is not None and 0<=self.clock()-self.stamp<self.ttl
            return {'target_kind':'face','face_target':self.current_target(),
                'face_count':self.count if fresh else 0,'face_targets':copy.deepcopy(self.tracks) if fresh else []}

    def health(self):
        with self.lock:return {'ready':self.ready and not self.error,'error':self.error,
            'processed':self.processed,'discarded':self.discarded,'last_inference_ms':self.last_ms,
            'source_age_ms':None if self.stamp is None else self.clock()-self.stamp}

    def process(self, packet, detector):
        image,fid,stamp=packet
        if not 0<=self.clock()-stamp<self.ttl:
            with self.lock:self.discarded+=1
            return
        started=time.monotonic();raw=detector.detect(image);faces=[]
        if len(raw)<=16:
            for row in raw:
                row=tuple(float(v) for v in row)
                if (len(row)==15 and all(math.isfinite(v) for v in row)
                        and min(row[2:4])>=self.minimum_pixels and row[14]>=self.minimum_score):faces.append(row)
        with self.lock:
            self.last_ms=round((time.monotonic()-started)*1000,2)
            if self.closed or not 0<=self.clock()-stamp<self.ttl:
                self.discarded+=1;return
            observation=self.tracker.update(faces,fid,stamp/1000,640,480)
            visible=[t for t in observation['tracks'] if t['visible']]
            ids={t['track_id'] for t in visible}
            for tid in ids-self.previous_visible:self.generations[tid]=self.generations.get(tid,0)+1
            self.previous_visible=ids
            self.generations={tid:gen for tid,gen in self.generations.items() if tid in self.tracker.tracks}
            confirmed=[t for t in visible if t['confirmed']]
            previous_key=self.key
            self.key=None;self.tracks=[];selected_face=None
            for t in confirmed:
                key={'camera_epoch':self.camera_epoch,'track_id':t['track_id'],'track_generation':self.generations[t['track_id']]}
                self.tracks.append({'key':key,'label':'人脸 #'+str(t['track_id'])})
                if len(faces)==1 and len(confirmed)==1:
                    # FaceTracks publishes the detector's actual box. Never
                    # choose the largest face or re-use a predicted box.
                    candidates=[row for row in faces if all(abs(a-b)<1e-4 for a,b in zip(row[:4],t['box']))]
                    if len(candidates)==1:
                        if previous_key and previous_key['track_id']==t['track_id']:
                            key['track_generation']=previous_key['track_generation']
                        else:
                            self.owner_sequence+=1;key['track_generation']=self.owner_sequence
                        self.key=key;selected_face=candidates[0]
            self.count=len(faces);self.stamp=stamp;self.processed+=1
            key=copy.deepcopy(self.key)
        self.on_face(image,selected_face,fid,stamp,key)

    def work(self):
        try:
            detector=self.factory()
            with self.lock:self.ready=True
            next_at=0
            while True:
                with self.condition:
                    self.condition.wait_for(lambda:self.closed or self.pending is not None)
                    if self.closed:return
                    delay=next_at-time.monotonic()
                    if delay>0:self.condition.wait(delay);continue
                    packet,self.pending=self.pending,None
                self.process(packet,detector);next_at=time.monotonic()+self.interval/1000
        except Exception as exc:
            with self.lock:self.error='人脸目标检测失败：'+str(exc)[:100];self.key=None;self.pending=None

    def close(self):
        with self.condition:self.closed=True;self.pending=None;self.key=None;self.condition.notify_all()
        if self.thread:
            self.thread.join(5)
            if self.thread.is_alive():raise RuntimeError('Face target worker did not stop')
