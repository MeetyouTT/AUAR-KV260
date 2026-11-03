"""Production listening preference, bound before the one audio owner starts.

The original voice-first controller, capture, endpoint, queue and ACK paths stay
in charge. This module performs no HTTP, model, microphone or service calls.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import stat
import threading

from common.handsfree_settings import HandsFreeSettings


class ProductionMonitorChoice:
    """Default-on board-private preference; only explicit toggles persist it.

    Internal cancellation, native failure and error cleanup must not turn a
    temporary failure into a saved user pause. The existing controller writes
    this interface during cancel(), so those writes are ignored unless its
    explicit handsfree_toggle() call owns the current thread's action window.
    """
    def __init__(self, private_root):
        self.root = Path(private_root)
        self.path = self.root / 'listening_preference.json'
        self.backend = HandsFreeSettings(self.path)
        self._action = threading.local()
        self._check()

    def _check(self):
        if (not self.root.is_absolute() or self.root.resolve(strict=True) != self.root
                or not self.root.is_dir()):
            raise ValueError('Canonical existing board-private root required')
        info = self.root.stat()
        if os.name != 'nt' and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
            raise ValueError('Board-private listening directory permissions required')
        if self.path.is_symlink():
            raise ValueError('Listening preference cannot be a symlink')
        if self.path.exists():
            info = self.path.stat()
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 4096
                    or self.path.resolve(strict=True) != self.path):
                raise ValueError('Unsafe listening preference file')
            if os.name != 'nt' and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
                raise ValueError('Private listening preference permissions required')

    def read(self):
        self._check()
        return self.backend.read()  # Missing preference deliberately means True.

    def write(self, enabled):
        if type(enabled) is not bool:
            raise ValueError('Expected boolean monitoring choice')
        if not getattr(self._action, 'active', False):
            return  # System cancellation does not overwrite the user's choice.
        try:
            self._check()
            self.backend.write(enabled)
        except ValueError as exc:
            # The original cancel() catches OSError before continuing to stop
            # capture. A rejected preference must never interrupt that stop.
            raise OSError('Listening preference could not be saved safely') from exc

    @contextmanager
    def explicit_toggle(self):
        if getattr(self._action, 'active', False):
            raise RuntimeError('Listening preference action already active')
        self._action.active = True
        try:
            yield
        finally:
            self._action.active = False


def bind_automatic_listening(recording, business, pair):
    """Restore the production preference after the legacy paired RAM pause.

    Bind after business.bind_recording(), before AvatarRenderWorker. runtime
    start() already requires the validated startup HTTP Date clock sample;
    native first-swap activates that runtime. No per-tick network work is added.
    """
    runtime = business.runtime
    settings = getattr(recording, 'monitor_settings', None)
    if (runtime.config.data_origin != 'board' or business.character_pair is not pair
            or business.recording is not recording or pair is None
            or not isinstance(settings, ProductionMonitorChoice)
            or not getattr(recording, 'voice_first', False) or recording.early_listen
            or getattr(recording, '_production_listening_bound', False)):
        raise ValueError('Fresh production voice-first listening owner required')
    original_tick = recording._monitor_tick
    original_toggle = recording.handsfree_toggle
    original_cancel = recording.cancel
    # Current production policy: speech starts a turn without a wake phrase.
    # Keep the original acoustic admission, identity and playback boundaries.
    recording.wake_word_required = False

    def monitor_tick():
        if not recording.closed and recording.monitor_enabled:
            ready = runtime.started and not runtime.closed and pair.ready_now()
            if not ready:
                if recording.monitor_owned:
                    recording._finish_session('SERVICE_NOT_READY', 5.)
                recording.monitor_state = 'WAITING_SERVICE'
                recording.monitor_reason = 'BUSINESS_OR_NATIVE_NOT_READY'
                return
        return original_tick()  # Retains feedback/enabled/idle/cooldown checks.

    def handsfree_toggle():
        with settings.explicit_toggle():
            return original_toggle()

    def cancel():
        # Stop this turn first. Re-arm only a previously enabled listener;
        # explicit user pause and shutdown retain their original semantics.
        explicit = getattr(settings._action, 'active', False)
        rearm = (recording.monitor_enabled and not explicit and not recording.closed
                 and not getattr(recording, '_closing', False) and not runtime.closed)
        result = original_cancel()  # Exceptions propagate; never re-arm after failure.
        if (rearm and not getattr(settings._action, 'active', False)
                and not recording.closed and not getattr(recording, '_closing', False)
                and not runtime.closed):
            recording.monitor_enabled = True
            recording.cooldown_until = max(recording.cooldown_until, recording.clock() + .5)
            recording.monitor_state = 'WAITING_SERVICE'
            recording.monitor_reason = 'CURRENT_TURN_CANCELLED'
        return result

    recording._monitor_tick = monitor_tick
    recording.handsfree_toggle = handsfree_toggle
    recording.cancel = cancel
    recording._production_listening_bound = True
    try:
        recording.monitor_enabled = settings.read()
    except (OSError, ValueError, TypeError):
        recording.monitor_enabled = False
        recording.monitor_error = '聆听设置读取失败，已保持暂停'
        recording.monitor_reason = 'LISTENING_PREFERENCE_UNAVAILABLE'
    else:
        recording.monitor_reason = ('BUSINESS_OR_NATIVE_NOT_READY' if recording.monitor_enabled
                                    else 'EXPLICIT_USER_PAUSE')
    recording.monitor_state = 'WAITING_SERVICE' if recording.monitor_enabled else 'PAUSED'
    return recording
