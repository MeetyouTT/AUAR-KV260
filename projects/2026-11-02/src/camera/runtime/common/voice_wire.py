"""Voice reply metadata for the explicit conversation endpoint; ASR-only stays separate."""
import hashlib
import io
import math
import re
import wave

PROTOCOL='aura-voice-1'
REVISION='c5fdb5ccb189668d56333f77ba2629f4cd7535f4'
MAX_WAV=1500000

def voice_reply(value):
    if not isinstance(value,dict) or value.get('protocol')!=PROTOCOL:
        raise ValueError('Voice reply protocol mismatch')
    if value.get('source_kind')!='actual' or value.get('engine')!='omnivoice' or value.get('revision')!=REVISION:
        raise ValueError('Unverified voice engine or revision')
    if value.get('num_step')!=16:raise ValueError('Accepted voice requires 16 steps')
    text=value.get('reply_text')
    if not isinstance(text,str) or not 1<=len(text.strip())<=240 or any(ord(c)<32 for c in text):
        raise ValueError('Invalid spoken reply')
    if value.get('emotion') not in {'neutral','friendly','happy','sad'}:raise ValueError('Invalid voice emotion')
    sha=value.get('sha256')
    if not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha):raise ValueError('Invalid voice digest')
    if type(value.get('bytes')) is not int or not 44<=value['bytes']<=MAX_WAV:raise ValueError('Invalid WAV size')
    duration=value.get('duration_seconds')
    if type(duration) not in (int,float) or not math.isfinite(duration) or not 0<duration<=30:
        raise ValueError('Invalid voice duration')
    return dict(value,reply_text=text.strip())

def wav_payload(meta,raw):
    meta=voice_reply(meta)
    if len(raw)!=meta['bytes'] or hashlib.sha256(raw).hexdigest()!=meta['sha256']:
        raise ValueError('Voice WAV size/hash mismatch')
    with wave.open(io.BytesIO(raw),'rb') as audio:
        if (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())!=(24000,1,2):
            raise ValueError('Voice WAV must be 24kHz mono PCM16')
        if not 1<=audio.getnframes()<=720000 or abs(audio.getnframes()/24000-meta['duration_seconds'])>1/24000:
            raise ValueError('Voice WAV sample count/duration mismatch')
        if len(audio.readframes(audio.getnframes()))!=audio.getnframes()*2:raise ValueError('Truncated voice PCM')
    return meta
