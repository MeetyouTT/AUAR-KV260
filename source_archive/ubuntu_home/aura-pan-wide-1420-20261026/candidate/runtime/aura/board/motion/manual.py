"""Finite, explicitly requested calibration steps; never automatic following."""
from collections import deque
import copy
import math
import threading
import time
import uuid
from board.motion.pan_profile import HARD_MIN_US, HARD_MAX_US, CENTER_US


class ManualPan:
    """One hardware owner, no queued movement, and an interruptible finite lease."""
    def __init__(self, transport_factory, *, duration_s=2.0, clock=time.monotonic):
        if not 0 < duration_s <= 2:
            raise ValueError('Invalid finite step duration')
        self.factory, self.duration, self.clock = transport_factory, duration_s, clock
        self.condition = threading.Condition()
        self.cancel = threading.Event()
        self.closed = False
        self.pending = None
        self.history = deque(maxlen=32)
        self.value = dict(state='CONNECTING', pulse_us=None, target_us=None,
                          left_sign=-1, minimum_us=HARD_MIN_US, maximum_us=HARD_MAX_US,
                          center_us=CENTER_US, center_user_confirmed=True,
                          angle_endpoints_verified=False,
                          mechanical_reference_calibrated=False,
                          automatic_following=False, message='正在连接转轴', error='')
        self.thread = threading.Thread(target=self.work, name='aura-manual-pan', daemon=True)
        self.thread.start()

    def read(self):
        with self.condition:
            return copy.deepcopy(dict(self.value, history=list(self.history)))

    def jog(self, direction, step_us=20, *, source_time=None):
        with self.condition:
            issued = self.clock() if source_time is None else source_time
            if (type(issued) not in (int, float) or not math.isfinite(issued)
                    or not 0 <= self.clock()-issued <= .25):
                raise ValueError('点击已经过期，请重新点击')
            if self.closed or self.value['state'] != 'READY':
                raise ValueError('请等待本次点动结束，或先停止')
            if direction not in ('left', 'right') or type(step_us) is not int or step_us not in (5, 20):
                raise ValueError('请选择左转、右转和有效步长')
            sign = self.value['left_sign'] * (1 if direction == 'left' else -1)
            target = self.value['pulse_us'] + sign * step_us
            if not self.value['minimum_us'] <= target <= self.value['maximum_us']:
                raise ValueError('已到当前调节边界，请反向调节')
            self.cancel.clear()
            ident = uuid.uuid4().hex
            self.pending = dict(id=ident, target_us=target, issued=issued, direction=direction)
            self.value.update(state='MOVING', target_us=target, error='', message='正在点动')
            self.condition.notify()
            return dict(ok=True, command_id=ident, message='正在点动')

    def reverse(self):
        with self.condition:
            if self.closed or self.value['state'] != 'READY':
                raise ValueError('停止后才能切换左右方向')
            self.value['left_sign'] *= -1
            self.value['message'] = '左右按钮方向已互换'
            return dict(ok=True, message=self.value['message'])

    def stop(self):
        with self.condition:
            self.cancel.set()
            if self.value['state'] == 'MOVING':
                self.value.update(state='STOPPING', message='正在停止')
            self.condition.notify()
        return dict(ok=True, message='停止请求已发出')

    def close(self):
        with self.condition:
            self.closed = True
            self.cancel.set()
            self.condition.notify()
        self.thread.join(timeout=3)

    def publish_status(self, status, **values):
        with self.condition:
            self.value.update(pulse_us=status['width_us'], readback=copy.deepcopy(status), **values)

    def work(self):
        try:
            with self.factory() as hardware:
                initial = hardware.status()
                if initial['flags'] != 0 or initial['lease_left_ms'] != 0 or not HARD_MIN_US <= initial['width_us'] <= HARD_MAX_US:
                    raise RuntimeError('转轴尚未停止或位置读回无效')
                self.publish_status(initial, state='READY', message='点击一次，转动一小步', error='')
                try:
                    while True:
                        with self.condition:
                            self.condition.wait_for(lambda: self.closed or self.pending is not None)
                            if self.closed:
                                return
                            intent, self.pending = self.pending, None
                        if self.cancel.is_set() or not 0 <= self.clock() - intent['issued'] <= .25:
                            self.publish_status(hardware.stop(), state='READY', message='点动已取消')
                            continue
                        before = hardware.status()
                        self.run_step(hardware, intent, before)
                finally:
                    self.publish_status(hardware.stop(), state='CLOSED' if self.closed else 'FAULT')
        except Exception as exc:
            with self.condition:
                self.value.update(state='FAULT', error=str(exc), message='转轴不可调节，请检查连接')

    def run_step(self, hardware, intent, before):
        accepted = 0
        failure = None
        started = self.clock()
        try:
            hardware.before_move()
        except ValueError as exc:
            self.publish_status(hardware.status(), state='READY', message=str(exc), error='')
            return
        try:
            if self.cancel.is_set() or not 0 <= self.clock() - intent['issued'] <= .25:
                return
            hardware.begin(before)
            started = self.clock()
            while self.clock() - started < self.duration and not self.cancel.is_set():
                status = hardware.commit(intent['target_us'])
                accepted += 1
                self.publish_status(status)
                self.cancel.wait(.04)
            if not self.cancel.is_set() and hardware.status()['width_us'] != intent['target_us']:
                raise RuntimeError('转轴未到达请求脉宽')
        except Exception as exc:
            failure = dict(error=type(exc).__name__+': '+str(exc), detail=copy.deepcopy(getattr(exc, 'detail', {})))
            raise
        finally:
            completion_error = None
            completion = 'IMMEDIATE_STOP' if failure or self.cancel.is_set() else 'FULL_PULSE_FINISH'
            try:
                final = hardware.stop() if completion == 'IMMEDIATE_STOP' else hardware.finish()
            except Exception as exc:
                completion_error = exc
                if failure is None:
                    failure = dict(error=type(exc).__name__+': '+str(exc), detail={})
                final = hardware.stop()
            row = dict(command_id=intent['id'], direction=intent['direction'],
                       initial_us=before['width_us'], target_us=intent['target_us'],
                       final_us=final['width_us'], commands_accepted=accepted,
                       stopped_early=self.cancel.is_set(), duration_ms=round((self.clock()-started)*1000, 2),
                       timing=copy.deepcopy(getattr(hardware, 'timing', {})),
                       source_time=intent['issued'], completion=completion,
                       failure=failure, final=copy.deepcopy(final))
            with self.condition:
                self.history.append(row)
            self.publish_status(final, state='FAULT' if failure else 'READY',
                                message='完整脉冲结束失败，请检查连接' if failure else '已停止',
                                target_us=final['width_us'])
            if completion_error is not None:
                raise completion_error
