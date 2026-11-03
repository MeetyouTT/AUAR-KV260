"""Bounded background HTTP adapter and persistent touchscreen connection prefs."""
from collections import deque
import copy
import ipaddress
import json
import os
from pathlib import Path
import threading
import urllib.parse
import urllib.request
import uuid

from board.interaction.ui_contract import (PROTOCOL, SnapshotGate, millis, require,
                                          validate_action, validate_ack)

DEFAULT_CONNECTION = {'enabled': False, 'host': '127.0.0.1', 'port': 8790}


def validate_connection(values):
    require(isinstance(values, dict) and set(values) == set(DEFAULT_CONNECTION), '连接设置字段无效')
    require(type(values['enabled']) is bool and type(values['port']) is int
            and 1024 <= values['port'] <= 65535, '端口须为 1024～65535')
    host = values['host']
    require(isinstance(host, str), '请输入 IPv4 地址')
    try:
        address = ipaddress.IPv4Address(host)
    except ipaddress.AddressValueError:
        raise ValueError('请输入正确的 IPv4 地址') from None
    require(not address.is_unspecified and not address.is_multicast and str(address) != '255.255.255.255',
            '请输入具体的板端服务地址')
    return dict(values, host=str(address))


class ConnectionStore:
    def __init__(self, path, defaults=None):
        self.path = Path(path)
        self.values = validate_connection(defaults or DEFAULT_CONNECTION)
        self.error = ''
        if self.path.exists():
            try:
                require(self.path.stat().st_size <= 4096, '连接配置过大')
                value = json.loads(self.path.read_text(encoding='utf-8'))
                require(value['schema_version'] == PROTOCOL, '连接配置版本不匹配')
                self.values = validate_connection(value['connection'])
            except (OSError, ValueError, KeyError, TypeError) as exc:
                self.error = str(exc)

    def read(self):
        return dict(self.values)

    def update(self, values):
        values = validate_connection(values)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(self.path.name+'.tmp-'+uuid.uuid4().hex)
        fd = os.open(str(temp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump({'schema_version': PROTOCOL, 'connection': values}, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(str(temp), str(self.path))
        self.values, self.error = values, ''
        return self.read()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('服务接口不接受跳转')


class HttpTransport:
    def __init__(self):
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, base, path, data=None, *, limit=131072):
        request = urllib.request.Request(base+path, headers={'Accept': 'application/json'})
        if data is not None:
            request.data = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
            request.add_header('Content-Type', 'application/json')
        with self.opener.open(request, timeout=1.5) as response:
            body = response.read(limit+1)
            require(len(body) <= limit, '服务响应超过大小限制')
            return dict(response.headers.items()), body

    def json(self, base, path, data=None):
        headers, body = self.request(base, path, data)
        content_type = {k.lower(): v for k, v in headers.items()}.get('content-type', '')
        require(content_type.split(';')[0] == 'application/json', '服务没有返回 JSON')
        return json.loads(body.decode('utf-8'))


class UiServiceClient:
    """No network/file IO in GTK tick; four queued intents, latest preview only."""
    def __init__(self, boot_id, connection, *, transport=None, clock=millis, poll_seconds=.6):
        self.boot_id, self.clock = boot_id, clock
        self.connection = validate_connection(connection)
        self.transport = transport or HttpTransport()
        self.poll_seconds = poll_seconds
        self.condition = threading.Condition()
        self.gate = SnapshotGate(boot_id, clock)
        self.ui_epoch = uuid.uuid4().hex
        self.ui_generation = self.config_generation = 0
        self.waiting, self.results = deque(), deque(maxlen=16)
        self.inflight = None
        self.link = 'CONNECTING' if connection['enabled'] else 'DISABLED'
        self.error = ''
        self.closed = False
        self.preview = self.preview_key = None
        self.preview_error = ''
        self.thread = threading.Thread(target=self.work, name='aura-ui-services', daemon=True)
        self.thread.start()

    def configure(self, connection):
        connection = validate_connection(connection)
        with self.condition:
            self.connection = connection
            self.config_generation += 1
            self.ui_generation += 1
            self.gate = SnapshotGate(self.boot_id, self.clock)
            self.waiting.clear()
            self.inflight = None
            self.results.clear()
            self.preview = self.preview_key = None
            self.error = self.preview_error = ''
            self.link = 'CONNECTING' if connection['enabled'] else 'DISABLED'
            self.condition.notify()

    def read(self):
        with self.condition:
            snapshot = self.gate.read() if self.link == 'READY' else None
            link = 'STALE' if self.link == 'READY' and snapshot is None else self.link
            preview = self.preview if snapshot and snapshot.get('preview') == self.preview_key else None
            if preview and self.clock()-self.preview_key['captured_mono_ms'] > 1500:
                preview = None
            return {'link': link, 'error': self.error, 'snapshot': snapshot,
                    'connection': dict(self.connection), 'preview': preview,
                    'preview_error': self.preview_error, 'pending_count': len(self.waiting)+bool(self.inflight),
                    'ui_epoch': self.ui_epoch, 'ui_generation': self.ui_generation,
                    'results': copy.deepcopy(list(self.results))}

    def submit(self, action, params=None):
        params = {} if params is None else params
        with self.condition:
            require(not self.closed and self.link == 'READY', '服务尚未连接')
            snapshot = self.gate.read()
            params = validate_action(action, params, snapshot)
            if action == 'ask_frame':
                require(self.clock()-snapshot['preview']['captured_mono_ms'] <= 1500, '当前画面已过期')
            if action == 'cancel':
                self.ui_generation += 1
                self.waiting.clear()
                self.gate.cancel()
            require(len(self.waiting) < 4, '操作队列已满，请稍后再试')
            now = self.clock()
            command = {'protocol_version': PROTOCOL, 'board_boot_id': self.boot_id,
                       'service_epoch': snapshot['service_epoch'], 'command_id': uuid.uuid4().hex,
                       'ui_epoch': self.ui_epoch, 'ui_generation': self.ui_generation,
                       'snapshot_sequence': snapshot['sequence'], 'context': snapshot['context'],
                       'issued_mono_ms': now, 'deadline_mono_ms': now+2500,
                       'action': action, 'params': params}
            if action == 'ask_frame':
                command['params'] = {'frame': snapshot['preview']}
            self.waiting.append((self.config_generation, command))
            self.condition.notify()
            return {'ok': True, 'queued': True, 'command_id': command['command_id'],
                    'message': '请求已排队，等待服务回执'}

    def cancel_local(self):
        """Hide cancelled subtitles even when the provider has lost connectivity."""
        with self.condition:
            self.gate.cancel()
            self.ui_generation += 1
            self.waiting.clear()

    def refresh(self):
        with self.condition:
            self.condition.notify()

    def work(self):
        while True:
            with self.condition:
                if self.closed:
                    return
                connection, token = dict(self.connection), self.config_generation
                pending = self.waiting.popleft() if self.waiting else None
                self.inflight = pending[1]['command_id'] if pending else None
                if not connection['enabled']:
                    self.condition.wait(1)
                    continue
            base = 'http://'+connection['host']+':'+str(connection['port'])
            if pending:
                generation, command = pending
                result = dict(command_id=command['command_id'], action=command['action'])
                try:
                    require(self.clock() < command['deadline_mono_ms'], '操作尚未发送就已超时')
                    with self.condition:
                        snapshot = self.gate.read()
                        require(token == generation == self.config_generation
                                and command['ui_generation'] == self.ui_generation
                                and snapshot and snapshot['service_epoch'] == command['service_epoch'],
                                '操作归属已失效')
                        require(snapshot['context'] == command['context'], '操作会话已变化')
                        params = {} if command['action'] == 'ask_frame' else command['params']
                        validate_action(command['action'],params,snapshot)
                        if command['action'] == 'ask_frame':
                            require(snapshot.get('preview') == command['params']['frame']
                                    and self.clock()-snapshot['preview']['captured_mono_ms'] <= 1500,
                                    '问答画面已变化或过期')
                    ack = self.transport.json(base, '/v1/ui/commands', command)
                    result.update(validate_ack(ack, command, self.clock()))
                except Exception as exc:
                    result.update(accepted=False, detail=str(exc)[:160], outcome='UNKNOWN')
                with self.condition:
                    if (token == self.config_generation and command['ui_generation'] == self.ui_generation
                            and self.gate.value and self.gate.value['service_epoch'] == command['service_epoch']):
                        self.results.append(result)
                    if token == self.config_generation:
                        self.inflight = None
            try:
                value = self.transport.json(base, '/v1/ui/status')
                with self.condition:
                    if token != self.config_generation:
                        continue
                    self.gate.ingest(value)
                    self.link, self.error = 'READY', ''
                    snapshot = self.gate.read()
                    preview = snapshot.get('preview') if snapshot else None
                    needs_preview = (preview and preview != self.preview_key
                                     and self.clock()-preview['captured_mono_ms'] <= 1500)
                if needs_preview:
                    try:
                        path = '/v1/ui/preview.jpg?'+urllib.parse.urlencode(
                            {'camera_epoch': preview['camera_epoch'], 'frame_id': preview['frame_id']})
                        headers, image = self.transport.request(base, path, limit=262144)
                        headers = {k.lower(): v for k, v in headers.items()}
                        require(headers.get('content-type', '').split(';')[0] == 'image/jpeg'
                                and headers.get('x-aura-boot-id') == self.boot_id
                                and headers.get('x-aura-camera-epoch') == preview['camera_epoch']
                                and headers.get('x-aura-frame-id') == str(preview['frame_id']), '画面归属不匹配')
                        with self.condition:
                            if token == self.config_generation:
                                self.preview, self.preview_key, self.preview_error = image, preview, ''
                    except Exception as exc:
                        with self.condition:
                            self.preview = self.preview_key = None
                            self.preview_error = str(exc)[:160]
            except Exception as exc:
                with self.condition:
                    if token == self.config_generation:
                        self.link, self.error = 'OFFLINE', str(exc)[:160]
                        self.preview = self.preview_key = None
            with self.condition:
                if not self.waiting and not self.closed:
                    self.condition.wait(self.poll_seconds)

    def close(self):
        with self.condition:
            self.closed = True
            self.waiting.clear()
            self.condition.notify()
        self.thread.join(timeout=4)
