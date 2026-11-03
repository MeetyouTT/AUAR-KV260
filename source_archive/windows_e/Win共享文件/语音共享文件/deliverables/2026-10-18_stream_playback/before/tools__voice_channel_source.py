"""Host-only 27B token stream -> natural clauses -> existing OmniVoice16.

OmniVoice still synthesizes a complete clause. This is clause pipelining, not
native token-to-audio TTS. No voice model or inference is installed on KV260.
"""
import hashlib
import queue
import threading
import time
import wave
from pathlib import Path

from common.voice_channel import MAX_SAMPLES, PACKET_SAMPLES, ChannelWriter
from common.voice_wire import REVISION
from tools.dialogue_stream import OllamaReplyStream


class ClauseBuffer:
    def __init__(self):
        self.text = ''

    def feed(self, delta):
        self.text += delta
        pieces = []
        # A tiny filler and a short pause stay attached to the meaningful phrase.
        # Never split arbitrary characters inside a number/name just to save time.
        while True:
            cut = next((i + 1 for i, c in enumerate(self.text)
                        if c in '，。！？；：' and i + 1 >= 8), None)
            if cut is None: break
            pieces.append(self.text[:cut])
            self.text = self.text[cut:]
        return pieces

    def finish(self):
        text, self.text = self.text, ''
        return [text] if text.strip() else []


def channel_frames(models, meta, text, timeout, *, model, host, stream_factory=OllamaReplyStream):
    """Yield validated wire frames; caller retains exclusive model ownership.

    Streaming history is deliberately not committed here: receiving bytes is
    not evidence that the user heard them. The old complete-WAV endpoint keeps
    its existing history behavior. Playback acknowledgement is a later UI step.
    """
    deadline = time.monotonic() + timeout
    owner = ChannelWriter(meta)
    history = list(models.histories.get((meta['board_boot_id'], meta['session_id']), []))
    yield owner.frame('start', context=meta, sample_rate=24000, channels=1, sample_width=2,
                      source_kind='actual', llm_model=model, engine='omnivoice', revision=REVISION,
                      num_step=16, synthesis_mode='full-clause', tone_control=False,
                      history_commit='awaiting_playback_integration')
    yield owner.frame('transcript', text=text)
    stream = stream_factory(host, model, history, text, max(.01, deadline-time.monotonic()))
    pending = queue.Queue(maxsize=8)
    stopped = threading.Event()

    def put(value):
        while not stopped.is_set():
            try:
                pending.put(value, timeout=.1)
                return
            except queue.Full:
                continue

    def read_llm():
        try:
            for kind, value in stream:
                if stopped.is_set(): return
                put((kind, value))
        except Exception as exc:
            put(('failure', exc))
        finally:
            put(('eof', None))

    thread = threading.Thread(target=read_llm, daemon=True, name='aura-27b-text-stream')
    thread.start()
    clause = ClauseBuffer()
    reply = None
    first_pcm_ms = None
    started = time.monotonic()
    last_heartbeat = started
    segment_id = 0
    first_text_ms = None
    timing = {}
    tts_total_ms = 0.0
    tts_cache_hits = 0

    def synthesize(part):
        nonlocal segment_id, first_pcm_ms, tts_total_ms, tts_cache_hits
        if time.monotonic() >= deadline: raise TimeoutError('Channel synthesis budget expired')
        before = time.monotonic()
        generated = models.voice.generate(part)
        tts_total_ms += (time.monotonic()-before)*1000
        tts_cache_hits += int(bool(generated.get('cache_hit')))
        if time.monotonic() >= deadline: raise TimeoutError('Channel synthesis budget expired')
        path = Path(generated['path'])
        if generated.get('sha256') != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError('Generated clause SHA256 mismatch')
        with wave.open(str(path), 'rb') as audio:
            if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (24000, 1, 2):
                raise ValueError('Clause must be 24kHz mono PCM16')
            if not 0 < audio.getnframes() <= MAX_SAMPLES - owner.state.samples:
                raise ValueError('Channel audio exceeds duration bound')
            while True:
                pcm = audio.readframes(PACKET_SAMPLES)
                if not pcm: break
                if first_pcm_ms is None: first_pcm_ms = round((time.monotonic()-started)*1000, 2)
                yield owner.frame('audio', pcm, start_sample=owner.state.samples,
                                  sha256=hashlib.sha256(pcm).hexdigest(), segment_id=segment_id,
                                  tts_ms=round((time.monotonic()-before)*1000, 2))
        segment_id += 1

    try:
        while True:
            if time.monotonic() >= deadline: raise TimeoutError('Voice channel budget expired')
            try:
                kind, value = pending.get(timeout=.1)
            except queue.Empty:
                if time.monotonic()-last_heartbeat >= 1:
                    yield owner.frame('heartbeat')
                    last_heartbeat = time.monotonic()
                continue
            if kind == 'failure': raise value
            if kind == 'text':
                if first_text_ms is None: first_text_ms=round((time.monotonic()-started)*1000,2)
                yield owner.frame('text', text=value)
                for part in clause.feed(value):
                    yield from synthesize(part)
            elif kind == 'complete':
                reply = value
                timing['llm_complete_observed_ms']=round((time.monotonic()-started)*1000,2)
                # The current schema may emit emotion after reply_text. It is
                # applied to subsequent audio, never retroactively to old samples.
                yield owner.frame('control', emotion=value['emotion'], action='',
                                  at_sample=owner.state.samples, tone_applied=False)
            elif kind == 'eof':
                if reply is None: raise ValueError('Incomplete LLM response')
                if reply['reply_text'] != owner.state.text:
                    raise ValueError('Streamed text differs from complete reply')
                for part in clause.finish():
                    yield from synthesize(part)
                yield owner.frame('end', reply_text=owner.state.text, sample_count=owner.state.samples,
                                  pcm_sha256=owner.state.digest.hexdigest(), first_pcm_ms=first_pcm_ms,
                                  first_text_ms=first_text_ms, timing=timing, clauses=segment_id,
                                  tts_total_ms=round(tts_total_ms,2), tts_cache_hits=tts_cache_hits,
                                  total_ms=round((time.monotonic()-started)*1000, 2))
                return
    except Exception as exc:
        if not owner.state.ended:
            yield owner.frame('error', error=(type(exc).__name__ + ': ' + str(exc))[:300])
    finally:
        stopped.set()
        stream.cancel()
        thread.join(timeout=1)


def serve_channel(handler, meta, text, timeout):
    """HTTP/1.1 chunking flushes frames immediately; old routes stay unchanged."""
    import socket
    from common.voice_channel import CONTENT_TYPE
    from tools.board_model_host import MODEL, OLLAMA_HOST
    handler.protocol_version = 'HTTP/1.1'
    handler.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    handler.send_response(200)
    handler.send_header('Content-Type', CONTENT_TYPE)
    handler.send_header('Transfer-Encoding', 'chunked')
    handler.send_header('Cache-Control', 'no-store')
    handler.send_header('Connection', 'keep-alive')
    handler.end_headers()
    frames = channel_frames(handler.server.models, meta, text, timeout, model=MODEL, host=OLLAMA_HOST)
    try:
        for frame in frames:
            handler.wfile.write(('%x\r\n' % len(frame)).encode('ascii') + frame + b'\r\n')
            handler.wfile.flush()
        handler.wfile.write(b'0\r\n\r\n')
        handler.wfile.flush()
        handler.close_connection = False
    except OSError:
        handler.close_connection = True
    finally:
        frames.close()
