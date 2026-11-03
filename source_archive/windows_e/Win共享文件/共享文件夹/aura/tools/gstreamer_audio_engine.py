"""GStreamer sink position, explicit MCP01 conversion and generation guards.

Gst is injected so lifecycle/error/generation behavior can be tested without
loading a native library or opening a device. Only the worker loads Gst.
"""
import hashlib
from pathlib import Path
import time
import wave

OUTPUT_CAPS = 'audio/x-raw,format=S16LE,layout=interleaved,rate=48000,channels=2'
REQUIRED_ELEMENTS = ('filesrc', 'wavparse', 'audioconvert', 'audioresample', 'capsfilter', 'alsasink')


def validate_clip(path, expected_sha256):
    path = Path(path).resolve(strict=True)
    if not expected_sha256 or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError('Cached WAV SHA256 mismatch')
    with wave.open(str(path), 'rb') as stream:
        if (stream.getframerate(), stream.getnchannels(), stream.getsampwidth()) != (24000, 1, 2):
            raise ValueError('Expected selected-voice 24kHz mono PCM16 WAV')
        if stream.getnframes() <= 0:
            raise ValueError('Empty cached WAV')
        duration = stream.getnframes() / 24000.0
    return path, duration


def build_pipeline(gst, path, device):
    pipeline = gst.Pipeline.new('aura-selected-voice')
    if pipeline is None:
        raise RuntimeError('Cannot create GStreamer pipeline')
    elements = []
    try:
        for factory in REQUIRED_ELEMENTS:
            element = gst.ElementFactory.make(factory, factory)
            if element is None:
                raise RuntimeError('Missing GStreamer element: ' + factory)
            pipeline.add(element)
            elements.append(element)
        source, parser, convert, resample, caps, sink = elements
        source.set_property('location', str(path))
        caps.set_property('caps', gst.Caps.from_string(OUTPUT_CAPS))
        sink.set_property('device', device)
        sink.set_property('sync', True)
        sink.set_property('buffer-time', 80000)
        sink.set_property('latency-time', 10000)
        for left, right in zip(elements, elements[1:]):
            if not left.link(right):
                raise RuntimeError('Cannot link cached WAV playback elements')
        return pipeline, sink
    except Exception:
        pipeline.set_state(gst.State.NULL)
        raise


class GstAudioEngine:
    def __init__(self, gst, device, *, clock=time.monotonic, pipeline_factory=build_pipeline):
        self.gst, self.device, self.clock = gst, device, clock
        self.pipeline_factory = pipeline_factory
        self.pipeline = self.sink = self.bus = None
        self.token = 0
        self.duration = self.position = 0.0
        self.ready = self.done = self.paused = False
        self.error = ''
        self.started_at = None
        self.requested_at = None

    def release(self):
        if self.pipeline is not None:
            self.pipeline.set_state(self.gst.State.NULL)
        self.pipeline = self.sink = self.bus = None
        self.ready = False

    def fail(self, error):
        self.error = str(error)
        self.done = False
        self.release()

    def command(self, message):
        token = message.get('token')
        if not isinstance(token, int) or isinstance(token, bool) or token < self.token:
            return False
        kind = message.get('type')
        if kind == 'pause':
            if token != self.token or self.pipeline is None:
                return False
            # Preserve the last sink query before freezing the published clock.
            self.poll()
            if self.pipeline is None:
                return False
            self.paused = bool(message.get('paused'))
            if not self.paused and not self.ready:
                self.requested_at = self.clock()
            state = self.gst.State.PAUSED if self.paused else self.gst.State.PLAYING
            if self.pipeline.set_state(state) == self.gst.StateChangeReturn.FAILURE:
                self.fail('Audio pause/resume failed')
            return True
        if kind not in ('play', 'stop', 'close'):
            raise ValueError('Unknown audio command')
        self.release()
        self.token = token
        self.ready = self.done = self.paused = False
        self.error = ''
        self.started_at = self.requested_at = None
        if kind != 'play':
            return True
        self.position = self.duration = 0.0
        try:
            path, self.duration = validate_clip(message['path'], message.get('sha256'))
            self.pipeline, self.sink = self.pipeline_factory(self.gst, path, self.device)
            self.bus = self.pipeline.get_bus()
            self.requested_at = self.clock()
            if self.pipeline.set_state(self.gst.State.PLAYING) == self.gst.StateChangeReturn.FAILURE:
                raise RuntimeError('MCP01 playback device failed to start')
        except Exception as exc:
            self.fail(type(exc).__name__ + ': ' + str(exc))
        return True

    def poll(self):
        if self.pipeline is None:
            return self.snapshot()
        gst = self.gst
        mask = gst.MessageType.ERROR | gst.MessageType.EOS
        for _ in range(16):
            message = self.bus.timed_pop_filtered(0, mask)
            if message is None:
                break
            if message.type == gst.MessageType.ERROR:
                error, debug = message.parse_error()
                self.fail(str(error))
                return self.snapshot()
            if message.type == gst.MessageType.EOS:
                self.position = self.duration
                self.done = True
                self.release()
                return self.snapshot()
        result, state, pending = self.pipeline.get_state(0)
        if result == gst.StateChangeReturn.FAILURE:
            self.fail('Audio state change failed')
            return self.snapshot()
        if not self.paused and state == gst.State.PLAYING:
            ok, value = self.sink.query_position(gst.Format.TIME)
            if ok and value >= 0:
                self.position = min(self.duration, max(self.position, value / gst.SECOND))
                if not self.ready:
                    self.ready = True
                    self.started_at = self.clock()
        if not self.ready and not self.paused and self.requested_at is not None and self.clock() - self.requested_at > 8:
            self.fail('Audio device preroll/position timed out')
        return self.snapshot()

    def snapshot(self):
        return {'token': self.token, 'ready': self.ready, 'clock': self.position,
                'done': self.done, 'error': self.error, 'started_at': self.started_at,
                'device_state': ('ERROR' if self.error else 'EOS' if self.done else
                                 'PAUSED' if self.paused and self.pipeline is not None else
                                 'PLAYING' if self.ready else 'STARTING' if self.pipeline is not None else 'NULL'),
                'clock_source': 'GStreamer ALSA sink position query', 'output_caps': OUTPUT_CAPS,
                'device': self.device}
