"""Small persistent UI preferences and a bounded, asynchronous ALSA mixer."""
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time

DEFAULTS = {'volume': 100, 'muted': False, 'fullscreen': True, 'economy': False}


def validate(values):
    if not isinstance(values, dict) or set(values) - set(DEFAULTS):
        raise ValueError('Unknown UI setting')
    for key, value in values.items():
        if key == 'volume':
            if type(value) is not int or not 0 <= value <= 100:
                raise ValueError('Volume must be an integer from 0 to 100')
        elif type(value) is not bool:
            raise ValueError('UI switches must be boolean')
    return dict(values)


class SettingsStore:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.values = dict(DEFAULTS)
        self.loaded = False
        self.load_error = ''
        if self.path.exists():
            try:
                if self.path.stat().st_size > 8192:
                    raise ValueError('Settings file is too large')
                data = json.loads(self.path.read_text(encoding='utf-8'))
                if data.get('schema_version') != 1:
                    raise ValueError('Unsupported settings version')
                self.values.update(validate(data['values']))
                self.loaded = True
            except (OSError, ValueError, KeyError, TypeError) as exc:
                self.load_error = str(exc)

    def read(self):
        with self.lock:
            return dict(self.values)

    def update(self, values):
        values = validate(values)
        with self.lock:
            updated = dict(self.values, **values)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_name(self.path.name + '.tmp')
            payload = json.dumps({'schema_version': 1, 'values': updated}, indent=2) + '\n'
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0)
            fd = os.open(str(temporary), flags, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(str(temporary), str(self.path))
            self.values = updated
            return dict(updated)


class AlsaMixer:
    """Only the MCP01 playback PCM control is writable; never capture controls."""
    def __init__(self, run=subprocess.run):
        self.run = run

    @staticmethod
    def parse(output):
        volumes = re.findall(r'Playback\s+\d+\s+\[(\d+)%\]', output)
        switches = re.findall(r'\[(on|off)\]', output)
        if not volumes or not switches or len(set(volumes)) != 1 or len(set(switches)) != 1:
            raise RuntimeError('Cannot read the joined MCP01 playback control')
        volume = int(volumes[0])
        validate({'volume': volume})
        return {'volume': volume, 'muted': switches[0] == 'off'}

    def command(self, *args):
        result = self.run(['amixer', '-c', 'MCP01', *args], stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, timeout=4, text=True)
        if result.returncode:
            raise RuntimeError('MCP01 音量控制不可用：' + result.stdout.strip()[:200])
        return result.stdout

    def read(self):
        return self.parse(self.command('sget', 'PCM'))

    def apply(self, values):
        validate(values)
        current = self.read()
        desired = dict(current, **values)
        self.command('sset', 'PCM', str(desired['volume']) + '%',
                     'mute' if desired['muted'] else 'unmute')
        actual = self.read()
        if abs(actual['volume'] - desired['volume']) > 1 or actual['muted'] != desired['muted']:
            raise RuntimeError('MCP01 音量回读与设置不符')
        return actual


class MixerService:
    """Latest pending setting wins; ALSA commands never run in the GTK thread."""
    def __init__(self, store, backend=None, *, poll_seconds=2):
        self.store, self.backend = store, backend or AlsaMixer()
        self.poll_seconds = poll_seconds
        self.condition = threading.Condition()
        self.closed = False
        self.pending = None
        self.version = self.applied_version = 0
        self.status = {'available': False, 'volume': None, 'muted': False,
                       'pending': False, 'error': '', 'revision': 0}
        if store.loaded:
            self.pending = {k: store.read()[k] for k in ('volume', 'muted')}
            self.version = 1
            self.status['pending'] = True
        self.thread = threading.Thread(target=self.work, name='aura-mixer', daemon=True)
        self.thread.start()

    def request(self, values):
        validate(values)
        if not values or set(values) - {'volume', 'muted'}:
            raise ValueError('Unsupported mixer setting')
        with self.condition:
            if self.closed:
                raise RuntimeError('Mixer is closed')
            self.pending = dict(self.pending or {}, **values)
            self.version += 1
            self.status.update(pending=True, error='')
            self.condition.notify()
            return self.version

    def read(self):
        with self.condition:
            return dict(self.status, requested_version=self.version,
                        applied_version=self.applied_version)

    def work(self):
        first = True
        while True:
            with self.condition:
                if not first and self.pending is None and not self.closed:
                    self.condition.wait(self.poll_seconds)
                if self.closed:
                    return
                request, version = self.pending, self.version
                self.pending = None
            first = False
            try:
                actual = self.backend.apply(request) if request else self.backend.read()
                if request:
                    self.store.update(actual)
                with self.condition:
                    self.applied_version = version
                    self.status.update(actual, available=True, error='',
                                       pending=self.pending is not None,
                                       revision=self.status['revision'] + 1)
            except Exception as exc:
                with self.condition:
                    self.status.update(available=False, error=str(exc),
                                       pending=self.pending is not None,
                                       revision=self.status['revision'] + 1)

    def close(self):
        with self.condition:
            self.closed = True
            self.condition.notify()
        self.thread.join(timeout=5)


def touch_devices(root='/sys/class/input'):
    devices = []
    for event in sorted(Path(root).glob('event*')):
        try:
            props = (event/'device/properties').read_text().strip().split()
            # INPUT_PROP_DIRECT: an absolute direct surface, rather than a mouse.
            if props and int(props[-1], 16) & 2:
                devices.append({'event': event.name,
                                'name': (event/'device/name').read_text().strip()})
        except (OSError, ValueError):
            continue
    return devices
