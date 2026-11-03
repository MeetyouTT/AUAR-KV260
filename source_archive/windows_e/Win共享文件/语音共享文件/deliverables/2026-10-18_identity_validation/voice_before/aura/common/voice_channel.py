"""Ordered binary PCM/control frames inside a single HTTP response.

No model code, playback, or board hardware dependencies. A frame is an 8-byte
network-order length pair, bounded UTF-8 JSON, then optional raw PCM16 bytes.
"""
import hashlib
import json
import struct

PROTOCOL = 'aura-channel-1'
CONTENT_TYPE = 'application/x-aura-channel'
MAX_HEADER = 4096
PACKET_SAMPLES = 480  # 20ms at 24kHz; the final packet may be shorter.
MAX_SAMPLES = 720000
KINDS = {'start', 'transcript', 'text', 'control', 'audio', 'end', 'error', 'heartbeat', 'thinking'}


def encode_frame(header, payload=b''):
    if not isinstance(header, dict) or not isinstance(payload, bytes):
        raise ValueError('Expected header object and PCM bytes')
    raw = json.dumps(header, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')
    if not 1 <= len(raw) <= MAX_HEADER or len(payload) > PACKET_SAMPLES * 2:
        raise ValueError('Channel frame exceeds bounds')
    return struct.pack('!II', len(raw), len(payload)) + raw + payload


def _exact(stream, count):
    chunks = bytearray()
    while len(chunks) < count:
        value = stream.read(count - len(chunks))
        if not value:
            raise EOFError('Truncated voice channel')
        chunks.extend(value)
    return bytes(chunks)


def read_frame(stream):
    header_size, pcm_size = struct.unpack('!II', _exact(stream, 8))
    if not 1 <= header_size <= MAX_HEADER or pcm_size > PACKET_SAMPLES * 2:
        raise ValueError('Invalid channel frame lengths')
    header = json.loads(_exact(stream, header_size).decode('utf-8'))
    if not isinstance(header, dict):
        raise ValueError('Invalid channel header')
    return header, _exact(stream, pcm_size) if pcm_size else b''


class ChannelState:
    """Validate each packet before delivering it to playback/control callbacks."""
    def __init__(self, owner):
        from common.asr_wire import context
        self.owner = context(owner)
        self.seq = self.samples = 0
        self.text = ''
        self.started = self.ended = False
        self.digest = hashlib.sha256()

    def accept(self, header, pcm=b''):
        if self.ended:
            raise ValueError('Frame after channel end')
        if (header.get('protocol') != PROTOCOL or header.get('request_id') != self.owner['request_id']
                or type(header.get('generation')) is not int
                or header['generation'] != self.owner['generation']
                or type(header.get('seq')) is not int or header['seq'] != self.seq):
            raise ValueError('Wrong channel owner or frame sequence')
        kind = header.get('kind')
        if kind not in KINDS or (not self.started and kind != 'start'):
            raise ValueError('Invalid channel event order')
        if kind != 'audio' and pcm:
            raise ValueError('PCM on a non-audio frame')
        if self.seq >= 4096:
            raise ValueError('Too many channel frames')
        if kind == 'start':
            if self.started or header.get('context') != self.owner:
                raise ValueError('Wrong channel start context')
            if (header.get('sample_rate'), header.get('channels'), header.get('sample_width')) != (24000, 1, 2):
                raise ValueError('Channel requires 24kHz mono PCM16')
            self.started = True
        elif kind in {'transcript', 'text'}:
            text = header.get('text')
            limit = 4096 if kind == 'transcript' else 240
            if not isinstance(text, str) or not 1 <= len(text) <= limit or any(ord(c) < 32 for c in text):
                raise ValueError('Invalid channel text')
            if kind == 'text':
                if len(self.text) + len(text) > 240:
                    raise ValueError('Spoken text exceeds limit')
                self.text += text
        elif kind == 'thinking':
            if header.get('feedback_id')!='thinking' or header.get('reason') not in {'complex','delayed'}:
                raise ValueError('Invalid thinking feedback event')
        elif kind == 'control':
            if (header.get('emotion') not in {'neutral', 'friendly', 'happy', 'sad'}
                    or header.get('action') not in {'', 'ack_nod', 'deny_shake'}
                    or type(header.get('at_sample')) is not int
                    or not 0 <= header['at_sample'] <= MAX_SAMPLES):
                raise ValueError('Invalid channel control')
        elif kind == 'audio':
            if (not pcm or len(pcm) % 2 or len(pcm) > PACKET_SAMPLES * 2
                    or type(header.get('start_sample')) is not int or header['start_sample'] != self.samples
                    or self.samples + len(pcm) // 2 > MAX_SAMPLES
                    or header.get('sha256') != hashlib.sha256(pcm).hexdigest()):
                raise ValueError('Invalid PCM order, size or digest')
            self.digest.update(pcm)
            self.samples += len(pcm) // 2
        elif kind == 'end':
            if (type(header.get('sample_count')) is not int or header['sample_count'] != self.samples
                    or header.get('pcm_sha256') != self.digest.hexdigest()
                    or header.get('reply_text') != self.text):
                raise ValueError('Invalid channel completion')
            self.ended = True
        elif kind == 'error':
            if not isinstance(header.get('error'), str) or not 1 <= len(header['error']) <= 300:
                raise ValueError('Invalid channel error')
            self.ended = True
        self.seq += 1
        return header


class ChannelWriter:
    def __init__(self, owner):
        self.state = ChannelState(owner)

    def frame(self, kind, payload=b'', **fields):
        header = dict(fields, protocol=PROTOCOL, request_id=self.state.owner['request_id'],
                      generation=self.state.owner['generation'], seq=self.state.seq, kind=kind)
        self.state.accept(header, payload)
        return encode_frame(header, payload)
