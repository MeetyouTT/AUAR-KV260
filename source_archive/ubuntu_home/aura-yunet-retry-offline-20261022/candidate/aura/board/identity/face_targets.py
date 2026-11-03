"""Camera-shared face targets, independent of body tracking and identity scores."""
import copy
import math
import threading
import time
from board.interaction.ui_contract import millis
from board.vision.reference_core import FaceTracks, valid_box


class FaceTargetService:
    def __init__(self, factory, on_face, camera_epoch, *, lock=None, clock=millis,
                 interval_ms=200, ttl_ms=1000, minimum_score=.9, minimum_pixels=48,
                 slot_retry=False, retry_clock=time.monotonic):
        if type(slot_retry) is not bool:
            raise ValueError('slot_retry must be an explicit bool')
        self.factory,self.on_face,self.camera_epoch=factory,on_face,camera_epoch
        self.lock=lock or threading.RLock();self.condition=threading.Condition(self.lock)
        self.clock,self.interval,self.ttl=clock,interval_ms,ttl_ms
        self.minimum_score,self.minimum_pixels=minimum_score,minimum_pixels
        self.tracker=FaceTracks(camera_epoch,lost_s=1.,confirm_observations=2)
        self.pending=None;self.thread=None;self.closed=False;self.ready=False;self.error=''
        self.key=None;self.stamp=None;self.count=0;self.tracks=[]
        self.previous_visible=set();self.generations={};self.processed=self.discarded=0;self.last_ms=None
        self.owner_sequence=0
        self.continuity_key=None;self.continuity_stamp=None
        self.attention=None
        self.backend='CPU_YUNET'
        self.slot_retry=slot_retry;self.retry_clock=retry_clock
        self.retry_stats={'enabled':slot_retry,'rounds':0,'retries':0,'denied':0,
            'exhausted':0,'deadline':0,'closed':0,'expired':0,'disabled':0,'busy':0,
            'maximum_round_ms':0.,'maximum_deadline_overrun_ms':0.}

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
                'face_count':self.count if fresh else 0,'face_targets':copy.deepcopy(self.tracks) if fresh else [],
                'face_attention':copy.deepcopy(self.attention) if fresh and self.key else None}

    def health(self):
        with self.lock:return {'ready':self.ready and not self.error,'error':self.error,
            'backend':self.backend,
            'processed':self.processed,'discarded':self.discarded,'last_inference_ms':self.last_ms,
            'source_age_ms':None if self.stamp is None else self.clock()-self.stamp}

    def process(self, packet, detector, *, admission_check=None):
        image,fid,stamp=packet
        if not 0<=self.clock()-stamp<self.ttl:
            with self.lock:self.discarded+=1
            return
        started=time.monotonic()
        from board.vision.dpu_vision_runtime import (SlotUnavailable,
            SlotAdmissionDenied, AdmissionCancelled, OptionalJobDisabled)
        try:
            if admission_check is not None:
                admission_check()
                guarded=getattr(detector,'detect_with_admission_guard',None)
                raw=guarded(image,admission_check) if guarded else detector.detect(image)
            else:
                raw=detector.detect(image)
        except SlotUnavailable as exc:
            # A missed DPU slot is not a negative face observation. Preserve
            # the existing TTL and let the latest frame replace this packet.
            with self.lock:self.discarded+=1
            if admission_check is not None and type(exc) is SlotAdmissionDenied:
                return exc
            return
        except (AdmissionCancelled,OptionalJobDisabled) as exc:
            if admission_check is None:raise
            with self.lock:
                self.discarded+=1
                reason=exc.reason if isinstance(exc,AdmissionCancelled) else 'disabled'
                self.retry_stats[reason]+=1
            return
        faces=[]
        if len(raw)<=16:
            for row in raw:
                row=tuple(float(v) for v in row)
                if (len(row)==15 and all(math.isfinite(v) for v in row)
                        and min(row[2:4])>=self.minimum_pixels and row[14]>=self.minimum_score):faces.append(row)
        with self.lock:
            self.last_ms=round((time.monotonic()-started)*1000,2)
            self.backend=getattr(detector,'kind','CPU_YUNET')
            if self.closed or not 0<=self.clock()-stamp<self.ttl:
                self.discarded+=1;return
            # Bound prediction only in this face tracker. A rapid head movement
            # followed by a stop must not project its old velocity across a face.
            for track in self.tracker.tracks.values():
                dt=stamp/1000-track['observed_time']
                if dt>0:
                    track['velocity']=[max(-size*.25/dt,min(size*.25/dt,speed))
                        for speed,size in zip(track['velocity'],track['box'][2:4])]
            observation=self.tracker.update(faces,fid,stamp/1000,640,480)
            visible=[t for t in observation['tracks'] if t['visible']]
            ids={t['track_id'] for t in visible}
            for tid in ids-self.previous_visible:self.generations[tid]=self.generations.get(tid,0)+1
            self.previous_visible=ids
            self.generations={tid:gen for tid,gen in self.generations.items() if tid in self.tracker.tracks}
            confirmed=[t for t in visible if t['confirmed']]
            previous_key=self.continuity_key
            if (previous_key and (self.continuity_stamp is None or stamp-self.continuity_stamp>=self.ttl
                    or previous_key['track_id'] not in self.tracker.tracks
                    or len(faces)>1 or any(t['track_id']!=previous_key['track_id'] for t in visible))):
                previous_key=None
            self.key=None;self.tracks=[];selected_face=None
            for t in confirmed:
                key={'camera_epoch':self.camera_epoch,'track_id':t['track_id'],'track_generation':self.generations[t['track_id']]}
                self.tracks.append({'key':key,'label':'人脸 #'+str(t['track_id'])})
                if len(faces)==1 and len(confirmed)==1:
                    # FaceTracks publishes the detector's actual box. Never
                    # choose the largest face or re-use a predicted box.
                    candidates=[row for row in faces if valid_box(row[:4],640,480) is not None
                        and all(abs(a-b)<1e-4 for a,b in zip(valid_box(row[:4],640,480),t['box']))]
                    if len(candidates)==1:
                        if previous_key and previous_key['track_id']==t['track_id']:
                            key['track_generation']=previous_key['track_generation']
                        else:
                            self.owner_sequence+=1;key['track_generation']=self.owner_sequence
                        self.key=key;selected_face=candidates[0]
            # A missing detection hides the public target and crop immediately.
            # A return can reuse the private binding only if the SAME live IoU
            # track recovers before its existing 1s expiry, without another face.
            self.continuity_key=copy.deepcopy(self.key or previous_key)
            if self.key:self.continuity_stamp=stamp
            elif self.continuity_key is None:self.continuity_stamp=None
            self.count=len(faces);self.stamp=stamp;self.processed+=1
            key=copy.deepcopy(self.key)
            self.attention=None
            if key and selected_face:
                from board.identity.sampling import pose_quality
                pose=pose_quality(selected_face,0.)
                if pose:
                    self.attention={'version':1,'target':copy.deepcopy(key),'frame_id':fid,
                        'captured_mono_ms':stamp,'ttl_ms':self.ttl,
                        'yaw_ratio':pose['yaw'],'roll_degrees':pose['roll'],
                        'frontal':abs(pose['yaw'])<=.22 and abs(pose['roll'])<=15.}
        self.on_face(image,selected_face,fid,stamp,key)

    def retry_health(self):
        """Numeric opt-in experiment counters; no images or identity fields."""
        with self.lock:return dict(self.retry_stats)

    def _process_with_retry(self, packet, detector):
        from board.vision.dpu_vision_runtime import SlotAdmissionDenied,AdmissionCancelled
        began=self.retry_clock();deadline=None;retries=0
        with self.lock:self.retry_stats['rounds']+=1
        try:
            while True:
                stamp=packet[2]
                def check():
                    # This callback also runs inside the DPU slot. Never wait
                    # for the camera-shared lock while owning that slot.
                    if not self.lock.acquire(False):raise AdmissionCancelled('busy')
                    try:
                        if self.closed:raise AdmissionCancelled('closed')
                        if not 0<=self.clock()-stamp<self.ttl:raise AdmissionCancelled('expired')
                        if deadline is not None and self.retry_clock()>=deadline:
                            raise AdmissionCancelled('deadline')
                    finally:self.lock.release()
                rejected=self.process(packet,detector,admission_check=check)
                if type(rejected) is not SlotAdmissionDenied:return
                with self.lock:self.retry_stats['denied']+=1
                if deadline is None:deadline=rejected.rejected_at+.200
                if retries>=2:
                    with self.lock:self.retry_stats['exhausted']+=1
                    return
                not_before=rejected.rejected_at+.025
                with self.condition:
                    while True:
                        now=self.retry_clock()
                        if self.closed:
                            self.retry_stats['closed']+=1;return
                        if now>=deadline:
                            self.retry_stats['deadline']+=1;return
                        if self.pending is not None and now>=not_before:
                            latest,self.pending=self.pending,None
                            # Re-offering an old frame cannot spend another
                            # CPU preparation. Keep only a new, live packet.
                            if (latest[1]<=packet[1] or latest[2]<packet[2]
                                    or not 0<=self.clock()-latest[2]<self.ttl):
                                self.discarded+=1
                                continue
                            packet=latest;retries+=1;self.retry_stats['retries']+=1
                            break
                        delay=deadline-now
                        if self.pending is not None and now<not_before:
                            delay=min(delay,not_before-now)
                        # Condition.wait releases the camera-shared lock.
                        # No DPU slot is owned here; no image copy or polling.
                        self.condition.wait(delay)
        finally:
            ended=self.retry_clock()
            with self.lock:
                self.retry_stats['maximum_round_ms']=max(
                    self.retry_stats['maximum_round_ms'],(ended-began)*1000.)
                if deadline is not None:
                    self.retry_stats['maximum_deadline_overrun_ms']=max(
                        self.retry_stats['maximum_deadline_overrun_ms'],max(0.,ended-deadline)*1000.)

    def work(self):
        detector=None
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
                if self.slot_retry:self._process_with_retry(packet,detector)
                else:self.process(packet,detector)
                next_at=time.monotonic()+self.interval/1000
        except Exception as exc:
            with self.lock:self.error='人脸目标检测失败：'+str(exc)[:100];self.key=None;self.pending=None
        finally:
            if detector and hasattr(detector,'close'):detector.close()

    def close(self):
        with self.condition:self.closed=True;self.pending=None;self.key=None;self.condition.notify_all()
        if self.thread:
            self.thread.join(5)
            if self.thread.is_alive():raise RuntimeError('Face target worker did not stop')
