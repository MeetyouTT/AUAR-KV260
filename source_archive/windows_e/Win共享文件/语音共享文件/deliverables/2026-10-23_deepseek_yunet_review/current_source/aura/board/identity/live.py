"""Selected-target identity, with one CPU worker and no camera ownership.

Embedding candidates stay in RAM; opted-in enrollment photos have a separate
face-only archive. Only explicit enrollment writes a model-specific template.
The owner supplies the camera lock and target check
so a changed target cannot race a transaction or resurrect a late result.
"""
import copy
import threading
import time
import uuid

from board.interaction.ui_contract import millis, target_key, text
from board.identity.store import normalize
from board.identity.deferred import DeferredIdentity


class IdentityService:
    def __init__(self, store, extractor_factory, current_target, *, lock=None,
                 clock=millis, result_ttl_ms=1500, interval_ms=500, max_people=32, multi_frame=False,
                 backend='CPU_SFACE_REFERENCE',photo_archive=None):
        if not 100 <= result_ttl_ms <= 5000 or not 100 <= interval_ms <= 5000 or not 1 <= max_people <= 32:
            raise ValueError('Invalid identity service limits')
        self.store, self.extractor_factory, self.current_target = store, extractor_factory, current_target
        self.lock = lock or threading.RLock()
        self.clock, self.ttl, self.interval, self.max_people = clock, result_ttl_ms, interval_ms, max_people
        self.condition = threading.Condition(self.lock)
        self.pending = self.result = None
        self.error = self.reason = ''
        self.ready = False
        self.closed = False
        self.thread = None
        self.last_operation = None
        self.processed = self.discarded = 0
        self.match_counts={'KNOWN':0,'UNKNOWN':0,'AMBIGUOUS':0}
        self.deferred = 0
        self.last_ms = None
        self.face_targets = None
        self.extractor = None
        self.shutdown_incomplete = False
        self.backend=backend
        self.photo_archive=photo_archive
        from board.identity.sampling import EnrollmentSampling
        self.sampling = EnrollmentSampling(store.threshold, store.ambiguity_margin, clock,photo_archive) if multi_frame else None

    def sample_start(self, params, command_id):
        with self.lock:
            key=target_key(params['target'])
            if not self.sampling or not self._fresh(self.result) or key!=self.current_target():
                raise ValueError('请先正对镜头，等待清晰人脸')
            if self.result['match'].state!='UNKNOWN':raise ValueError('当前身份已识别或有歧义，请先核对')
            if self.sampling.stage not in ('idle','failed'):
                raise ValueError('请先完成或取消当前采样')
            replace=params.get('replace_person_id','')
            if replace and (params.get('db_version')!=self.store.revision or
                    replace not in [r['person_id'] for r in self.store.people()]):
                raise ValueError('待更新身份已变化，请重新核对')
            self.sampling.start(key,self.store.revision,replace,anchor=self.result['embedding'])
            return '已开始人脸采样，请正对镜头'

    def sample_cancel(self, params, command_id):
        with self.lock:
            if self.sampling and self.sampling.session_id==params['session_id']:
                self.sampling.reset()
            return '人脸采样已结束，未保存身份'

    def _sampling_check(self):
        if self.sampling:
            if (self.face_targets and self.face_targets.view()['face_count']>1
                    and self.sampling.stage not in ('idle','failed')):
                self.sampling.fail('检测到多张人脸，已停止采样，请只保留登记者')
            self.sampling.check(self.current_target(),self.store.revision)

    def start(self):
        with self.lock:
            if self.thread is not None or self.closed:
                raise RuntimeError('Identity worker cannot be started twice')
            self.thread = threading.Thread(target=self.work, name='camera-identity', daemon=True)
            self.thread.start()

    def offer(self, image, fid, stamp, observation, camera_epoch):
        """Latest-only slot, sharing the immutable capture frame with detection."""
        with self.condition:
            selected = observation.get('target_id')
            track = next((t for t in observation['tracks'] if t['track_id'] == selected
                          and t['visible'] and t['confirmed']), None)
            if track is None:
                self.pending = self.result = None
                return
            key = {'camera_epoch': camera_epoch, 'track_id': selected, 'track_generation': track['generation']}
            self.pending = (image, fid, stamp, copy.deepcopy(observation), key)
            self.condition.notify()

    def offer_face(self,image,face,fid,stamp,key):
        # FaceTargetService invokes this after releasing state.lock. The
        # extractor is published only after its auxiliary objects are bound.
        extractor = self.extractor
        producer = getattr(extractor, 'producer', None) if extractor is not None else None
        if producer is not None:
            try:
                producer.offer_face(image,face,fid,stamp,key)
            except Exception:
                # Auxiliary delivery must not change Windows pending/results.
                pass
        with self.condition:
            if face is None or key is None:
                self.pending=self.result=None;return
            observation={'target_kind':'face','face':tuple(face),'face_target':copy.deepcopy(key),
                         'frame_id':fid,'captured_mono_ms':stamp}
            self.pending=(image,fid,stamp,observation,copy.deepcopy(key));self.condition.notify()

    def _fresh(self, result):
        return bool(result and result['target'] == self.current_target()
                    and 0 <= self.clock()-result['stamp'] < self.ttl
                    and result['revision'] == self.store.revision)

    def view(self):
        with self.lock:
            people = self.store.people()
            value = {'state': 'ERROR' if self.error else 'UNKNOWN', 'person_id': '', 'display_name': '',
                     'db_version': self.store.revision, 'people': people, 'backend': self.backend,
                     'detail': self.error or ('身份模型正在加载' if not self.ready else '请先选择一个当前对象')}
            current = self.current_target()
            self._sampling_check()
            if self.face_targets:
                value.update(self.face_targets.view())
                detector=self.face_targets.health()
                if detector['error']:value.update(state='ERROR',detail=detector['error'])
                elif not detector['ready']:value['detail']='人脸检测模型正在加载'
                elif value['face_count']>1:value['detail']='检测到多张人脸，请只保留登记者正对镜头'
                elif not current:value['detail']='请正对摄像头，等待人脸目标确认'
            if self.ready and current:
                value['detail'] = self.reason or '等待当前对象的清晰正面人脸'
            result = self.result
            fresh = self.ready and not self.error and self._fresh(result)
            if fresh:
                match = result['match']
                value.update(state='KNOWN' if match.state == 'KNOWN' else 'UNKNOWN',
                             person_id=match.identity_id, display_name=match.name,
                             detail=('DPU 本地识别 · ' if self.backend == 'DPU_SFACE_INT8' else 'CPU 参考识别 · ')+match.name if match.state == 'KNOWN' else
                             '匹配存在歧义，请重新面对摄像头' if match.state == 'AMBIGUOUS' else '未登记 / UNKNOWN',
                             source_frame_id=result['fid'], source_mono_ms=result['stamp'],
                             target=copy.deepcopy(result['target']))
                if result.get('face_png'):
                    value['face_preview'] = {'target':copy.deepcopy(result['target']),
                        'frame_id':result['fid'], 'captured_mono_ms':result['stamp'], 'ttl_ms':self.ttl}
            elif result and current and not self.error:
                value['detail'] = '身份结果已过期，等待新的人脸'
            if self.last_operation:
                value['last_operation'] = copy.deepcopy(self.last_operation)
            can_enroll = bool(fresh and result['match'].state == 'UNKNOWN' and len(people) < self.max_people)
            can_sample=bool(fresh and result['match'].state=='UNKNOWN')
            if self.sampling:
                value['enrollment_sampling']=self.sampling.public()
                can_enroll=bool(can_sample and (len(people)<self.max_people or self.sampling.replace_id)
                    and self.sampling.stage=='ready'
                    and self.sampling.authorizes(current)
                    and self.sampling.usable(result['embedding'],self.store.best_other_score(result['embedding'],self.sampling.replace_id)))
            return value, {'identity_enroll': can_enroll, 'identity_delete': bool(people),
                'identity_sample_start':bool(self.sampling and can_sample and self.sampling.stage in ('idle','failed')),
                'identity_sample_cancel':bool(self.sampling and self.sampling.session_id)}

    def face_preview(self, target, fid):
        """Only the current qualified model-input crop; never a whole frame."""
        with self.lock:
            result = self.result
            if (not self.ready or self.error or not self._fresh(result)
                    or result['target'] != target or result['fid'] != fid):
                return None
            return result.get('face_png')

    def enroll(self, params, command_id):
        with self.lock:
            key = target_key(params['target'])
            name = params['display_name'].strip()
            if params.get('confirmed') is not True or not text(name, 48, False):
                raise ValueError('登记需要明确确认和有效名称')
            result = self.result
            if not self.ready or self.error or not self._fresh(result) or result['target'] != key:
                raise ValueError('目标或合格人脸已变化，请重新确认后登记')
            if result['match'].state != 'UNKNOWN':
                raise ValueError('当前对象已登记或匹配有歧义，请先核对身份')
            vector=result['embedding']
            replace=params.get('replace_person_id','')
            people=self.store.people()
            if replace and (params.get('db_version')!=self.store.revision or
                    not any(r['person_id']==replace and r['display_name'].casefold()==name.casefold() for r in people)):
                raise ValueError('待更新身份或称呼已变化，请重新核对')
            if self.sampling:
                self._sampling_check()
                if ('sampling_session_id' in params and params['sampling_session_id']!=self.sampling.session_id):
                    raise ValueError('待保存的采样会话已变化')
                if (self.sampling.stage!='ready' or not self.sampling.authorizes(key)
                        or self.sampling.replace_id!=replace or not self.sampling.usable(vector,
                        self.store.best_other_score(vector,replace))):
                    raise ValueError('人脸采样或独立新画面验证尚未通过')
                vector=self.sampling.candidate['embedding']
                match=self.store.match(vector)
                if match.state!='UNKNOWN' and match.identity_id!=replace:raise ValueError('候选模板已对应现有身份，请先核对')
            if any(p['display_name'].casefold() == name.casefold() and p['person_id']!=replace for p in people):
                raise ValueError('该称呼已存在，请使用不同称呼')
            self.store.enroll(replace or uuid.uuid4().hex, name, vector, consent=True,
                              expected_revision=result['revision'], max_people=self.max_people)
            result['revision'] = self.store.revision
            result['match'] = self.store.match(result['embedding'])
            detail = ('已更新登记“' if replace else '已登记“')+name+'”'
            self.last_operation = {'command_id': command_id, 'action': 'identity_enroll',
                                   'state': 'COMMITTED', 'detail': detail, 'db_version': self.store.revision}
            if self.sampling:self.sampling.reset(outcome='committed',revision=self.store.revision)
            return detail

    def delete(self, params, command_id):
        with self.lock:
            if params.get('confirmed') is not True:
                raise ValueError('删除需要明确确认')
            if not self.store.delete(params['person_id'], expected_revision=params['db_version']):
                raise ValueError('该身份已删除，请刷新状态')
            # Invalidate every cached template/result, including an in-flight job.
            self.result = self.pending = None
            if self.sampling:self.sampling.reset()
            self.reason = '身份已删除，等待重新识别'
            self.last_operation = {'command_id': command_id, 'action': 'identity_delete',
                                   'state': 'COMMITTED', 'detail': '身份已删除', 'db_version': self.store.revision}
            return '身份已删除'

    def process(self, packet, extractor):
        image, fid, stamp, observation, key = packet
        with self.lock:
            if key != self.current_target() or not 0 <= self.clock()-stamp < self.ttl:
                self.discarded += 1
                return
            revision = self.store.revision
        started = time.monotonic()
        try:
            embedding, reason = extractor.extract(image, observation, key)
            vector = None if embedding is None else normalize(embedding, self.store.dimension)
            reason = str(reason)[:120]
        except DeferredIdentity:
            with self.lock:
                self.last_ms = round((time.monotonic()-started)*1000, 2)
                self.discarded += 1
                self.deferred += 1
            # No recognition decision was computed. Keep the previous result
            # and sampling state; view()/enroll() still enforce its original TTL.
            return
        except Exception as exc:
            vector, reason = None, '身份识别失败：'+str(exc)[:100]
        with self.lock:
            self.last_ms = round((time.monotonic()-started)*1000, 2)
            if (self.closed or key != self.current_target() or not 0 <= self.clock()-stamp < self.ttl
                    or revision != self.store.revision):
                self.discarded += 1
                return
            self.processed += 1
            self.reason, self.result = reason, None
            if vector is not None:
                preview = getattr(extractor, 'preview_png', None)
                if not isinstance(preview, bytes) or not preview.startswith(b'\x89PNG\r\n\x1a\n') or len(preview)>65536:
                    preview = None
                self.result = {'target': key, 'fid': fid, 'stamp': stamp, 'embedding': vector,
                               'revision': revision, 'match': self.store.match(vector), 'face_png':preview}
                self.match_counts[self.result['match'].state]+=1
                if self.sampling:
                    self.sampling.offer(self.result,getattr(extractor,'enrollment_quality',None),
                        self.store.best_other_score(vector,self.sampling.replace_id))

    def work(self):
        extractor = None
        try:
            extractor = self.extractor_factory()
            with self.lock:
                self.extractor = extractor
                self.ready = True
            next_at = 0
            while True:
                with self.condition:
                    self.condition.wait_for(lambda: self.closed or self.pending is not None)
                    if self.closed:
                        return
                    delay = max(0, next_at-time.monotonic())
                    if delay:
                        self.condition.wait(delay)
                        continue
                    packet, self.pending = self.pending, None
                self.process(packet, extractor)
                next_at = time.monotonic()+self.interval/1000
        except Exception as exc:
            with self.lock:
                self.error = '身份服务不可用：'+str(exc)[:100]
                self.result = self.pending = None
        finally:
            if extractor is not None and callable(getattr(extractor, 'close', None)):
                try:
                    if extractor.close() is False:
                        with self.lock:self.shutdown_incomplete = True
                except Exception as exc:
                    with self.lock:
                        self.shutdown_incomplete = True
                        self.error = '身份模型关闭失败：'+str(exc)[:100]

    def health(self):
        with self.lock:
            face=self.face_targets.health() if self.face_targets else None
            return {'ready': self.ready and not self.error and (not face or face['ready']),
                    'error': self.error or (face['error'] if face else ''), 'face_targets':face,
                    'backend': self.backend, 'processed': self.processed,
                    'shutdown_incomplete':self.shutdown_incomplete,
                    'feature_inference': self.extractor.health() if self.extractor is not None
                        and callable(getattr(self.extractor, 'health', None)) else None,
                    'enrollment_photos':self.photo_archive.health() if self.photo_archive else {'enabled':False},
                    'sampling_diagnostics':None if not self.sampling else {
                        'stage':self.sampling.stage,'pool_frames':len(self.sampling.training),
                        'template_policy':self.sampling.policy,
                        'last_failure':copy.deepcopy(self.sampling.last_failure),'metrics':copy.deepcopy(self.sampling.metrics)},
                    'discarded': self.discarded, 'deferred': self.deferred,
                    'model_id': self.store.model_id, 'last_inference_ms': self.last_ms,
                    'match_diagnostics':{'counts':dict(self.match_counts),
                        'last_state':self.result['match'].state if self.result else None,
                        'last_score':float(self.result['match'].score) if self.result else None},
                    'pending_frames': int(self.pending is not None)}

    def close(self):
        if self.face_targets:self.face_targets.close()
        with self.condition:
            self.closed = True
            if self.sampling:self.sampling.reset()
            self.pending = self.result = None
            self.condition.notify_all()
        if self.thread:
            self.thread.join(5)
            if self.thread.is_alive():
                raise RuntimeError('Identity worker did not stop; database remains open')
        with self.lock:
            if self.shutdown_incomplete:
                ready = getattr(self.extractor, 'shutdown_ready', None)
                if not callable(ready) or not ready():
                    raise RuntimeError('Shadow inference has not stopped; keep the shared DPU owner open')
                self.shutdown_incomplete = False
            self.store.close()
