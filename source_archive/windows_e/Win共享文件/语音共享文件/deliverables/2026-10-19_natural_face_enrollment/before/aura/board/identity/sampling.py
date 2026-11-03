"""Bounded RAM-only enrollment; ten selection frames and five held-out frames."""
import copy
import math
import uuid


COUNTS = {'front': 4, 'left': 3, 'right': 3, 'validate': 5}
GUIDES = {'front': '请正对镜头', 'left': '请轻微向左转头，双眼保持可见',
          'right': '请轻微向右转头，双眼保持可见', 'validate': '请回到正脸，正在用新画面验证',
          'ready': '新画面验证通过，可以确认称呼后保存', 'failed': '采样或验证未通过，请重新采样'}


def pose_quality(face, blur):
    """Five-landmark geometric guide, not a calibrated head-pose model."""
    ex, ey = face[6]-face[4], face[7]-face[5]
    distance = math.hypot(ex, ey)
    if distance < 1:
        return None
    yaw = ((face[8]-(face[4]+face[6])/2)*ex + (face[9]-(face[5]+face[7])/2)*ey)/(distance*distance)
    return {'yaw': yaw, 'roll': math.degrees(math.atan2(ey, ex)),
            'pixels': min(face[2:4]), 'eye_distance': distance, 'blur': blur}


class EnrollmentSampling:
    def __init__(self, threshold, ambiguity_margin, clock):
        self.threshold, self.margin, self.clock = threshold, ambiguity_margin, clock
        self.reset()

    def reset(self):
        self.stage = 'idle'; self.session_id = ''; self.owner = None; self.revision = None
        self.started = self.until = 0; self.last_fid = self.last_stamp = -1
        self.counts = {key: 0 for key in COUNTS}; self.training = []; self.candidate = None
        self.baseline = 0.; self.detail = ''; self.validation_scores = []
        self.replace_id = ''

    def start(self, owner, revision, replace_id=''):
        self.reset(); self.session_id = uuid.uuid4().hex; self.owner = copy.deepcopy(owner)
        self.revision = revision; self.stage = 'front'; self.started = self.clock(); self.until = self.started+90000
        self.replace_id = replace_id

    def fail(self, detail):
        self.stage = 'failed'; self.detail = detail
        self.training = []; self.candidate = None; self.validation_scores = []

    def check(self, owner, revision):
        if self.stage not in ('idle', 'failed'):
            if owner != self.owner or revision != self.revision:
                self.fail('对象或身份库已变化，请重新采样')
            elif self.clock() >= self.until:
                self.fail('采样或确认已超时，请重新采样')

    def public(self):
        phase = self.stage
        return {'session_id': self.session_id, 'stage': phase, 'counts': dict(self.counts),
                'total': sum(self.counts.values()), 'total_required': 15,
                'detail': self.detail or GUIDES.get(phase, '等待开始人脸采样')}

    def usable(self, vector, existing_best):
        if self.candidate is None:
            return False
        score = sum(a*b for a,b in zip(vector,self.candidate['embedding']))
        return score >= self.threshold and (existing_best is None or score-existing_best >= self.margin)

    def offer(self, result, quality, existing_best):
        self.check(result['target'], result['revision'])
        if self.stage not in COUNTS or quality is None:
            return
        fid, stamp = result['fid'], result['stamp']
        if fid <= self.last_fid or stamp < self.started or stamp-self.last_stamp < 500:
            return
        if (not all(math.isfinite(v) for v in quality.values()) or quality['pixels'] < 72
                or quality['eye_distance'] < 18 or quality['blur'] < 40 or abs(quality['roll']) > 12):
            self.detail = '请靠近镜头并保持清晰，头不要歪斜'; return
        yaw = quality['yaw']; phase = self.stage
        delta = yaw-self.baseline
        correct = (abs(yaw) <= .18 if phase == 'front' else abs(delta) <= .055 if phase == 'validate'
                   else -.28 <= delta <= -.06 if phase == 'left' else .06 <= delta <= .28)
        if not correct:
            self.detail = GUIDES[phase]; return
        self.last_fid, self.last_stamp = fid, stamp; self.detail = ''
        if phase == 'validate':
            if not self.usable(result['embedding'], existing_best):
                self.fail('新画面验证未达到识别门槛或身份间隔，请调整取景后重新采样'); return
            self.validation_scores.append(sum(a*b for a,b in zip(result['embedding'],self.candidate['embedding'])))
        else:
            self.training.append({'embedding':result['embedding'], 'fid':fid,
                                  'stamp':stamp, 'face_png':result.get('face_png'), 'yaw':yaw})
        self.counts[phase] += 1
        if self.counts[phase] == COUNTS[phase]:
            if phase == 'front':
                self.baseline = sum(r['yaw'] for r in self.training)/4; self.stage = 'left'
            elif phase == 'left': self.stage = 'right'
            elif phase == 'right':
                # Choose an observed vector, never average/augment a template.
                def representativeness(row):
                    return sum(sum(a*b for a,b in zip(row['embedding'],other['embedding'])) for other in self.training)
                self.candidate = max(self.training, key=representativeness)
                self.training = []; self.stage = 'validate'
            else:
                self.stage = 'ready'; self.until = self.clock()+60000
