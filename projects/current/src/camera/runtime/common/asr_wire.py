"""Bounded ASR-only PCM exchange; separate from dialogue/media reply delivery."""
import base64
import hashlib
import json
import re

PROTOCOL='aura-asr-1'
MAX_PCM=640000
MAX_REPLY=32768
FIELDS={'protocol','board_boot_id','session_id','request_id','generation','capture_id',
        'sample_count','pcm_sha256','budget_ms'}


def context(value, pcm=None):
    if not isinstance(value,dict) or set(value)!=FIELDS or value.get('protocol')!=PROTOCOL:
        raise ValueError('ASR protocol/context mismatch')
    for key in ('board_boot_id','session_id','request_id','capture_id'):
        if not isinstance(value[key],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,96}',value[key]):
            raise ValueError('Invalid ASR identity: '+key)
    for key,low,high in (('generation',0,2**53-1),('sample_count',3200,320000),('budget_ms',500,120000)):
        if type(value[key]) is not int or not low<=value[key]<=high:raise ValueError('Invalid ASR '+key)
    if not isinstance(value['pcm_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',value['pcm_sha256']):
        raise ValueError('Invalid PCM digest')
    if pcm is not None and (not isinstance(pcm,bytes) or len(pcm)!=value['sample_count']*2
                            or hashlib.sha256(pcm).hexdigest()!=value['pcm_sha256']):
        raise ValueError('PCM length/digest mismatch')
    return dict(value)


def encode_context(value):
    return base64.b64encode(json.dumps(context(value),separators=(',',':')).encode()).decode('ascii')


def decode_context(header):
    if not isinstance(header,str) or len(header)>2048:raise ValueError('ASR context exceeds limit')
    return context(json.loads(base64.b64decode(header,validate=True)))


def response(value, expected):
    if not isinstance(value,dict) or value.get('context')!=context(expected):
        raise ValueError('ASR result belongs to another recording or generation')
    text=value.get('text')
    if not isinstance(text,str) or len(text)>4096 or '\x00' in text:raise ValueError('Invalid transcription text')
    if value.get('source_kind')!='actual':raise ValueError('Only actual recognition results are accepted')
    elapsed=value.get('recognition_ms')
    if type(elapsed) not in (float,int) or not 0<=elapsed<=120000:raise ValueError('Invalid recognition time')
    if not isinstance(value.get('model_id'),str) or not value['model_id'] or len(value['model_id'])>160:
        raise ValueError('ASR model identity is missing')
    return dict(value,text=text.strip())
