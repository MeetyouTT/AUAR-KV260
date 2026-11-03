"""Pinned r1 read-only guards and metadata receipt writer, with X mutation paths excluded."""

import ctypes as C


import ctypes.util


import hashlib


import http.client


import importlib.util


import json


import os


from pathlib import Path


import time


STARTUP_SHA = '94f665cf69e861d4f3d625dd627116218120cdbbef2244aa4cf2b63c39b9f1c7'


X11_SHA = 'da318d5094a44bce9e62d57dda5c5c2f62ee06580d028e9cc08334737c9ceb97'


BOOT = 'bebd3e7d-e984-4517-8cbb-211df7f1c6dc'


CONTROL = Path('/home/root/aura-board-business-20261030/control-production-v1')


POLICY_PATH = CONTROL / ('temporary-display-v21-' + BOOT + '.json')


PREFERENCE = Path('/home/root/.local/share/aura-board-business/listening_preference.json')


ORIGINAL = dict(timeout=600, interval=600, prefer_blank=1, allow_exposures=1)


TEMPORARY = dict(ORIGINAL, timeout=0)


class Refused(RuntimeError):
    pass


def need(condition, code):
    if not condition:
        raise Refused(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def bounded(path, size=1048576):
    path = Path(path)
    need(path.resolve() == path and not path.is_symlink(), 'PATH_IDENTITY_CHANGED')
    with path.open('rb') as stream:
        raw = stream.read(size + 1)
    need(len(raw) <= size, 'BOUNDED_METADATA_REQUIRED')
    return raw


def policy(raw):
    value = json.loads(raw)
    need(set(value) == {'boot_id', 'owner', 'phase', 'original_screen_saver',
                       'dpms_capable', 'dpms_originally_enabled', 'saved_mono'}, 'POLICY_KEYS_CHANGED')
    need(value['boot_id'] == BOOT and value['owner'] == 'root-v21-display-publication'
         and value['phase'] == 'ORIGINAL_POLICY_SAVED', 'ORIGINAL_POLICY_OWNER_CHANGED')
    need(value['original_screen_saver'] == ORIGINAL
         and all(type(v) is int for v in value['original_screen_saver'].values())
         and value['dpms_capable'] is True and value['dpms_originally_enabled'] is True,
         'ORIGINAL_POLICY_VALUES_CHANGED')
    need(type(value['saved_mono']) in (int, float) and 0 < value['saved_mono'] < time.monotonic(),
         'ORIGINAL_POLICY_TIME_CHANGED')
    return value


def helper_module(spec):
    path = Path(spec['target']) / 'runtime/aura/tools/x11_display_activity.py'
    raw = bounded(path)
    need(sha(raw) == X11_SHA, 'PINNED_X11_HELPER_CHANGED')
    module_spec = importlib.util.spec_from_loader('_pinned_v21_x11_display_activity', loader=None)
    module = importlib.util.module_from_spec(module_spec)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def full_guard(arguments):
    captured = []
    namespace = dict(SPEC=arguments['spec'], READY=arguments['ready'], EXPECTED_STARTUP=STARTUP_SHA,
                     PRODUCTS=arguments['products'], ALLOWED_PRODUCTS=list(arguments['products']),
                     print=lambda value: captured.append(json.loads(value)))
    exec(compile(arguments['guard_source'], '<pinned-v21-readonly-guard>', 'exec'), namespace)
    need(len(captured) == 1, 'FULL_GUARD_RESULT_MISSING')
    value = captured[0]
    need(value['startup_sha256'] == STARTUP_SHA and value['component_pins'] == arguments['spec']['component_sha256'],
         'FULL_GUARD_SOURCE_MISMATCH')
    proof = {key: value[key] for key in ('boot_id', 'startup_sha256', 'source_manifest_sha256',
             'configuration_sha256', 'supervisor', 'gtk', 'camera')}
    need(proof == arguments['baseline_owners'], 'SEALED_V21_OWNER_CHANGED')
    return proof


def identity(pid):
    path = Path('/proc') / str(pid)
    fields = bounded(path / 'stat', 65536).decode().rsplit(')', 1)[1].split()
    return dict(pid=pid, birth_ticks=int(fields[19]), command_sha256=sha(bounded(path / 'cmdline')))


def same_owners(expected):
    need(bounded('/proc/sys/kernel/random/boot_id', 128).decode().strip() == BOOT, 'BOOT_CHANGED')
    for kind in ('supervisor', 'gtk', 'camera'):
        need(identity(expected[kind]['pid']) == expected[kind], 'LIVE_OWNER_CHANGED')


def paused_guard(expected):
    same_owners(expected)
    state = json.loads(bounded(CONTROL / 'state.json'))
    need(state.get('phase') == 'COMMITTED' and state.get('guard_removed') is True
         and state.get('target_startup_sha256') == STARTUP_SHA, 'PUBLICATION_CHANGED')
    preference = json.loads(bounded(PREFERENCE, 4096))
    need(set(preference) == {'version', 'enabled'} and type(preference['version']) is int
         and preference['version'] == 1 and preference['enabled'] is False, 'SAVED_PAUSE_CHANGED')
    connection = http.client.HTTPConnection('127.0.0.1', 8783, timeout=2)
    try:
        connection.request('GET', '/api/state')
        response = connection.getresponse()
        need(response.status == 200, 'UI_METADATA_UNAVAILABLE')
        raw = response.read(1048577)
        need(len(raw) <= 1048576, 'UI_METADATA_TOO_LARGE')
        ui = json.loads(raw)
    finally:
        connection.close()
    handsfree = ui.get('handsfree_dialogue', {})
    display = ui.get('avatar_display', {})
    need(handsfree.get('enabled') is False and handsfree.get('state') == 'PAUSED'
         and handsfree.get('microphone_open') is False and ui.get('playing') is False
         and ui.get('phase') == 'IDLE', 'LIVE_PAUSE_CHANGED')
    need(display.get('kind') == 'native_yuki_egl' and display.get('visible') is True
         and type(display.get('frames')) is int and display['frames'] > 0, 'UI_DISPLAY_NOT_READY')
    same_owners(expected)
    return dict(enabled=False, state='PAUSED', microphone_open=False, playing=False,
                native_frames=display['frames'])


def error_metadata(error):
    kind = type(error).__name__
    allowed = {'Refused', 'AssertionError', 'OSError', 'AttributeError', 'ValueError',
               'KeyError', 'TypeError', 'TimeoutError', 'FileNotFoundError', 'KeyboardInterrupt'}
    code = str(error) if type(error) is Refused else 'TOOL_OR_GUARD_FAILURE'
    return dict(code=code, exception_class=kind if kind in allowed else 'OtherException')


def save_receipt(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    need(path.parent.resolve() == path.parent and not path.is_symlink(), 'RECEIPT_PATH_CHANGED')
    temporary = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    with temporary.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(str(temporary), str(path))
    descriptor = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

