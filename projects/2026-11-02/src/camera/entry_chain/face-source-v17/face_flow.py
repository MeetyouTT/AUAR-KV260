"""Face-only current-pixel measurements across a bounded detector miss.

No detector prediction or old coordinate can produce a new measurement stamp.
The detector/identity service is read-only; this module owns only a motion key.
"""
import collections
import threading
import time

ANCHOR_MAX_AGE_MS = 500
MEASUREMENT_MAX_AGE_MS = 250


class FaceFlow:
    def __init__(self, face, *, start=True):
        self.face = face
        self.condition = threading.Condition()
        self.frames = collections.OrderedDict()
        self.closed = False
        self.latest = self.value = None
        self.error = ''
        self.processed = 0
        self.reason = 'WAITING'
        self.elapsed_ms = 0.
        self.offered = 0
        self.offer_source_age_ms = self.offer_gap_ms = self.offer_arrival_gap_ms = None
        self.maximum_offer_gap_ms = self.maximum_offer_arrival_gap_ms = 0
        self.last_offer_arrival = None
        self.snapshot_wait_ms = self.detector_offer_ms = self.maximum_detector_offer_ms = 0.
        self.source_age_at_start_ms = self.source_age_at_finish_ms = None
        self.process_source_gap_ms = self.process_finish_gap_ms = None
        self.maximum_process_source_gap_ms = self.maximum_process_finish_gap_ms = 0
        self.last_process_stamp = self.last_process_finish = None
        self.last_offer = self.last_offer_stamp = None
        self.last_fid = self.last_stamp = None
        self.anchor_id = self.anchor_stamp = self.anchor_key = None
        self.binding = self.template = self.box = self.score = None
        self.continuity_match_skips = self.continuity_match_calls = 0
        self.result_reasons = collections.Counter()
        self.valid_measurements = self.anchor_refreshes = 0
        self.last_valid_source_stamp = self.last_valid_finished = None
        self.maximum_valid_source_gap_ms = self.maximum_valid_finish_gap_ms = 0
        self.last_detector_frame_id = self.last_detector_source_age_ms = None
        self.thread = None
        if start:
            self.thread = threading.Thread(target=self.work, name='aura-face-measure-v11', daemon=True)
            self.thread.start()

    def offer(self, image, fid, stamp):
        with self.condition:
            if (self.closed or (self.last_offer is not None and fid <= self.last_offer)
                    or (self.last_offer_stamp is not None and stamp <= self.last_offer_stamp)):
                return
            arrived = self.clock_ms()
            self.offered += 1
            self.offer_source_age_ms = arrived-stamp
            self.offer_gap_ms = None if self.last_offer_stamp is None else stamp-self.last_offer_stamp
            self.offer_arrival_gap_ms = None if self.last_offer_arrival is None else arrived-self.last_offer_arrival
            self.maximum_offer_gap_ms = max(self.maximum_offer_gap_ms, self.offer_gap_ms or 0)
            self.maximum_offer_arrival_gap_ms = max(self.maximum_offer_arrival_gap_ms, self.offer_arrival_gap_ms or 0)
            self.last_offer, self.last_offer_stamp, self.last_offer_arrival = fid, stamp, arrived
            self.frames[fid] = (image, stamp)
            while len(self.frames) > 16:
                self.frames.popitem(last=False)
            self.latest = (fid, stamp, image)
            self.condition.notify()

    def snapshot(self):
        with self.condition:
            return self.value, self.error

    def diagnostics(self):
        with self.condition:
            return dict(processed=self.processed, reason=self.reason, elapsed_ms=self.elapsed_ms,
                        error=self.error, version=11, anchor_max_age_ms=ANCHOR_MAX_AGE_MS,
                        offered=self.offered, offer_source_age_ms=self.offer_source_age_ms,
                        offer_gap_ms=self.offer_gap_ms, offer_arrival_gap_ms=self.offer_arrival_gap_ms,
                        maximum_offer_gap_ms=self.maximum_offer_gap_ms,
                        maximum_offer_arrival_gap_ms=self.maximum_offer_arrival_gap_ms,
                        snapshot_wait_ms=self.snapshot_wait_ms, detector_offer_ms=self.detector_offer_ms,
                        maximum_detector_offer_ms=self.maximum_detector_offer_ms,
                        source_age_at_start_ms=self.source_age_at_start_ms,
                        source_age_at_finish_ms=self.source_age_at_finish_ms,
                        process_source_gap_ms=self.process_source_gap_ms,
                        process_finish_gap_ms=self.process_finish_gap_ms,
                        maximum_process_source_gap_ms=self.maximum_process_source_gap_ms,
                        maximum_process_finish_gap_ms=self.maximum_process_finish_gap_ms,
                        continuity_match_skips=self.continuity_match_skips,
                        continuity_match_calls=self.continuity_match_calls,
                        algorithm_version=14, result_reasons=dict(self.result_reasons),
                        valid_measurements=self.valid_measurements, anchor_refreshes=self.anchor_refreshes,
                        maximum_valid_source_gap_ms=self.maximum_valid_source_gap_ms,
                        maximum_valid_finish_gap_ms=self.maximum_valid_finish_gap_ms,
                        last_detector_frame_id=self.last_detector_frame_id,
                        last_detector_source_age_ms=self.last_detector_source_age_ms)

    def clock_ms(self):
        return self.face.clock() if hasattr(self.face, 'clock') else time.monotonic_ns()//1000000

    def note_detector_offer(self, elapsed_ms):
        with self.condition:
            self.detector_offer_ms = round(elapsed_ms, 3)
            self.maximum_detector_offer_ms = max(self.maximum_detector_offer_ms, self.detector_offer_ms)

    def close(self):
        with self.condition:
            self.closed = True
            self.value = self.latest = None
            self.frames.clear()
            self.condition.notify_all()
        if self.thread is not None:
            self.thread.join(timeout=2)

    @staticmethod
    def clipped(box, shape):
        x, y, w, h = box
        left, top = max(0., x), max(0., y)
        right, bottom = min(float(shape[1]), x+w), min(float(shape[0]), y+h)
        if (w <= 0 or h <= 0 or right-left < 24 or bottom-top < 24
                or (right-left)/w < .55 or (bottom-top)/h < .6):
            return None
        return [left, top, right-left, bottom-top]

    @staticmethod
    def seed(gray, box):
        import numpy as np
        if FaceFlow.clipped(box, gray.shape) is None:
            return None
        x, y, w, h = box
        x0, x1 = max(0, int(x+w*.16)), min(gray.shape[1], int(x+w*.84))
        y0, y1 = max(0, int(y+h*.16)), min(gray.shape[0], int(y+h*.84))
        crop = gray[y0:y1, x0:x1]
        if min(crop.shape, default=0) < 10 or float(np.std(crop)) < 8:
            return None
        # These pixels and features stay bound to the actual detector image.
        # Later matches never become a new template or renew the real anchor.
        return dict(template=crop.copy(), offset=(x0-x, y0-y), method='FACE_DETECTION_ANCHOR',
                    anchor_gray=gray.copy(),anchor_box=list(box),
                    anchor_crop=(x0,y0,x1,y1))

    @staticmethod
    def anchor_features(state):
        """Extract at most once per real anchor, only on actual NCC failure."""
        import cv2
        import numpy as np
        if 'anchor_points' not in state:
            gray=state.get('anchor_gray')
            if gray is None:return None
            x0,y0,x1,y1=state['anchor_crop']
            mask=np.zeros_like(gray);mask[y0:y1,x0:x1]=255
            # None is cached too: weak texture must not trigger this work
            # repeatedly or acquire features from a later image.
            state['anchor_points']=cv2.goodFeaturesToTrack(gray,maxCorners=40,qualityLevel=.02,
                                                         minDistance=5,mask=mask,blockSize=5)
        return state['anchor_points']

    @staticmethod
    def anchored_lk(current,state,box):
        """Bounded affine fallback, checked against the original face pixels."""
        import cv2
        import numpy as np
        points=FaceFlow.anchor_features(state);anchor=state.get('anchor_gray')
        if points is None or anchor is None or len(points)<12:return None
        options=dict(winSize=(21,21),maxLevel=2,
                     criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,15,.02))
        forward,status,_=cv2.calcOpticalFlowPyrLK(anchor,current,points,None,**options)
        if forward is None or status is None:return None
        backward,reverse,_=cv2.calcOpticalFlowPyrLK(current,anchor,forward,None,**options)
        if backward is None or reverse is None:return None
        original=points.reshape(-1,2);actual=forward.reshape(-1,2)
        returned=backward.reshape(-1,2)
        good=(status.reshape(-1).astype(bool)&reverse.reshape(-1).astype(bool)
              &np.isfinite(actual).all(axis=1)&np.isfinite(returned).all(axis=1)
              &(np.max(np.abs(original-returned),axis=1)<=.75))
        if int(good.sum())<12 or float(good.mean())<.70:return None
        matrix,inliers=cv2.estimateAffinePartial2D(original[good],actual[good],
            method=cv2.RANSAC,ransacReprojThreshold=1.25,maxIters=300,confidence=.99,refineIters=5)
        if matrix is None or inliers is None or not np.isfinite(matrix).all():return None
        mask=inliers.reshape(-1).astype(bool)
        if int(mask.sum())<12 or float(mask.mean())<.80:return None
        support=original[good][mask]
        ax,ay,aw,ah=state['anchor_box']
        # Distributed support prevents one visible eye or an occluder patch
        # from defining the whole face's transform.
        if np.ptp(support[:,0])<aw*.35 or np.ptp(support[:,1])<ah*.35:return None
        quadrants=(support[:,0]>ax+aw/2).astype(int)+2*(support[:,1]>ay+ah/2).astype(int)
        if len(set(quadrants.tolist()))<3:return None
        scale=float(np.hypot(matrix[0,0],matrix[1,0]))
        rotation=float(np.degrees(np.arctan2(matrix[1,0],matrix[0,0])))
        if not .85<=scale<=1.18 or abs(rotation)>15:return None
        corners=np.float32([[ax,ay],[ax+aw,ay],[ax,ay+ah],[ax+aw,ay+ah]])
        projected=corners@matrix[:,:2].T+matrix[:,2]
        left,top=np.min(projected,axis=0);right,bottom=np.max(projected,axis=0)
        updated=[float(left),float(top),float(right-left),float(bottom-top)]
        if FaceFlow.clipped(updated,current.shape) is None:return None
        radius=min(64,max(16,int(max(box[2:])*.6)))
        if max(abs(updated[0]+updated[2]/2-box[0]-box[2]/2),
               abs(updated[1]+updated[3]/2-box[1]-box[3]/2))>radius:return None
        # Affine geometry alone can follow a distractor. Reconstruct current
        # pixels at the fixed detector crop and retain the same .80 NCC gate.
        aligned=cv2.warpAffine(current,matrix,(anchor.shape[1],anchor.shape[0]),
                               flags=cv2.INTER_LINEAR|cv2.WARP_INVERSE_MAP)
        visible=cv2.warpAffine(np.full_like(current,255),matrix,(anchor.shape[1],anchor.shape[0]),
                               flags=cv2.INTER_NEAREST|cv2.WARP_INVERSE_MAP)
        x0,y0,x1,y1=state['anchor_crop']
        if not np.all(visible[y0:y1,x0:x1]==255):return None
        crop=aligned[y0:y1,x0:x1]
        if float(np.std(crop))<8:return None
        score=float(cv2.matchTemplate(crop,state['template'],cv2.TM_CCOEFF_NORMED)[0,0])
        if not np.isfinite(score) or score<.80:return None
        return updated,dict(state,method='FACE_FIXED_ANCHOR_LK_AFFINE',match_score=score,
                            lk_inliers=int(mask.sum()),lk_inlier_ratio=float(mask.mean()),
                            lk_scale=scale,lk_rotation_degrees=rotation)

    @staticmethod
    def partial_edge(current, state, box, radius):
        """Match two fixed anchor patches when only their edge column is visible.

        A real detector crop remains the sole template source. This fallback
        neither rolls/reseeds templates nor lowers score/face quality gates.
        """
        import cv2
        import numpy as np
        x,y,w,h=box;template=state['template'];ox,oy=state['offset']
        th,tw=template.shape;mx,my=tw//2,th//2
        if min(mx,tw-mx,my,th-my)<10:return None
        candidates=[]
        # At the left image edge the right template column remains visible;
        # the symmetric left column is used at the right image edge.
        for side,px,pw in [(-1,mx,tw-mx),(1,0,mx)]:
            if side<0 and x-radius>=0:continue
            if side>0 and x+w+radius<=current.shape[1]:continue
            matches=[]
            for py,ph in [(0,my),(my,th-my)]:
                patch=template[py:py+ph,px:px+pw]
                if float(np.std(patch))<8:break
                expected_x,expected_y=int(x+ox+px),int(y+oy+py)
                x0,y0=max(0,expected_x-radius),max(0,expected_y-radius)
                search=current[y0:min(current.shape[0],expected_y+ph+radius),
                               x0:min(current.shape[1],expected_x+pw+radius)]
                if search.shape[0]<ph or search.shape[1]<pw:break
                _,score,_,loc=cv2.minMaxLoc(cv2.matchTemplate(search,patch,cv2.TM_CCOEFF_NORMED))
                if not np.isfinite(score) or score<.80:break
                matches.append((x0+loc[0]-px-ox,y0+loc[1]-py-oy,float(score)))
            if len(matches)!=2:continue
            if max(abs(matches[0][0]-matches[1][0]),abs(matches[0][1]-matches[1][1]))>1.5:continue
            updated=[float((matches[0][0]+matches[1][0])/2),
                     float((matches[0][1]+matches[1][1])/2),float(w),float(h)]
            # This is exclusively a horizontal edge fallback. The entire
            # original template must be partly outside, both matched fixed
            # patches must be visible, and the original face crop quality must
            # still accept the actual remaining face area.
            is_edge=(updated[0]<0 and updated[0]+ox<0 if side<0 else
                     updated[0]+w>current.shape[1] and updated[0]+ox+tw>current.shape[1])
            if not is_edge or FaceFlow.clipped(updated,current.shape) is None:continue
            score=min(matches[0][2],matches[1][2])
            candidates.append((score,updated,side))
        if not candidates:return None
        score,updated,side=max(candidates,key=lambda item:item[0])
        return updated,dict(state,method='FACE_TEMPLATE_PARTIAL_FIXED_ANCHOR',
                            match_score=score,partial_side=side,partial_patch_count=2)

    @staticmethod
    def step(previous, current, state, box):
        import cv2
        import numpy as np
        if state is None:
            return None
        if state.get('method')=='FACE_FIXED_ANCHOR_LK_AFFINE':
            # Fixed-template translation offsets no longer describe a scaled
            # or rotated crop. Continue measuring against the real anchor.
            return FaceFlow.anchored_lk(current,state,box)
        x, y, w, h = box
        template = state['template']
        ox, oy = state['offset']
        radius = min(64, max(16, int(max(w, h)*.6)))
        tx, ty = int(x+ox), int(y+oy)
        x0, y0 = max(0, tx-radius), max(0, ty-radius)
        search = current[y0:min(current.shape[0], ty+template.shape[0]+radius),
                         x0:min(current.shape[1], tx+template.shape[1]+radius)]
        if search.shape[0] >= template.shape[0] and search.shape[1] >= template.shape[1]:
            _, score, _, loc = cv2.minMaxLoc(cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED))
            if np.isfinite(score) and score >= .80:
                updated = [float(x0+loc[0]-ox), float(y0+loc[1]-oy), float(w), float(h)]
                if FaceFlow.clipped(updated, current.shape) is not None:
                    # Keep the actual detector-anchor template fixed.
                    refreshed = dict(state, method='FACE_TEMPLATE_VISIBLE_CLIP', match_score=float(score))
                    return updated, refreshed
        # Only images whose previous face can reach a horizontal image edge
        # inside the original bounded search window can use partial matching.
        if x-radius<0 or x+w+radius>current.shape[1]:
            partial=FaceFlow.partial_edge(current,state,box,radius)
            if partial is not None:return partial
        return FaceFlow.anchored_lk(current,state,box)

    def detector_snapshot(self):
        face = self.face
        with face.lock:
            key = dict(face.key) if face.key else None
            fid = face.tracker.last_frame
            track = face.tracker.tracks.get(key['track_id']) if key else None
            valid = (face.count == 1 and track is not None and track['visible']
                     and track['confirmed'] and track['frame_id'] == fid
                     and face.stamp is not None
                     and abs(track['observed_time']*1000-face.stamp) <= 1)
            return dict(healthy=face.ready and not face.error and not face.fault_latched
                        and not face.closed, count=face.count, key=key, fid=fid,
                        continuity_key=dict(face.continuity_key) if face.continuity_key else None,
                        stamp=face.stamp, ttl=min(face.ttl, ANCHOR_MAX_AGE_MS),
                        box=[v/2. for v in track['box']] if valid else None,
                        score=track['score'] if valid else None)

    def reset(self):
        self.anchor_id = self.anchor_stamp = self.anchor_key = None
        self.binding = self.template = self.box = self.score = None

    @staticmethod
    def same_face(box, detected):
        ax, ay, aw, ah = box
        bx, by, bw, bh = detected
        overlap = max(0., min(ax+aw, bx+bw)-max(ax, bx))*max(0., min(ay+ah, by+bh)-max(ay, by))
        union = aw*ah+bw*bh-overlap
        return union > 0 and overlap/union >= .5

    def measure(self, image, fid, stamp, detector):
        import cv2
        if ((self.last_fid is not None and fid <= self.last_fid)
                or (self.last_stamp is not None and stamp <= self.last_stamp)):
            return None, 'NON_NEW_IMAGE'
        self.last_fid, self.last_stamp = fid, stamp
        if not detector['healthy'] or detector['count'] > 1:
            self.reset()
            return None, 'MULTIPLE_FACES' if detector['count'] > 1 else 'FACE_ERROR'
        if (detector['stamp'] is None or not 0 <= stamp-detector['stamp'] < detector['ttl']):
            self.reset()
            return None, 'DETECTOR_EXPIRED'
        # A single visible but unconfirmed face cannot borrow an old binding.
        if detector['count'] == 1 and detector['box'] is None:
            self.reset()
            return None, 'UNCONFIRMED_DETECTION'
        if detector['count'] == 0 and (self.anchor_key is None
                                      or detector['continuity_key'] != self.anchor_key):
            self.reset()
            return None, 'FACE_CONTINUITY_LOST'
        current = cv2.cvtColor(cv2.resize(image, (320, 240)), cv2.COLOR_BGR2GRAY)
        if detector['box'] is not None and detector['fid'] != self.anchor_id:
            with self.condition:
                seed = self.frames.get(detector['fid'])
            if seed is None or seed[1] != detector['stamp']:
                self.reset()
                return None, 'MISSING_ANCHOR_FRAME'
            old_box = self.box
            old_binding = self.binding
            old_template = self.template
            seed_gray = cv2.cvtColor(cv2.resize(seed[0], (320, 240)), cv2.COLOR_BGR2GRAY)
            # Bind across detector key churn only when the old anchored pixels
            # also match the newly detected face on its actual source image.
            continuity = None
            if (old_box is not None and old_binding is not None and self.anchor_stamp is not None
                    and 0 <= detector['stamp']-self.anchor_stamp < detector['ttl']
                    and old_binding.get('camera_epoch') == detector['key'].get('camera_epoch')):
                if (old_template is not None and self.anchor_key == detector['key']
                        and old_binding == detector['key']):
                    # This optional NCC can only choose old_binding or the
                    # detector key. When both dicts are exactly equal, either
                    # outcome has the identical motion identity. Keep the new
                    # REAL detector crop/template and all current-pixel checks.
                    self.continuity_match_skips += 1
                else:
                    self.continuity_match_calls += 1
                    continuity = self.step(None, seed_gray, old_template, old_box)
            preserve = continuity is not None and self.same_face(continuity[0], detector['box'])
            self.binding = dict(old_binding if preserve else detector['key'])
            self.anchor_id, self.anchor_stamp = detector['fid'], detector['stamp']
            self.anchor_refreshes += 1
            self.anchor_key = dict(detector['key'])
            self.box, self.score = detector['box'], detector['score']
            self.template = self.seed(seed_gray, self.box)
        if self.template is None or self.anchor_stamp is None:
            return None, 'NO_FACE_ANCHOR'
        if not 0 <= stamp-self.anchor_stamp < detector['ttl']:
            self.reset()
            return None, 'FACE_ANCHOR_EXPIRED'
        if fid == self.anchor_id and stamp == self.anchor_stamp:
            measured = self.box, self.template
        else:
            measured = self.step(None, current, self.template, self.box)
        if measured is None:
            # A real failed pixel match invalidates the motion binding until a
            # newer confirmed detector anchor, rather than reacquiring blindly.
            self.template = self.box = self.binding = None
            return None, 'FACE_MEASUREMENT_REJECTED'
        self.box, self.template = measured
        clipped = self.clipped(self.box, current.shape)
        return dict(frame_id=fid, stamp=stamp, key=dict(self.binding), box=[v*2 for v in clipped],
                    score=self.score, anchor_stamp=self.anchor_stamp, anchor_frame_id=self.anchor_id,
                    detector_key=dict(self.anchor_key), detector_frame_id=detector['fid'],
                    detection_miss=detector['count'] == 0,
                    match_score=self.template.get('match_score'),
                    measurement_method=self.template['method'],
                    lk_inliers=self.template.get('lk_inliers'),
                    lk_scale=self.template.get('lk_scale'),
                    lk_rotation_degrees=self.template.get('lk_rotation_degrees')), self.template['method']

    def work(self):
        try:
            while True:
                with self.condition:
                    self.condition.wait_for(lambda: self.closed or self.latest is not None
                                            and self.latest[0] != self.last_fid)
                    if self.closed:
                        return
                began = time.monotonic()
                detector = self.detector_snapshot()
                snapshot_wait_ms = (time.monotonic()-began)*1000
                # A shared detector-state lock may wait behind other camera
                # work. Select the newest actual capture AFTER that wait.
                with self.condition:
                    if self.closed:
                        return
                    fid, stamp, image = self.latest
                source_age_at_start = self.clock_ms()-stamp
                if 0 <= source_age_at_start < MEASUREMENT_MAX_AGE_MS:
                    value, reason = self.measure(image, fid, stamp, detector)
                else:
                    self.last_fid, self.last_stamp = fid, stamp
                    value, reason = None, 'CURRENT_IMAGE_EXPIRED'
                finished = self.clock_ms()
                source_age_at_finish = finished-stamp
                if value is not None and not 0 <= source_age_at_finish < MEASUREMENT_MAX_AGE_MS:
                    value, reason = None, 'CURRENT_IMAGE_EXPIRED'
                with self.condition:
                    self.value = value
                    self.processed += 1
                    self.reason = reason
                    self.elapsed_ms = round((time.monotonic()-began)*1000, 3)
                    self.snapshot_wait_ms = round(snapshot_wait_ms, 3)
                    self.source_age_at_start_ms = source_age_at_start
                    self.source_age_at_finish_ms = source_age_at_finish
                    self.process_source_gap_ms = None if self.last_process_stamp is None else stamp-self.last_process_stamp
                    self.process_finish_gap_ms = None if self.last_process_finish is None else finished-self.last_process_finish
                    self.maximum_process_source_gap_ms = max(self.maximum_process_source_gap_ms, self.process_source_gap_ms or 0)
                    self.maximum_process_finish_gap_ms = max(self.maximum_process_finish_gap_ms, self.process_finish_gap_ms or 0)
                    self.last_process_stamp, self.last_process_finish = stamp, finished
                    self.result_reasons[reason] += 1
                    self.last_detector_frame_id=detector['fid']
                    self.last_detector_source_age_ms=finished-detector['stamp'] if detector['stamp'] is not None else None
                    if value is not None:
                        self.valid_measurements += 1
                        if self.last_valid_source_stamp is not None:
                            self.maximum_valid_source_gap_ms=max(self.maximum_valid_source_gap_ms,
                                                                  stamp-self.last_valid_source_stamp)
                            self.maximum_valid_finish_gap_ms=max(self.maximum_valid_finish_gap_ms,
                                                                  finished-self.last_valid_finished)
                        self.last_valid_source_stamp,self.last_valid_finished=stamp,finished
                with self.face._edge_signal:
                    self.face._edge_revision += 1
                    self.face._edge_signal.notify_all()
        except BaseException as exc:
            with self.condition:
                self.value = None
                self.error = type(exc).__name__+': '+str(exc)[:100]
