"""Bounded RGB portrait packets. No speech, audio, file paths or executable data."""
import json
import math
import re
import struct
import zlib

PROTOCOL='aura-portrait-1'
MAX_HEADER=8192
MAX_RGB=1024*600*3
STATES=frozenset(('IDLE','PRESENT','LISTENING','THINKING','SPEAKING','SPEAKING_NEUTRAL',
    'SPEAKING_LOW','AWAKE','PUZZLED','ACK_NOD','DENY_SHAKE','CAMERA_LOST','NETWORK_LOST','CANCELLED','ERROR'))
EMOTIONS=frozenset(('neutral','friendly','happy','excited','sad','low'))

def integer(value,low,high):
    if type(value) is not int or not low<=value<=high:raise ValueError('Invalid integer')
    return value

def number(value,low,high):
    if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:
        raise ValueError('Invalid number')
    return value

def identifier(value):
    if not isinstance(value,str) or not re.fullmatch('[a-zA-Z0-9_-]{1,80}',value):raise ValueError('Invalid owner')
    return value

def plan(value):
    required={'protocol','kind','session','generation','sequence','state','clock','gain','level','idle_gain',
              'emotion','characters','audio_sample','track','width','height','revision'}
    if set(value)!=required or value.get('protocol')!=PROTOCOL or value.get('kind')!='render':raise ValueError('Invalid render plan')
    identifier(value['session']);identifier(value['revision'])
    integer(value['generation'],0,2**53);integer(value['sequence'],1,2**53)
    if value['state'] not in STATES or value['emotion'] not in EMOTIONS:raise ValueError('Unsupported portrait state')
    number(value['clock'],0,10**10);number(value['gain'],0,1);number(value['level'],0,1);number(value['idle_gain'],0,2)
    integer(value['characters'],0,8000);integer(value['audio_sample'],0,2**53)
    if value['track'] not in ('none','answer','feedback'):raise ValueError('Invalid audio track')
    integer(value['width'],1,1024);integer(value['height'],1,600)
    return value

def owner(value):return value['session'],value['generation'],value['state'],value['track']

def exact(connection,length):
    data=bytearray(length);view=memoryview(data);offset=0
    while offset<length:
        count=connection.recv_into(view[offset:])
        if not count:raise EOFError('Portrait connection ended')
        offset+=count
    return bytes(data)

def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate header key')
        result[key]=value
    return result

def send(connection,header,payload=b''):
    if len(payload)>MAX_RGB:raise ValueError('Portrait payload too large')
    header=dict(header,payload_bytes=len(payload),crc32='%08x'%(zlib.crc32(payload)&0xffffffff))
    raw=json.dumps(header,separators=(',',':'),allow_nan=False).encode('utf-8')
    if len(raw)>MAX_HEADER:raise ValueError('Portrait header too large')
    connection.sendall(struct.pack('!I',len(raw))+raw+payload)

def receive(connection,expected_bytes=None):
    length=struct.unpack('!I',exact(connection,4))[0]
    if not 1<=length<=MAX_HEADER:raise ValueError('Invalid portrait header size')
    value=json.loads(exact(connection,length).decode('utf-8'),object_pairs_hook=unique)
    if not isinstance(value,dict):raise ValueError('Expected portrait object')
    amount=integer(value.pop('payload_bytes',None),0,MAX_RGB);checksum=value.pop('crc32',None)
    if not isinstance(checksum,str) or not re.fullmatch('[0-9a-f]{8}',checksum):raise ValueError('Invalid portrait CRC')
    if expected_bytes is not None and amount!=expected_bytes:raise ValueError('Unexpected portrait payload size')
    data=exact(connection,amount)
    if '%08x'%(zlib.crc32(data)&0xffffffff)!=checksum:raise ValueError('Portrait CRC mismatch')
    return value,data

def frame(value,payload,request):
    required={'protocol','kind','session','generation','sequence','state','clock','audio_sample','track','revision','width','height',
              'asset','index','display_state','transitioning','mouth_level','speech_gain','burst_finished','render_ms'}
    if set(value)!=required or value.get('protocol')!=PROTOCOL or value.get('kind')!='frame':raise ValueError('Invalid portrait frame')
    for key in ('session','generation','sequence','state','clock','audio_sample','track','revision','width','height'):
        if type(value[key]) is not type(request[key]) or value[key]!=request[key]:raise ValueError('Portrait frame owner mismatch: '+key)
    if len(payload)!=request['width']*request['height']*3:raise ValueError('Invalid RGB length')
    if not isinstance(value['asset'],str) or not re.fullmatch('[a-zA-Z0-9_-]{1,80}',value['asset']):raise ValueError('Invalid asset')
    integer(value['index'],0,100000);number(value['render_ms'],0,10000)
    if value['display_state'] not in STATES:raise ValueError('Invalid display state')
    for key in ('transitioning','burst_finished'):
        if type(value[key]) is not bool:raise ValueError('Invalid portrait flag')
    number(value['mouth_level'],0,1);number(value['speech_gain'],0,1)
    return value
