"""Bounded face-only feature protocol; exact image, model, frame and owner binding."""
import base64
import hashlib
import json
import math
import re
import struct

PROTOCOL='aura-face-feature-1'
MODEL_ID='sface-2021dec-0ba9fbfa01b5'
MODEL_SHA='0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79'
MAX_PNG=65536

def checked_meta(value,png=None):
    keys={'protocol','model_id','request_id','target','frame_id','captured_mono_ms','sha256'}
    if not isinstance(value,dict) or set(value)!=keys or value['protocol']!=PROTOCOL or value['model_id']!=MODEL_ID:
        raise ValueError('Invalid face feature protocol/model')
    if not re.fullmatch('[0-9a-f]{32}',str(value['request_id'])) or not re.fullmatch('[0-9a-f]{64}',str(value['sha256'])):
        raise ValueError('Invalid face feature identifiers')
    target=value['target']
    if (not isinstance(target,dict) or set(target)!={'camera_epoch','track_id','track_generation'}
            or not isinstance(target['camera_epoch'],str) or not 1<=len(target['camera_epoch'])<=96
            or any(type(target[k]) is not int or not 1<=target[k]<2**53 for k in ('track_id','track_generation'))):
        raise ValueError('Invalid face owner')
    if any(type(value[k]) is not int or not 1<=value[k]<2**53 for k in ('frame_id','captured_mono_ms')):
        raise ValueError('Invalid face source frame')
    if png is not None:
        checked_png(png)
        if hashlib.sha256(png).hexdigest()!=value['sha256']:raise ValueError('Face PNG digest mismatch')
    return value

def checked_png(raw):
    if (not isinstance(raw,bytes) or not 24<=len(raw)<=MAX_PNG or raw[:8]!=b'\x89PNG\r\n\x1a\n'
            or raw[12:16]!=b'IHDR' or struct.unpack('!II',raw[16:24])!=(112,112)):
        raise ValueError('Expected bounded 112x112 face PNG')

def encode_meta(value):
    checked_meta(value)
    return base64.urlsafe_b64encode(json.dumps(value,separators=(',',':')).encode()).decode()

def decode_meta(raw):
    if not isinstance(raw,str) or len(raw)>4096:raise ValueError('Invalid face header')
    return checked_meta(json.loads(base64.b64decode(raw.encode(),altchars=b'-_',validate=True)))

def checked_reply(reply,meta):
    if (not isinstance(reply,dict) or set(reply)!={'context','embedding','inference_ms','backend'}
            or reply['context']!=meta or reply['backend']!='WINDOWS_CPU_SFACE_ORT'
            or type(reply['inference_ms']) not in (int,float) or not math.isfinite(reply['inference_ms'])
            or not 0<=reply['inference_ms']<=5000):raise ValueError('Mismatched face feature response')
    vector=reply['embedding']
    if (not isinstance(vector,list) or len(vector)!=128 or any(type(x) not in (int,float) or not math.isfinite(x) for x in vector)
            or sum(x*x for x in vector)<=1e-12):raise ValueError('Invalid SFace vector')
    return tuple(vector)
