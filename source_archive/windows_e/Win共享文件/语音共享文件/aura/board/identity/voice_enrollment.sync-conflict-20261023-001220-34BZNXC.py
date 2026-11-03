"""ASR-driven enrollment on the board; no LLM output can commit a face template.

Only the camera owner collects images. This coordinator uses fresh UI status and
bounded commands; it never opens a camera, stores photos or loads a face model.
"""
import copy
import re
import threading
import time


def compact(text):
    return re.sub(r'[\s，。！？、,.!?：:；;“”"‘’]', '', text)


TRIGGERS = ('记住我是谁', '记住我的身份', '记住我', '帮我登记身份', '我要登记身份', '登记我的身份')
YES = {'确认', '确认登记', '同意', '同意登记', '是的', '对', '可以', '好的', '确认记住'}
NO = {'不', '不是', '不要', '不用', '取消', '取消登记', '别记了', '算了', '不同意', '不需要', '不要记住我'}


def requested_name(text):
    match = re.fullmatch(r'(?:我叫|叫我|我的名字是|我是)([\u3400-\u9fffA-Za-z0-9·]{1,16})', text)
    return match.group(1) if match else None


class VoiceEnrollment:
    def __init__(self, services, *, clock=time.monotonic, sleep=time.sleep):
        self.services, self.clock, self.sleep = services, clock, sleep
        self.lock = threading.RLock()
        self.phase, self.name, self.target = 'IDLE', '', None
        self.expires, self.command_id = 0, None
        self.serial = 0

    def _cancel_remote(self, cid):
        if cid:
            try:
                self.services.submit('identity_cancel', {'enrollment_id': cid})
            except ValueError:
                # Camera timeout/target guards still bound an unreachable job.
                pass

    def reset(self, *, collecting_only=False):
        with self.lock:
            if collecting_only and self.phase != 'COLLECTING':
                return
            cid = self.command_id
            self.phase, self.name, self.target, self.command_id = 'IDLE', '', None, None
            self.serial += 1
        self._cancel_remote(cid)

    def interrupt(self):
        self.reset(collecting_only=True)

    def _target(self):
        snapshot = self.services.read().get('snapshot')
        if not snapshot or snapshot.get('source_kind') != 'actual':
            raise ValueError('相机服务尚未连接，请稍后再登记。')
        modules = snapshot['modules']
        if (modules.get('camera', {}).get('state') != 'READY'
                or modules.get('vision', {}).get('state') != 'READY'):
            raise ValueError('摄像头画面暂时不可用，请稍后再登记。')
        identity = modules.get('identity', {})
        if not identity.get('enrollment_supported'):
            raise ValueError('身份登记服务尚未就绪，现在还不能记住你。')
        tracks = modules.get('target', {}).get('tracks', [])
        if modules.get('vision', {}).get('people_count') != 1 or len(tracks) != 1:
            raise ValueError('请让登记者单独站在摄像头前，避免记错人。')
        return snapshot, copy.deepcopy(tracks[0]['key'])

    def handle(self, text, *, is_current=lambda: True, deadline=None):
        """Return a factual spoken reply, or None to use the ordinary LLM path."""
        normalized = compact(text)
        start, initial_name = False, None
        for trigger in TRIGGERS:
            candidate = normalized[1:] if normalized.startswith('请') else normalized
            if candidate == trigger:
                start = True
                break
            if candidate.startswith(trigger):
                initial_name = requested_name(candidate[len(trigger):])
                if initial_name:
                    start = True
                    break
        with self.lock:
            if not is_current():
                raise InterruptedError('Stale enrollment speech')
            if self.phase == 'IDLE' and not start:
                if normalized == '取消登记':
                    return '当前没有正在进行的登记。'
                return None
            if normalized in NO:
                self.reset()
                return '已取消登记。'
            if self.phase != 'IDLE' and self.clock() >= self.expires:
                self.reset()
                if not start:
                    return '这次登记已超时，请重新说“记住我是谁”。'
            try:
                snapshot, target = self._target()
                if self.target is not None and target != self.target:
                    raise ValueError('画面中的人物已经变化，请重新开始登记。')
            except ValueError as exc:
                self.reset()
                return str(exc)
            if start:
                self.reset()
                self.target, self.name = target, initial_name or ''
                self.expires = self.clock()+60
                self.phase = 'CONFIRM' if self.name else 'ASK_NAME'
                if not self.name:
                    return '可以，请一直留在画面中。你希望我怎么称呼你？请说“我叫”加上称呼。'
            elif self.phase == 'ASK_NAME':
                name = requested_name(normalized)
                if not name:
                    return '请说“我叫”加上你希望使用的称呼，或者说“取消登记”。'
                self.name, self.phase = name, 'CONFIRM'
            elif self.phase == 'CONFIRM':
                if normalized not in YES:
                    name = requested_name(normalized)
                    if name:
                        self.name = name
                    else:
                        return '请说“确认登记”，或者说“取消登记”。'
                else:
                    self.phase = 'COLLECTING'
                    serial = self.serial
                    # Never hold this lock across camera/network waits.
            else:
                return '正在采样，请正对摄像头，或取消后重试。'
            if self.phase != 'COLLECTING':
                return ('我将保存你的人脸特征，称呼你为'+self.name+'。请正对摄像头，确认登记吗？')
        try:
            return self._collect(serial, is_current, deadline)
        except InterruptedError:
            raise
        except (ValueError, TimeoutError) as exc:
            return str(exc)
        finally:
            with self.lock:
                if self.serial == serial:
                    self.reset()

    def _collect(self, serial, is_current, deadline):
        end = min(self.clock()+20, deadline if deadline is not None else self.clock()+20)
        def current():
            with self.lock:
                valid = self.serial == serial and self.phase == 'COLLECTING'
            if not valid or not is_current():
                raise InterruptedError('Enrollment was cancelled or replaced')
            if self.clock() >= end:
                raise TimeoutError('暂时无法确认登记结果，请查看屏幕提示后重试。')
        current()
        snapshot, target = self._target()
        if target != self.target:
            raise ValueError('人物已变化，请重新登记。')
        if snapshot['modules']['target'].get('selected') != target:
            self.services.submit('target_select', {'target': target})
        ready_deadline = min(end, self.clock()+4)
        while True:
            current()
            snapshot, found = self._target()
            if found != target:
                raise ValueError('人物已变化，请重新登记。')
            if snapshot['modules']['target'].get('selected') == target and snapshot['capabilities'].get('identity_collect'):
                break
            if self.clock() >= ready_deadline:
                raise ValueError('没有获得清晰且未登记的人脸，请靠近摄像头后重试。')
            self.sleep(.1)
        with self.lock:
            current()
            name = self.name
            request = self.services.submit('identity_collect', {'target': target, 'display_name': name, 'confirmed': True})
            self.command_id = cid = request['command_id']
        while True:
            current()
            view = self.services.read()
            snapshot = view.get('snapshot')
            if snapshot:
                identity = snapshot['modules'].get('identity', {})
                operation = identity.get('last_operation', {})
                if operation.get('command_id') == cid and operation.get('action') == 'identity_collect':
                    state = operation.get('state')
                    if state == 'COMMITTED' and operation.get('db_version') == identity.get('db_version'):
                        # A queue receipt or a generated sentence cannot enter here.
                        with self.lock:
                            self.command_id = None
                        return '记住了，你是'+name+'。以后看到你，我会尝试认出你。'
                    if state in ('FAILED', 'CANCELLED'):
                        raise ValueError(operation.get('detail') or '登记未完成，请重试。')
                if self._target()[1] != target:
                    raise ValueError('人物已变化，登记已中止。')
            for result in view.get('results', []):
                if result.get('command_id') == cid and result.get('accepted') is False:
                    raise ValueError('登记未完成：'+result.get('detail', '请求未被相机服务接受'))
            self.sleep(.1)

    def public(self):
        with self.lock:
            return {'state': self.phase, 'display_name': self.name, 'command_id': self.command_id}
