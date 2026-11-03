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
        self.last_offer = self.last_offer_stamp = None
        self.last_fid = self.last_stamp = None
        self.anchor_id = self.anchor_stamp = self.anchor_key = None
        self.binding = self.template = self.box = self.score = None
        self.thread = None
        if start:
            self.thread = threading.Thread(target=self.work, name='aura-face-measure-v8', daemon=True)
            self.thread.start()

    def offer(self, image, fid, stamp):
        with self.condition:
            if (self.closed or (self.last_offer is not None and fid <= self.last_offer)
                    or (self.last_offer_stamp is not None and stamp <= self.last_offer_stamp)):
                return
            self.last_offer, self.last_offer_stamp = fid, stamp
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
                        error=self.error, version=8, anchor_max_age_ms=ANCHOR_MAX_AGE_MS)

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
        return dict(template=crop.copy(), offset=(x0-x, y0-y), method='FACE_DETECTION_ANCHOR')

    @staticmethod
    def step(previous, current, state, box):
        import cv2
        import numpy as np
        if state is None:
            return None
        x, y, w, h = box
        template = state['template']
        ox, oy = state['offset']
        radius = min(64, max(16, int(max(w, h)*.6)))
        tx, ty = int(x+ox), int(y+oy)
        x0, y0 = max(0, tx-radius), max(0, ty-radius)
        search = current[y0:min(current.shape[0], ty+template.shape[0]+radius),
                         x0:min(current.shape[1], tx+template.shape[1]+radius)]
        if search.shape[0] < template.shape[0] or search.shape[1] < template.shape[1]:
            return None
        _, score, _, loc = cv2.minMaxLoc(cv2.matchTemplate(search, template, cv2.TM_CCOEFF_NORMED))
        if not np.isfinite(score) or score < .80:
            return None
        updated = [float(x0+loc[0]-ox), float(y0+loc[1]-oy), float(w), float(h)]
        if FaceFlow.clipped(updated, current.shape) is None:
            return None
        # Keep the actual detector-anchor template fixed. Repeated self-reseeding
        # must not let a briefly occluding object gradually replace the face.
        refreshed = dict(state, method='FACE_TEMPLATE_VISIBLE_CLIP', match_score=float(score))
        return updated, refreshed

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
                continuity = self.step(None, seed_gray, old_template, old_box)
            preserve = continuity is not None and self.same_face(continuity[0], detector['box'])
            self.binding = dict(old_binding if preserve else detector['key'])
            self.anchor_id, self.anchor_stamp = detector['fid'], detector['stamp']
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
                    match_score=self.template.get('match_score')), self.template['method']

    def work(self):
        try:
            while True:
                with self.condition:
                    self.condition.wait_for(lambda: self.closed or self.latest is not None
                                            and self.latest[0] != self.last_fid)
                    if self.closed:
                        return
                    fid, stamp, image = self.latest
                began = time.monotonic()
                value, reason = self.measure(image, fid, stamp, self.detector_snapshot())
                with self.condition:
                    self.value = value
                    self.processed += 1
                    self.reason = reason
                    self.elapsed_ms = round((time.monotonic()-began)*1000, 3)
                with self.face._edge_signal:
                    self.face._edge_revision += 1
                    self.face._edge_signal.notify_all()
        except BaseException as exc:
            with self.condition:
                self.value = None
                self.error = type(exc).__name__+': '+str(exc)[:100]
