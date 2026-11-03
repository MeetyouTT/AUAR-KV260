"""Strict16fps candidate wrapper over the pinned, unchanged Yuki host ABI.

One GTK/EGL widget owns GLES. The existing audio/render owner offers only
bounded numeric controls. No audio device, network, PCM or identity access.
"""
import time
from tools import native_yuki as original
from tools.formal_yuki import PairRejected, scoped_function


class StrictLocalPortrait(original.LocalPortrait):
    candidate_fixed_native = True

    def __init__(self, output, *, clock=time.monotonic, fps=16):
        self._prepared = self._drawn = False
        self._minimum_generation = 0
        self.visible = False
        super().__init__(output, clock=clock, fps=16)

    @property
    def ready(self):
        return self._prepared and self._drawn and not self.closed

    @ready.setter
    def ready(self, value):
        self._prepared = bool(value)
        if not value:
            self._drawn = False

    def set_fps(self, value):
        if type(value) is not int or value != 16:
            raise PairRejected('Selected candidate requires16fps; no8fps fallback')
        return dict(fps=16)

    def set_enabled(self, value):
        if value is not True:
            raise PairRejected('Restore the whole idle renderer/persona bundle to roll back')
        return dict(enabled=True)

    def offer(self, core, now, gain, level, audio_sample, track):
        value = None
        if core.talk_gen >= self._minimum_generation:
            value = super().offer(core, now, gain, level, audio_sample, track)
        if value is None:
            # Never None: the current RealtimeController would otherwise run
            # old display_frame/PNG paths when a GL widget is not ready.
            return dict(_portrait_wait=True, _native_yuki=True, _portrait_burst=False)
        return value

    def invalidate(self):
        with self.lock:
            if self.identity is not None:
                self._minimum_generation = max(self._minimum_generation, self.identity[0]+1)
        super().invalidate()

    def reset_local_if_needed(self, core):
        raise PairRejected('Selected native candidate has no local PNG fallback')

    def status(self):
        value = super().status()
        value.update(mode='native' if self.ready else 'blocked', selected=True,
                     target_fps=16, fallback_fps=None, fallback_allowed=False,
                     backend='KV260 GLES2', candidate_pair=False, formal_pair=True)
        value.update(visible=self.visible, presentation_state='visible' if self.visible else 'hidden')
        return value


def prepare_portrait(runtime, config, output, source_hashes, pair):
    prepare = scoped_function(original.prepare_portrait, dict(LocalPortrait=StrictLocalPortrait))
    mailbox, checked = prepare(runtime, config, output, source_hashes)
    if checked is None:
        pair.fail('native_preparation_failed')
        raise PairRejected('Pinned native renderer resources failed validation')
    pair.attach_mailbox(mailbox)
    return mailbox, checked


def create_gl_area(config, mailbox, pair):
    def failed(error):
        pair.fail('native_renderer_failed')
    area = original.create_gl_area(config, mailbox, on_error=failed)
    area.frame_observer = pair.observe_native_frame
    def visible(value):
        with mailbox.lock:
            mailbox.visible = value
    area.connect('map', lambda *_: visible(True))
    # Normal navigation can hide the portrait while audio continues. The
    # original widget pauses its frame timer; this is not lost GL readiness.
    area.connect('unmap', lambda *_: visible(False))
    # The original adapter clears ready on unrealize without reporting an
    # error. Readiness loss must also invalidate the business/audio generation.
    area.connect('unrealize', lambda *_: pair.fail('native_unrealized'))
    return area


def display_status(mailbox):
    """Only real native swap timestamps; GTK refresh never counts as FPS."""
    now = time.monotonic()
    with mailbox.lock:
        stats = dict(mailbox.latest_stats)
        visible = mailbox.visible
    paint = stats.get('paint_at')
    return dict(stats, kind='native_yuki_egl', target_fps=16,
                age_ms=max(0., (now-paint)*1000) if isinstance(paint, (int, float)) else None,
                visible=visible, presentation_state='visible' if visible else 'hidden',
                frame_scheduling_active=visible and mailbox.ready, fallback_allowed=False)

