"""Face-box association and a non-actuating visual control preview.

This small IoU baseline is not ByteTrack or an identity recognizer. Predicted
boxes help association only; they never create observations or movement leases.
"""
import math


def valid_box(box, width, height):
    if len(box) != 4 or not all(math.isfinite(float(v)) for v in box):
        return None
    x, y, w, h = map(float, box)
    if w <= 0 or h <= 0:
        return None
    x1, y1 = max(0., x), max(0., y)
    x2, y2 = min(float(width), x + w), min(float(height), y + h)
    return [x1, y1, x2-x1, y2-y1] if x2 > x1 and y2 > y1 else None


def iou(a, b):
    overlap = max(0., min(a[0]+a[2], b[0]+b[2])-max(a[0], b[0])) * max(
        0., min(a[1]+a[3], b[1]+b[3])-max(a[1], b[1]))
    return overlap / max(a[2]*a[3]+b[2]*b[3]-overlap, 1e-9)


class FaceTracks:
    def __init__(self, epoch, lost_s=.5, confirm_observations=2):
        self.epoch = epoch
        self.lost_s = lost_s
        self.confirm_observations = confirm_observations
        self.tracks = {}
        self.next_id = 1
        self.target_id = None
        self.last_frame = -1
        self.last_time = None

    def update(self, faces, frame_id, observed_time, width, height):
        if width <= 0 or height <= 0 or not math.isfinite(observed_time):
            raise ValueError('Invalid frame dimensions or time')
        if frame_id <= self.last_frame or (self.last_time is not None and observed_time <= self.last_time):
            raise ValueError('Observations must advance monotonically')
        self.last_frame, self.last_time = frame_id, observed_time
        boxes = []
        for face in faces:
            box = valid_box(face[:4], width, height)
            if box is not None and len(face) >= 15 and math.isfinite(float(face[14])):
                boxes.append((box, float(face[14])))
        self.tracks = {k: t for k, t in self.tracks.items()
                       if observed_time-t['observed_time'] <= self.lost_s}
        candidates = []
        for tid, t in self.tracks.items():
            dt = observed_time-t['observed_time']
            predicted = t['box'][:]
            predicted[0] += t['velocity'][0]*dt
            predicted[1] += t['velocity'][1]*dt
            for j, (box, _) in enumerate(boxes):
                overlap = iou(predicted, box)
                if overlap >= .15:
                    candidates.append((overlap, tid, j))
        matched_tracks, matched_boxes = set(), set()
        for _, tid, j in sorted(candidates, reverse=True):
            if tid in matched_tracks or j in matched_boxes:
                continue
            t = self.tracks[tid]
            box, score = boxes[j]
            dt = observed_time-t['observed_time']
            old = t['box']
            consecutive = t['consecutive']+1 if t['visible'] else 1
            velocity = [((box[0]+box[2]/2)-(old[0]+old[2]/2))/dt,
                        ((box[1]+box[3]/2)-(old[1]+old[3]/2))/dt]
            t.update(box=box, score=score, velocity=velocity, visible=True,
                     consecutive=consecutive, confirmed=t['confirmed'] or consecutive >= self.confirm_observations,
                     observed_time=observed_time, frame_id=frame_id)
            matched_tracks.add(tid)
            matched_boxes.add(j)
        for tid, t in self.tracks.items():
            if tid not in matched_tracks:
                t['visible'] = False
                t['consecutive'] = 0
        for j, (box, score) in enumerate(boxes):
            if j in matched_boxes:
                continue
            tid = self.next_id
            self.next_id += 1
            self.tracks[tid] = {'track_id': tid, 'generation': 1, 'epoch': self.epoch,
                                'box': box, 'score': score, 'velocity': [0., 0.],
                                'visible': True, 'consecutive': 1,
                                'confirmed': self.confirm_observations <= 1,
                                'observed_time': observed_time, 'frame_id': frame_id}
        if self.target_id not in self.tracks:
            self.target_id = None
        if self.target_id is None:
            available = [t for t in self.tracks.values() if t['visible'] and t['confirmed']]
            if available:
                self.target_id = max(available, key=lambda t: (t['box'][2]*t['box'][3], -t['track_id']))['track_id']
        tracks = [dict(t, box=t['box'][:], velocity=t['velocity'][:]) for t in self.tracks.values()]
        return {'epoch': self.epoch, 'frame_id': frame_id, 'observed_time': observed_time,
                'target_id': self.target_id, 'tracks': tracks,
                'association': 'FACE_IOU_BASELINE', 'identity_recognition': False}


class ControlPreview:
    """Proportional, dt-aware calculation with no hardware access or permission."""
    def __init__(self, tau=.1, deadband=.04, kp=20., max_step=2., max_dt=.25):
        self.tau, self.deadband, self.kp = tau, deadband, kp
        self.max_step, self.max_dt = max_step, max_dt
        self.key = None
        self.last_time = None
        self.filtered = None

    def update(self, snapshot, width, now, freshness_s=.25):
        result = {'valid': False, 'motion_command_emitted': False,
                  'actuation_authorized': False, 'direction': 'LOST',
                  'raw_error': None, 'filtered_error': None, 'virtual_delta_deg': 0.}
        target = next((t for t in snapshot['tracks'] if t['track_id']==snapshot['target_id']), None)
        if target is None or not target['visible'] or not target['confirmed']:
            self.key, self.last_time, self.filtered = None, None, None
            return dict(result, reason='NO_OBSERVED_TARGET')
        age = now-target['observed_time']
        if age < 0 or age > freshness_s:
            self.key, self.last_time, self.filtered = None, None, None
            return dict(result, reason='STALE_OBSERVATION')
        box = target['box']
        error = max(-1., min(1., ((box[0]+box[2]/2)-width/2)/(width/2)))
        key = (snapshot['epoch'], target['track_id'], target['generation'])
        dt = 0. if key != self.key or self.last_time is None else target['observed_time']-self.last_time
        if key != self.key or self.filtered is None or dt > self.max_dt:
            self.filtered = error
            dt = 0.
        elif dt > 0:
            alpha = 1-math.exp(-dt/self.tau)
            self.filtered = alpha*error+(1-alpha)*self.filtered
        else:
            return dict(result, reason='NO_NEW_OBSERVATION')
        self.key, self.last_time = key, target['observed_time']
        direction = 'CENTER' if abs(self.filtered) <= self.deadband else ('RIGHT' if self.filtered > 0 else 'LEFT')
        rate = 0. if direction=='CENTER' else max(-20., min(20., self.kp*self.filtered))
        delta = max(-self.max_step, min(self.max_step, rate*dt))
        return dict(result, valid=True, reason='DRY_RUN_ONLY', direction=direction,
                    raw_error=error, filtered_error=self.filtered, virtual_delta_deg=delta,
                    observation_age_ms=age*1000, dt_s=dt)


def display_observation(snapshot, now, freshness_s=.25):
    """Fail closed in the display even when the inference thread stalls."""
    age = now-snapshot['observed_time']
    fresh = 0 <= age <= freshness_s
    target = next((t for t in snapshot['tracks'] if t['track_id']==snapshot['target_id']), None)
    visible = fresh and target is not None and target['visible'] and target['confirmed']
    return {'fresh': fresh, 'target_visible': visible, 'age_ms': age*1000,
            'state': 'TRACKING' if visible else ('LOST' if fresh else 'STALE'),
            'motion_command_emitted': False}
