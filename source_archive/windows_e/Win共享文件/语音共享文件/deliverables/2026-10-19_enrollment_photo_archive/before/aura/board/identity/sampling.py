"""Natural-motion enrollment: a bounded video window and held-out validation."""
import copy
import math
import uuid


COUNTS = {'collect': 10, 'validate': 5}
COLLECTION_MS = 15000
MAX_POOL = 24
FRONT_YAW_MAX = .22
FRONT_ROLL_MAX = 15.
MIN_FRONT_FRAMES = 3
GUIDES = {'collect': '请看着镜头慢慢自然转头，正在自动挑选清晰人脸',
          'validate': '选样完成，请自然看向镜头，正在用新画面验证',
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
    policy = 'frontal_medoid_v1'
    def __init__(self, threshold, ambiguity_margin, clock):
        self.threshold, self.margin, self.clock = threshold, ambiguity_margin, clock
        self.reset()

    def reset(self):
        self.last_failure = getattr(self,'last_failure',None)
        self.stage = 'idle'; self.session_id = ''; self.owner = None; self.revision = None
        self.started = self.until = 0; self.last_fid = self.last_stamp = -1
        self.counts = {key: 0 for key in COUNTS}; self.training = []; self.candidate = None
        self.detail = ''; self.validation_scores = []; self.missing_since = None
        self.replace_id = ''
        self.anchor = None
        self.metrics={'quality_skips':0,'recovery_rejections':0,'validation_attempts':0,
                      'validation_passes':0,'score_rejections':0,'margin_rejections':0,'best_validation_run':0,
                      'recent_validation':[],'front_pose_skips':0,'candidate_pose':None}

    def start(self, owner, revision, replace_id='', anchor=None):
        self.reset(); self.session_id = uuid.uuid4().hex; self.owner = copy.deepcopy(owner)
        self.last_failure = None
        self.revision = revision; self.stage = 'collect'; self.started = self.clock(); self.until = self.started+90000
        self.replace_id = replace_id
        self.anchor = anchor

    def fail(self, detail):
        self.stage = 'failed'; self.detail = detail
        self.last_failure = {'detail':detail,'counts':dict(self.counts),'at_mono_ms':self.clock(),
                             'metrics':copy.deepcopy(self.metrics)}
        self.training = []; self.candidate = None; self.validation_scores = []
        self.anchor = None

    def check(self, owner, revision):
        if self.stage not in ('idle', 'failed'):
            if revision != self.revision or (owner is not None
                    and owner['camera_epoch'] != self.owner['camera_epoch']):
                self.fail('对象或身份库已变化，请重新采样')
            elif self.clock() >= self.until:
                self.fail('采样或确认已超时，请重新采样')
            elif owner != self.owner:
                if self.missing_since is None:self.missing_since = self.clock()
            else:
                self.missing_since = None

    def public(self):
        phase = self.stage
        return {'session_id': self.session_id, 'stage': phase, 'counts': dict(self.counts),
                'bound_target':copy.deepcopy(self.owner) if phase not in ('idle','failed') else None,
                'total': sum(self.counts.values()), 'total_required': 15,
                'detail': ('选样已保留，请看向镜头，等待同一张清晰人脸' if self.missing_since is not None
                           and phase not in ('idle','failed') else
                           self.detail or GUIDES.get(phase, '等待开始人脸采样'))}

    def authorizes(self, owner):
        return owner is not None and owner == self.owner and self.missing_since is None

    def usable(self, vector, existing_best):
        if self.candidate is None:
            return False
        score = sum(a*b for a,b in zip(vector,self.candidate['embedding']))
        return score >= self.threshold and (existing_best is None or score-existing_best >= self.margin)

    @staticmethod
    def frontal(pose):
        # This ratio is a five-landmark hint, not a calibrated angle. Natural
        # side views can be collected, but cannot certify a frontal template.
        return abs(pose['yaw'])<=FRONT_YAW_MAX and abs(pose['roll'])<=FRONT_ROLL_MAX

    def _keep(self,result,quality):
        self.training.append({'embedding':result['embedding'],'fid':result['fid'],
            'stamp':result['stamp'],'face_png':result.get('face_png'),
            'pose':dict(quality),'quality':min(quality['blur'],400.)+min(quality['pixels'],240.)})
        if len(self.training)>MAX_POOL:
            # A long, sharp profile must not evict the earlier usable front.
            self.training.remove(min(self.training,key=lambda row:(self.frontal(row['pose']),row['quality'])))

    def _choose_front(self):
        front=[row for row in self.training if self.frontal(row['pose'])]
        if len(front)<MIN_FRONT_FRAMES:return False
        # Limit the representative vote to the most frontal observed faces;
        # time spent turned sideways must not dominate the saved template.
        front=sorted(front,key=lambda row:(abs(row['pose']['yaw']),abs(row['pose']['roll']),-row['quality']))[:5]
        def representative(row):
            return (sum(sum(a*b for a,b in zip(row['embedding'],other['embedding'])) for other in front),
                    row['quality'])
        self.candidate=max(front,key=representative)
        self.metrics['candidate_pose']={k:round(float(v),4) for k,v in self.candidate['pose'].items()}
        self.training=[]
        return True

    def offer(self, result, quality, existing_best):
        self.check(result['target'], result['revision'])
        if self.stage not in (*COUNTS,'ready') or quality is None:
            return
        fid, stamp = result['fid'], result['stamp']
        if fid <= self.last_fid or stamp < self.started or stamp-self.last_stamp < 500:
            return
        if (not all(math.isfinite(v) for v in quality.values()) or quality['pixels'] < 72
                or quality['eye_distance'] < 18 or quality['blur'] < 40 or abs(quality['roll']) > 20
                or abs(quality['yaw']) > .38):
            self.metrics['quality_skips']+=1
            self.detail = '这帧已跳过，请慢慢转头、双眼朝向镜头并保持清晰'; return
        if result['target'] != self.owner:
            # Recovered detector tracks are not proof of the same person. Bind
            # one only after a fresh, qualified SFace observation matches the
            # ORIGINAL session anchor, with the unchanged identity threshold
            # and gallery margin. Never chain successively changing anchors.
            score = None if self.anchor is None else sum(a*b for a,b in zip(result['embedding'],self.anchor))
            if score is None or score < self.threshold or (existing_best is not None and score-existing_best < self.margin):
                self.metrics['recovery_rejections']+=1
                self.detail = '选样已保留，请看向镜头，正在核对是否同一人'; return
            self.owner = copy.deepcopy(result['target']); self.missing_since = None
        if self.anchor is None:self.anchor = result['embedding']
        if self.stage=='ready':return
        phase = self.stage
        self.last_fid, self.last_stamp = fid, stamp; self.detail = ''
        if phase == 'validate':
            if not self.frontal(quality):
                self.metrics['front_pose_skips']+=1
                self.validation_scores=[];self.counts['validate']=0
                self.detail='请自然看向镜头稍停，正在等待清晰正脸验证';return
            if self.candidate is None:
                # The transition already triggers the existing spoken cue.
                # If the video window contained only profiles, gather fronts
                # now, then require FIVE LATER frames; never count selection
                # frames as their own held-out validation.
                self._keep(result,quality);self._choose_front()
                self.detail='正在补充清晰正脸，请继续看向镜头稍停';return
            score=sum(a*b for a,b in zip(result['embedding'],self.candidate['embedding']))
            gap=None if existing_best is None else score-existing_best
            self.metrics['validation_attempts']+=1
            self.metrics['recent_validation'].append({'frame_id':fid,'score':round(score,6),
                'other_identity_gap':None if gap is None else round(gap,6)})
            self.metrics['recent_validation']=self.metrics['recent_validation'][-24:]
            if not self.usable(result['embedding'], existing_best):
                self.metrics['score_rejections']+=int(score<self.threshold)
                self.metrics['margin_rejections']+=int(gap is not None and gap<self.margin)
                # Require a new consecutive run; a poor frame never erases the
                # selection window, lowers the threshold, or counts as a pass.
                self.validation_scores = []; self.counts['validate'] = 0
                self.detail = '这一帧验证不足，已保留选样；请看向镜头稍停，正在继续验证'; return
            self.validation_scores.append(sum(a*b for a,b in zip(result['embedding'],self.candidate['embedding'])))
            self.metrics['validation_passes']+=1
        else:
            self._keep(result,quality)
        self.counts[phase] = min(COUNTS[phase], self.counts[phase]+1)
        self.metrics['best_validation_run']=max(self.metrics['best_validation_run'],self.counts['validate'])
        if self.counts[phase] == COUNTS[phase]:
            if phase == 'collect':
                if stamp-self.started < COLLECTION_MS:
                    self.detail = '已收集清晰人脸，请继续慢慢自然转头，正在完成视频选样'; return
                self._choose_front()
                if self.candidate is None:self.training=[row for row in self.training if self.frontal(row['pose'])]
                self.stage = 'validate'
            else:
                self.stage = 'ready'; self.until = self.clock()+60000
