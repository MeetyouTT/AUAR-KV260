"""Bounded X11 policy restoration and passive observation for the paused v21 UI."""
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


class XScreenSaverInfo(C.Structure):
    _fields_ = [('window', C.c_ulong), ('state', C.c_int), ('kind', C.c_int),
                ('til_or_since', C.c_ulong), ('idle', C.c_ulong), ('event_mask', C.c_ulong)]


def signature(library, name, arguments, result=C.c_int):
    function = getattr(library, name)
    function.argtypes = arguments
    function.restype = result
    return function


class XSession:
    """All necessary symbols are resolved before opening the display or writing policy."""
    def __init__(self, helper, load_xss=None):
        self.display = None
        self.x, self.ext = helper._display_libraries()
        need(self.ext is not None, 'DPMS_LIBRARY_UNAVAILABLE')
        load_xss = load_xss or (lambda: C.CDLL(ctypes.util.find_library('Xss') or 'libXss.so.1'))
        self.xss = load_xss()
        pointer = C.c_void_p
        integer = C.POINTER(C.c_int)
        ushort = C.POINTER(C.c_ushort)
        signature(self.x, 'XGetScreenSaver', [pointer, integer, integer, integer, integer])
        signature(self.x, 'XSetScreenSaver', [pointer, C.c_int, C.c_int, C.c_int, C.c_int])
        signature(self.x, 'XDefaultRootWindow', [pointer], C.c_ulong)
        signature(self.x, 'XSync', [pointer, C.c_int])
        signature(self.ext, 'DPMSCapable', [pointer])
        signature(self.ext, 'DPMSInfo', [pointer, ushort, integer])
        signature(self.ext, 'DPMSGetTimeouts', [pointer, ushort, ushort, ushort])
        signature(self.ext, 'DPMSEnable', [pointer])
        signature(self.ext, 'DPMSDisable', [pointer])
        signature(self.ext, 'DPMSForceLevel', [pointer, C.c_ushort])
        signature(self.xss, 'XScreenSaverQueryExtension', [pointer, integer, integer])
        signature(self.xss, 'XScreenSaverQueryInfo', [pointer, C.c_ulong, C.POINTER(XScreenSaverInfo)])
        self.display = self.x.XOpenDisplay(None)
        need(bool(self.display), 'X11_CONNECTION_UNAVAILABLE')
        try:
            event, error = C.c_int(), C.c_int()
            need(bool(self.xss.XScreenSaverQueryExtension(self.display, C.byref(event), C.byref(error))),
                 'XSS_EXTENSION_UNAVAILABLE')
            need(bool(self.ext.DPMSCapable(self.display)), 'DPMS_CAPABILITY_UNAVAILABLE')
            self.query()
        except BaseException:
            self.close()
            raise

    def query(self):
        timeout, interval, blank, exposures = [C.c_int() for _ in range(4)]
        self.x.XGetScreenSaver(self.display, C.byref(timeout), C.byref(interval),
                              C.byref(blank), C.byref(exposures))
        level, enabled = C.c_ushort(), C.c_int()
        need(bool(self.ext.DPMSInfo(self.display, C.byref(level), C.byref(enabled))), 'DPMS_QUERY_FAILED')
        standby, suspend, off = C.c_ushort(), C.c_ushort(), C.c_ushort()
        need(bool(self.ext.DPMSGetTimeouts(self.display, C.byref(standby), C.byref(suspend), C.byref(off))),
             'DPMS_TIMEOUT_QUERY_FAILED')
        info = XScreenSaverInfo()
        need(bool(self.xss.XScreenSaverQueryInfo(self.display, self.x.XDefaultRootWindow(self.display),
                                               C.byref(info))), 'XSS_QUERY_FAILED')
        need(info.state in (0, 1, 2, 3) and info.kind in (0, 1, 2)
             and enabled.value in (0, 1) and level.value in (0, 1, 2, 3), 'X_ENUM_UNEXPECTED')
        return dict(screen_saver=dict(timeout=timeout.value, interval=interval.value,
            prefer_blank=blank.value, allow_exposures=exposures.value), dpms_enabled=bool(enabled.value),
            dpms_level=level.value, dpms_timeouts=[standby.value, suspend.value, off.value],
            xss_idle_ms=info.idle, xss_state=info.state, xss_kind=info.kind)

    def set_policy(self, values, enabled):
        self.x.XSetScreenSaver(self.display, values['timeout'], values['interval'],
                               values['prefer_blank'], values['allow_exposures'])
        function = self.ext.DPMSEnable if enabled else self.ext.DPMSDisable
        need(bool(function(self.display)), 'DPMS_POLICY_WRITE_FAILED')
        self.x.XSync(self.display, 0)

    def wake_for_failure(self):
        # Used only after the same live paused owner has been revalidated.
        self.x.XResetScreenSaver(self.display)
        self.x.XSync(self.display, 0)

    def close(self):
        if self.display:
            self.x.XCloseDisplay(self.display)
            self.display = None


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


def validate_x(value, original, timeouts):
    need(value['screen_saver'] == (ORIGINAL if original else TEMPORARY)
         and value['dpms_enabled'] is original and value['dpms_timeouts'] == timeouts,
         'X_POLICY_READBACK_MISMATCH')
    need(value['dpms_level'] == 0 and value['xss_state'] == 0, 'DISPLAY_NOT_AWAKE')


