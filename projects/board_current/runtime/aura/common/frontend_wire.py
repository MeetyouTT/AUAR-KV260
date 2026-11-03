"""Bounded local-LAN frontend messages; no audio/text is logged or persisted."""
import ipaddress
import json
import re
import struct
import time

PROTOCOL='aura-audio-frontend-1'
DEFAULTS={'enabled':False,'host':'127.0.0.1','port':8795,'timeout_ms':180}


def configuration(value=None):
    if value is None:return dict(DEFAULTS)
    if not isinstance(value,dict) or set(value)!=set(DEFAULTS):raise ValueError('Invalid audio frontend configuration')
    if type(value['enabled']) is not bool:raise ValueError('Invalid frontend enabled flag')
    ipaddress.IPv4Address(value['host'])
    if type(value['port']) is not int or not 1024<=value['port']<=65535:raise ValueError('Invalid frontend port')
    if type(value['timeout_ms']) is not int or not 50<=value['timeout_ms']<=500:raise ValueError('Invalid frontend deadline')
    return dict(value)


def owner(meta,kind,stream,seq):
    if (not isinstance(meta,dict) or meta.get('protocol')!=PROTOCOL or meta.get('kind')!=kind
            or not isinstance(stream,str) or not re.fullmatch('[0-9a-f]{32}',stream)
            or meta.get('stream_id')!=stream or type(meta.get('sequence')) is not int or meta['sequence']!=seq):
        raise ValueError('Stale or invalid frontend owner')


def send(connection,meta,pcm=b''):
    raw=json.dumps(meta,allow_nan=False,separators=(',',':')).encode()
    if not 2<=len(raw)<=2048 or len(pcm) not in (0,640):raise ValueError('Frontend packet exceeds budget')
    connection.sendall(struct.pack('!II',len(raw),len(pcm))+raw+pcm)


def receive(connection,timeout):
    deadline=time.monotonic()+timeout
    def exact(n):
        result=bytearray()
        while len(result)<n:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('Frontend total packet deadline')
            connection.settimeout(remaining)
            part=connection.recv(n-len(result))
            if not part:raise ConnectionError('Frontend connection ended')
            result.extend(part)
        return bytes(result)
    size,audio_size=struct.unpack('!II',exact(8))
    if not 2<=size<=2048 or audio_size not in (0,640):raise ValueError('Invalid frontend packet lengths')
    meta=json.loads(exact(size))
    if not isinstance(meta,dict):raise ValueError('Invalid frontend metadata')
    return meta,exact(audio_size) if audio_size else b''
