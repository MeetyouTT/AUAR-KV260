"""Keep lease renewal outside GTK/audio's Python interpreter; never auto-replay."""
from collections import deque
import copy
import math
import multiprocessing
import signal
import threading
import time
import uuid


def backend(connection, config, *, transport_factory=None):
    from board.motion.manual import ManualPan
    from board.motion.manual_vsrv import ManualVSRV
    shutdown = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *unused:shutdown.set())
    pan = ManualPan(transport_factory or (lambda:ManualVSRV(config)))
    last_status = 0
    try:
        while not shutdown.is_set():
            if connection.poll(.02):
                request = connection.recv()
                kind = request['kind']
                if kind == 'close':
                    break
                try:
                    if kind == 'stop':
                        result = pan.stop()
                    elif (type(request.get('issued')) not in (int, float)
                          or not math.isfinite(request['issued'])
                          or not 0 <= time.monotonic()-request['issued'] <= .25):
                        raise ValueError('操作已经过期，请重新点击')
                    elif kind == 'jog':
                        result = pan.jog(request['direction'], request['step_us'], source_time=request['issued'])
                    elif kind == 'reverse':
                        result = pan.reverse()
                    else:
                        raise ValueError('无效操作')
                    response = dict(kind='ack', id=request['id'], ok=True, result=result, state=pan.read())
                except Exception as exc:
                    response = dict(kind='ack', id=request['id'], ok=False, error=str(exc), state=pan.read())
                connection.send(response)
            if time.monotonic()-last_status >= .1:
                value = pan.read()
                value['history'] = value['history'][-8:]
                connection.send(dict(kind='state', value=value, at=time.monotonic()))
                last_status = time.monotonic()
    except (EOFError, BrokenPipeError, OSError):
        pass
    finally:
        pan.close()
        connection.close()


class ManualPanProcess:
    """GTK-facing intent/status proxy. No native register access in this process."""
    def __init__(self, config, *, target=backend):
        self.config, self.target = config, target
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.closed = False
        self.requests = deque()
        self.pending_id = None
        self.reconnecting = False
        self.connection = self.process = None
        self.updated = 0
        self.value = self.initial()
        self.thread = threading.Thread(target=self.work, name='aura-pan-proxy', daemon=True)
        self.thread.start()

    @staticmethod
    def initial():
        return dict(state='CONNECTING', pulse_us=None, target_us=None, left_sign=-1,
                    minimum_us=1400, maximum_us=1600, history=[],
                    mechanical_reference_calibrated=False, automatic_following=False,
                    message='正在连接转轴', error='')

    def read(self):
        with self.lock:
            value = copy.deepcopy(self.value)
            value['backend_pid'] = self.process.pid if self.process is not None else None
            if value['state'] != 'CONNECTING' and time.monotonic()-self.updated > 1:
                value.update(state='UNAVAILABLE', message='转轴状态暂不可用，请重新连接')
            return value

    def request(self, kind, *, source_time=None, **params):
        with self.lock:
            issued = time.monotonic() if source_time is None else source_time
            if kind != 'stop' and (type(issued) not in (int, float) or not math.isfinite(issued)
                                   or not 0 <= time.monotonic()-issued <= .25):
                raise ValueError('点击已经过期，请重新点击')
            if self.closed:
                raise ValueError('转轴接口已关闭')
            if kind != 'stop' and (self.value['state'] != 'READY' or self.pending_id
                                   or time.monotonic()-self.updated > .5):
                raise ValueError('请等待本次点动结束，或重新连接')
            if len(self.requests) >= 4:
                raise ValueError('操作尚未完成，请稍后再试')
            ident = uuid.uuid4().hex
            request = dict(kind=kind, id=ident, issued=issued, **params)
            if kind == 'stop':
                self.requests.clear()
                self.requests.appendleft(request)
                self.value.update(state='STOPPING', message='正在停止')
            else:
                self.requests.append(request)
                self.value.update(state='MOVING' if kind == 'jog' else 'CONFIGURING', message='正在点动' if kind == 'jog' else '正在切换方向')
            self.pending_id = ident
            self.wake.set()
            return dict(ok=True, queued=True, command_id=ident, message=self.value['message'])

    def jog(self, direction, step_us=20, *, source_time=None):
        if direction not in ('left','right') or type(step_us) is not int or step_us not in (5,20):
            raise ValueError('请选择有效方向与步长')
        return self.request('jog', source_time=source_time, direction=direction, step_us=step_us)

    def reverse(self):
        return self.request('reverse')

    def stop(self):
        return self.request('stop') if not self.closed else dict(ok=True)

    def reconnect(self):
        with self.lock:
            if self.closed or self.value['state'] in ('MOVING','STOPPING','CONFIGURING'):
                raise ValueError('停止后才能重新连接')
            self.requests.clear()
            self.pending_id = None
            self.reconnecting = True
            self.value.update(state='CONNECTING', message='正在重新核验转轴接口', error='')
            self.wake.set()
        return dict(ok=True, queued=True, message='正在重新连接，不会恢复旧动作')

    def close(self):
        with self.lock:
            self.closed = True
            self.wake.set()
        self.thread.join(timeout=4)

    def start_backend(self):
        context = multiprocessing.get_context('spawn')
        connection, child = context.Pipe()
        process = context.Process(target=self.target, args=(child,self.config), name='aura-pan-control', daemon=True)
        process.start()
        child.close()
        with self.lock:
            self.connection, self.process = connection, process
            self.updated = time.monotonic()

    def stop_backend(self):
        connection, process = self.connection, self.process
        if process is None:
            return
        try:
            connection.send(dict(kind='close'))
        except (OSError, BrokenPipeError):
            pass
        process.join(timeout=2)
        if process.is_alive():
            process.terminate()
            process.join(timeout=1)
        if process.is_alive():
            process.kill()
            process.join(timeout=1)
        connection.close()
        with self.lock:
            self.connection = self.process = None

    def work(self):
        while True:
            try:
                self.start_backend()
                self.run_connected()
            except Exception as exc:
                with self.lock:
                    self.value.update(state='FAULT', message='转轴连接已断开，请重新连接', error=str(exc))
                    self.pending_id = None
                    self.requests.clear()
                    self.updated = time.monotonic()
            finally:
                self.stop_backend()
            while True:
                with self.lock:
                    if self.closed:
                        return
                    reconnect, self.reconnecting = self.reconnecting, False
                if reconnect:
                    break
                self.wake.wait(.1)
                self.wake.clear()

    def run_connected(self):
        while True:
            with self.lock:
                if self.closed:
                    return
                reconnect, self.reconnecting = self.reconnecting, False
                request = self.requests.popleft() if self.requests else None
            if reconnect:
                self.stop_backend()
                self.start_backend()
                continue
            if request:
                self.connection.send(request)
            while self.connection.poll(0):
                response = self.connection.recv()
                with self.lock:
                    if response['kind'] == 'ack':
                        if response['id'] == self.pending_id:
                            self.value = response['state']
                            if not response['ok']:
                                self.value['message'] = response['error']
                            self.pending_id = None
                            self.updated = time.monotonic()
                    elif not self.pending_id:
                        self.value = response['value']
                        self.updated = response['at']
            if not self.process.is_alive():
                raise RuntimeError('独立转轴控制已退出，请重新连接')
            self.wake.wait(.02)
            self.wake.clear()