def observe(session, guard, persist, receipt, finish=None, clock=time.monotonic, sleep=time.sleep):
    before = session.query()
    timeouts = before['dpms_timeouts']
    validate_x(before, False, timeouts)
    guard()
    receipt.update(status='RESTORE_INTENT_SAVED', before=before, samples=[])
    persist(receipt)
    mutated = False
    try:
        mutated = True
        session.set_policy(ORIGINAL, True)
        validate_x(session.query(), True, timeouts)
        receipt['status'] = 'ORIGINAL_POLICY_RESTORED'
        persist(receipt)
        started = clock()
        for index in range(31):
            sleep(max(0., started + index - clock()))
            need(clock() - started < 40., 'OBSERVATION_DEADLINE')
            live = guard()
            value = session.query()
            validate_x(value, True, timeouts)
            receipt['samples'].append(dict(elapsed_seconds=clock() - started, **value, **live))
            need(value['xss_idle_ms'] <= 7500, 'PAUSED_IDLE_EXCEEDED_7500_MS')
            if index % 5 == 0:
                persist(receipt)
        drops = [sample['elapsed_seconds'] for before, sample in zip(receipt['samples'], receipt['samples'][1:])
                 if before['xss_idle_ms'] - sample['xss_idle_ms'] >= 1000]
        need(len(drops) >= 4, 'INSUFFICIENT_PASSIVE_IDLE_RESETS')
        if finish is not None:
            finish()
        receipt.update(status='ORIGINAL_POLICY_RESTORED_PAUSED_IDLE_OBSERVED',
                       idle_drop_count=len(drops), idle_drop_times_seconds=drops,
                       observer_reset_calls=0, observer_dpms_timeout_writes=0,
                       external_input_not_excluded=True, policy_left='ORIGINAL')
        persist(receipt)
        return receipt
    except BaseException as error:
        receipt.update(status='RESTORE_OR_OBSERVATION_FAILED', failure=error_metadata(error),
                       policy_left='UNKNOWN', fallback='NOT_ATTEMPTED')
        if mutated:
            try:
                guard()
                session.set_policy(TEMPORARY, False)
                session.wake_for_failure()
                validate_x(session.query(), False, timeouts)
                receipt.update(fallback='TEMPORARY_RESTORED_SAME_PAUSED_OWNER', policy_left='TEMPORARY')
            except BaseException as fallback_error:
                receipt.update(fallback='REFUSED_OR_FAILED', fallback_failure=error_metadata(fallback_error))
        persist(receipt)
        return receipt


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


def execute(arguments):
    receipt = dict(status='PREFLIGHT_STARTED', action=arguments['action'],
        startup_sha256=STARTUP_SHA, microphone_control_sent=False, audio_played=False,
        production_database_opened=False, policy_file=str(POLICY_PATH))
    session = None
    receipt_owned = False
    receipt_path = CONTROL / ('temporary-display-v21-observation-' + str(arguments['token']) + '.json')
    try:
        need(type(arguments['token']) is int and arguments['token'] > 0, 'VALID_RECEIPT_TOKEN_REQUIRED')
        need(not receipt_path.exists(), 'NEW_RECEIPT_PATH_REQUIRED')
        receipt_owned = True
        need(arguments['spec']['startup_sha256'] == STARTUP_SHA, 'EXACT_V21_STARTUP_REQUIRED')
        expected = full_guard(arguments)
        raw = bounded(POLICY_PATH, 8192)
        policy(raw)
        receipt.update(owners=expected, policy_file_sha256=sha(raw), observed_mono=time.monotonic(),
                       remote_receipt_path=str(receipt_path))
        session = XSession(helper_module(arguments['spec']))
        guard = lambda: paused_guard(expected)
        live = guard()
        current = session.query()
        validate_x(current, False, current['dpms_timeouts'])
        receipt.update(status='PREFLIGHT_SYMBOLS_CONNECTION_PAUSE_PASS', x=current, listening=live,
                       xss_available=True, policy_modified=False)
        if arguments['action'] == 'preflight':
            save_receipt(receipt_path, receipt)
            return receipt
        need(arguments['action'] == 'restore-observe', 'ACTION_REJECTED')
        previous = arguments['preflight']
        need(previous.get('status') == 'PREFLIGHT_SYMBOLS_CONNECTION_PAUSE_PASS'
             and previous.get('owners') == expected and previous.get('policy_file_sha256') == sha(raw)
             and all(previous.get('x', {}).get(key) == current[key] for key in
                     ('screen_saver', 'dpms_enabled', 'dpms_level', 'dpms_timeouts'))
             and 0 <= time.monotonic() - previous['observed_mono'] <= 300,
             'FRESH_MATCHING_PREFLIGHT_REQUIRED')
        receipt['policy_modified'] = True
        def finish():
            need(full_guard(arguments) == expected, 'FINAL_OWNER_OR_SOURCE_CHANGED')
            receipt['full_component_checks'] = [380, 380]
        receipt = observe(session, guard, lambda value: save_receipt(receipt_path, value), receipt, finish)
        return receipt
    except BaseException as error:
        receipt.update(status='REFUSED_OR_TOOL_FAILED', failure=error_metadata(error))
        # Before restoration, every failure leaves the temporary policy in place.
        if receipt_owned and receipt_path.parent.exists():
            save_receipt(receipt_path, receipt)
        return receipt
    finally:
        if session is not None:
            session.close()

def expired(signum, frame):
    raise Refused('BOUNDED_DISPLAY_OPERATION_TIMEOUT')
import signal
signal.signal(signal.SIGALRM, expired)
signal.alarm(90)
try:
    result = execute(ARGUMENTS)
finally:
    signal.alarm(0)
print(json.dumps(result, sort_keys=True))
