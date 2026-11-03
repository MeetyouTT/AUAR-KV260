"""Selected-target identity, with one CPU worker and no camera ownership.

Image/embedding candidates stay in RAM. Only explicit enrollment writes a
model-specific template. The owner supplies the camera lock and target check
so a changed target cannot race a transaction or resurrect a late result.
"""
import copy
from collections import deque
import sqlite3
import threading
import time
import uuid

from board.interaction.ui_contract import millis, target_key, text
from board.identity.store import normalize


class IdentityService:
    def __init__(self, store, extractor_factory, current_target, *, lock=None,
                 clock=millis, result_ttl_ms=1500, interval_ms=500, max_people=32,
                 enrollment_target=None, enrollment_samples=5, enrollment_timeout_ms=15000):
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
        self.last_ms = None
        if not 3 <= enrollment_samples <= 12 or not 3000 <= enrollment_timeout_ms <= 30000:
            raise ValueError('Invalid enrollment limits')
        self.enrollment_target = enrollment_target or current_target
        self.enrollment_samples, self.enrollment_timeout = enrollment_samples, enrollment_timeout_ms
        self.enrollment = None
        self.cancelled_enrollments = deque(maxlen=128)

    def _finish_enrollment(self, state, detail):
        job = self.enrollment
        if job is None:
            return
        self.last_operation = {'command_id': job['command_id'], 'action': 'identity_collect',
                               'state': state, 'detail': detail, 'db_version': self.store.revision}
        self.enrollment = None  # Drop all transient vectors and crop digests.

    def _check_enrollment(self):
        job = self.enrollment
        if job is None:
            return
        if self.clock() >= job['deadline']:
            self._finish_enrollment('FAILED', '采样超时，请正对摄像头重新登记')
        elif (self.closed or self.error or job['target'] != self.enrollment_target()
              or job['revision'] != self.store.revision):
            self._finish_enrollment('FAILED', '人物、相机或身份库已变化，登记中止')

    def begin_enrollment(self, params, command_id):
        with self.lock:
            self._check_enrollment()
            name, key = params['display_name'].strip(), target_key(params['target'])
            if command_id in self.cancelled_enrollments:
                raise ValueError('该登记请求已取消')
            if params.get('confirmed') is not True or not text(name, 48, False):
                raise ValueError('登记需要明确确认和有效名称')
            if self.enrollment:
                raise ValueError('已有登记正在采样，请先完成或取消')
            result = self.result
            if (not self.ready or self.error or not self._fresh(result)
                    or result['target'] != key or self.enrollment_target() != key):
                raise ValueError('请让登记者单独面对摄像头并等待清晰人脸')
            if result['match'].state != 'UNKNOWN':
                raise ValueError('当前对象已登记或匹配有歧义，请先核对身份')
            if len(self.store.people()) >= self.max_people:
                raise ValueError('身份库已满')
            if any(p['display_name'].casefold() == name.casefold() for p in self.store.people()):
                raise ValueError('该称呼已存在，请使用不同称呼')
            self.enrollment = {'command_id': command_id, 'target': key, 'name': name,
                'revision': self.store.revision, 'deadline': self.clock()+self.enrollment_timeout,
                'start_fid': result['fid'], 'last_fid': result['fid'], 'last_stamp': result['stamp'],
                'vectors': [], 'signatures': set()}
            self.last_operation = {'command_id': command_id, 'action': 'identity_collect',
                'state': 'COLLECTING', 'detail': '正在采样，请正对摄像头并轻微转头',
                'db_version': self.store.revision}
            return self.last_operation['detail']

    def cancel_enrollment(self, params):
        with self.lock:
            cid = params['enrollment_id']
            self.cancelled_enrollments.append(cid)
            if self.enrollment and cid == self.enrollment['command_id']:
                self._finish_enrollment('CANCELLED', '登记已取消，未保存身份')
                return '登记已取消，未保存身份'
            if self.last_operation and self.last_operation['command_id'] == cid:
                return self.last_operation['detail']
            return '该登记请求已撤销'

    def _sample_enrollment(self, result, signature):
        self._check_enrollment()
        job = self.enrollment
        if job is None:
            return
        if (result['fid'] <= job['last_fid'] or result['stamp']-job['last_stamp'] < 400
                or not signature or signature in job['signatures']):
            return
        vector = result['embedding']
        if result['match'].state != 'UNKNOWN' or (job['vectors'] and
                sum(a*b for a,b in zip(job['vectors'][0], vector)) < .8):
            self._finish_enrollment('FAILED', '多帧人脸不一致或匹配有歧义，请重新登记')
            return
        job['vectors'].append(vector)
        job['signatures'].add(signature)
        job['last_fid'], job['last_stamp'] = result['fid'], result['stamp']
        if len(job['vectors']) < self.enrollment_samples:
            return
        try:
            vector = normalize(tuple(sum(row[i] for row in job['vectors']) for i in range(self.store.dimension)),
                               self.store.dimension)
            self.store.enroll(uuid.uuid4().hex, job['name'], vector, consent=True,
                              expected_revision=job['revision'], max_people=self.max_people)
        except (ValueError, sqlite3.Error) as exc:
            self._finish_enrollment('FAILED', ('登记未保存：'+str(exc))[:160])
            return
        name = job['name']
        self._finish_enrollment('COMMITTED', '已登记“'+name+'”')
        result['revision'] = self.store.revision
        result['match'] = self.store.match(result['embedding'])

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

    def _fresh(self, result):
        return bool(result and result['target'] == self.current_target()
                    and 0 <= self.clock()-result['stamp'] < self.ttl
                    and result['revision'] == self.store.revision)

    def view(self):
        with self.lock:
            self._check_enrollment()
            people = self.store.people()
            value = {'state': 'ERROR' if self.error else 'UNKNOWN', 'person_id': '', 'display_name': '',
                     'db_version': self.store.revision, 'people': people, 'backend': 'CPU_SFACE_REFERENCE',
                     'detail': self.error or ('身份模型正在加载' if not self.ready else '请先选择一个当前对象')}
            current = self.current_target()
            if self.ready and current:
                value['detail'] = self.reason or '等待当前对象的清晰正面人脸'
            result = self.result
            fresh = self.ready and not self.error and self._fresh(result)
            if fresh:
                match = result['match']
                value.update(state='KNOWN' if match.state == 'KNOWN' else 'UNKNOWN',
                             person_id=match.identity_id, display_name=match.name,
                             detail='CPU 参考识别 · '+match.name if match.state == 'KNOWN' else
                             '匹配存在歧义，请重新面对摄像头' if match.state == 'AMBIGUOUS' else '未登记 / UNKNOWN',
                             source_frame_id=result['fid'], source_mono_ms=result['stamp'],
                             target=copy.deepcopy(result['target']))
            elif result and current and not self.error:
                value['detail'] = '身份结果已过期，等待新的人脸'
            if self.last_operation:
                value['last_operation'] = copy.deepcopy(self.last_operation)
            value['enrollment_supported'] = bool(self.ready and not self.error)
            if self.enrollment:
                job = self.enrollment
                value.update(state='ENROLLING', detail='正在采样 '+str(len(job['vectors']))+'/'+str(self.enrollment_samples))
                value['enrollment'] = {'command_id': job['command_id'], 'sample_count': len(job['vectors']),
                                       'required_samples': self.enrollment_samples}
            can_enroll = bool(fresh and result['match'].state == 'UNKNOWN' and len(people) < self.max_people
                              and self.enrollment is None)
            return value, {'identity_enroll': can_enroll, 'identity_delete': bool(people),
                           'identity_collect': bool(can_enroll and self.enrollment_target() == self.current_target()),
                           'identity_cancel': bool(self.ready and not self.error)}

    def enroll(self, params, command_id):
        with self.lock:
            if self.enrollment:
                raise ValueError('多帧登记尚未结束，请先完成或取消')
            key = target_key(params['target'])
            name = params['display_name'].strip()
            if params.get('confirmed') is not True or not text(name, 48, False):
                raise ValueError('登记需要明确确认和有效名称')
            result = self.result
            if not self.ready or self.error or not self._fresh(result) or result['target'] != key:
                raise ValueError('目标或合格人脸已变化，请重新确认后登记')
            if result['match'].state != 'UNKNOWN':
                raise ValueError('当前对象已登记或匹配有歧义，请先核对身份')
            if any(p['display_name'].casefold() == name.casefold() for p in self.store.people()):
                raise ValueError('该称呼已存在，请使用不同称呼')
            self.store.enroll(uuid.uuid4().hex, name, result['embedding'], consent=True,
                              expected_revision=result['revision'], max_people=self.max_people)
            result['revision'] = self.store.revision
            result['match'] = self.store.match(result['embedding'])
            detail = '已登记“'+name+'”'
            self.last_operation = {'command_id': command_id, 'action': 'identity_enroll',
                                   'state': 'COMMITTED', 'detail': detail, 'db_version': self.store.revision}
            return detail

    def delete(self, params, command_id):
        with self.lock:
            if params.get('confirmed') is not True:
                raise ValueError('删除需要明确确认')
            if not self.store.delete(params['person_id'], expected_revision=params['db_version']):
                raise ValueError('该身份已删除，请刷新状态')
            # Invalidate every cached template/result, including an in-flight job.
            self.result = self.pending = None
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
                self.result = {'target': key, 'fid': fid, 'stamp': stamp, 'embedding': vector,
                               'revision': revision, 'match': self.store.match(vector)}
                self._sample_enrollment(self.result, getattr(extractor, 'sample_signature', None))
            else:
                self._check_enrollment()

    def work(self):
        try:
            extractor = self.extractor_factory()
            with self.lock:
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
                self._check_enrollment()

    def health(self):
        with self.lock:
            return {'ready': self.ready and not self.error, 'error': self.error,
                    'backend': 'CPU_SFACE_REFERENCE', 'processed': self.processed,
                    'discarded': self.discarded, 'last_inference_ms': self.last_ms,
                    'pending_frames': int(self.pending is not None)}

    def close(self):
        with self.condition:
            self.closed = True
            self._finish_enrollment('CANCELLED', '身份服务已关闭，登记取消')
            self.pending = self.result = None
            self.condition.notify_all()
        if self.thread:
            self.thread.join(5)
            if self.thread.is_alive():
                raise RuntimeError('Identity worker did not stop; database remains open')
        with self.lock:
            self.store.close()
