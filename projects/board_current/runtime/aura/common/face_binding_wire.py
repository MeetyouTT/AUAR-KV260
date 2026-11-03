"""Bounded metadata only: no image, vector, display name or memory grant."""
import base64,copy,hashlib,json,re
from common.asr_wire import context
from board.interaction.ui_contract import target_key
from common.voice_enrollment import valid_name

MAX_PACKET=32768
MAX_HEADER=4096
MAX_PEOPLE=32

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')

def _identifier(value):
    return isinstance(value,str) and re.fullmatch('[A-Za-z0-9_-]{1,96}',value) is not None

def _digest(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None

def _current(value):
    if value is None:return None
    if (not isinstance(value,dict) or set(value)!={'identity_id','template_fingerprint'}
       or not _identifier(value['identity_id']) or not _digest(value['template_fingerprint'])):
        raise ValueError('Invalid current face gallery reference')
    return copy.deepcopy(value)

def validate_packet(value,meta=None):
    if (not isinstance(value,dict) or set(value)!={'version','context','gallery','current','inventory'}
       or type(value['version']) is not int or value['version']!=1 or len(canonical(value))>MAX_PACKET):
        raise ValueError('Invalid bounded gallery metadata packet')
    owner=context(value['context'])
    if meta is not None and owner!=context(meta):raise ValueError('Foreign gallery packet owner')
    gallery=value['gallery']
    if (not isinstance(gallery,dict) or set(gallery)!={'store_id','model_id','revision','source_kind'}
       or not _identifier(gallery['store_id']) or not isinstance(gallery['model_id'],str)
       or not 1<=len(gallery['model_id'])<=160 or any(ord(c)<32 for c in gallery['model_id'])
       or type(gallery['revision']) is not int or not 0<=gallery['revision']<=2**53-1
       or gallery['source_kind']!='actual'):
        raise ValueError('Invalid actual face gallery metadata')
    inventory=value['inventory']
    if not isinstance(inventory,list) or len(inventory)>MAX_PEOPLE:raise ValueError('Gallery inventory exceeds original limit')
    ids=[]
    for row in inventory:
        if not isinstance(row,list) or len(row)!=2 or not _identifier(row[0]) or not _digest(row[1]):
            raise ValueError('Invalid face template digest reference')
        ids.append(row[0])
    if ids!=sorted(set(ids)):raise ValueError('Face gallery inventory must be unique and sorted')
    current=_current(value['current'])
    if current is not None and [current['identity_id'],current['template_fingerprint']] not in inventory:
        raise ValueError('Current template missing from complete inventory')
    return copy.deepcopy(value)

def packet_sha256(value):return hashlib.sha256(canonical(validate_packet(value))).hexdigest()

def encode_gallery_header(packet,meta):
    packet=validate_packet(packet,meta)
    value=dict(version=1,context=context(meta),packet_sha256=packet_sha256(packet),current=packet['current'])
    header='v1:'+base64.urlsafe_b64encode(canonical(value)).decode('ascii')
    if len(header)>MAX_HEADER:raise ValueError('Face gallery header exceeds bound')
    return header

def decode_gallery_header(header,meta):
    if not isinstance(header,str) or not header.startswith('v1:') or len(header)>MAX_HEADER:
        raise ValueError('Invalid face gallery header')
    try:value=json.loads(base64.b64decode(header[3:],altchars=b'-_',validate=True))
    except (ValueError,TypeError,UnicodeError) as exc:raise ValueError('Invalid face gallery encoding') from exc
    if (not isinstance(value,dict) or set(value)!={'version','context','packet_sha256','current'}
       or type(value['version']) is not int or value['version']!=1 or value['context']!=context(meta)
       or not _digest(value['packet_sha256'])):raise ValueError('Foreign face gallery header')
    _current(value['current'])
    return copy.deepcopy(value)

def validate_binding_request(value,meta):
    fields={'version','attempt_id','origin_context','face_guard','name','board_text','confirmed_existing'}
    if (not isinstance(value,dict) or set(value)!=fields or type(value['version']) is not int
       or value['version']!=1 or len(canonical(value))>3000):raise ValueError('Invalid board binding request')
    origin=context(value['origin_context']);owner=context(meta);ticket=value['attempt_id']
    if (origin['board_boot_id']!=owner['board_boot_id'] or origin['session_id']!=owner['session_id']
       or origin['generation']>owner['generation']):raise ValueError('Foreign binding origin')
    waiting=isinstance(ticket,str) and re.fullmatch('name-wait-[0-9a-f]{32}',ticket) is not None
    if not waiting and (not isinstance(ticket,str) or re.fullmatch('[0-9a-f]{32}',ticket) is None):
        raise ValueError('Invalid binding attempt')
    if value['name'] in ('',None):
        if not waiting or value['confirmed_existing'] is not False:raise ValueError('Only name inquiry may omit name')
    elif waiting or not valid_name(value['name']):raise ValueError('Invalid binding name')
    if (type(value['confirmed_existing']) is not bool or not isinstance(value['board_text'],str)
       or not 1<=len(value['board_text'])<=160 or any(ord(c)<32 for c in value['board_text'])):
        raise ValueError('Invalid controlled board text')
    guard=value['face_guard']
    if not isinstance(guard,dict) or set(guard)!={'service_epoch','camera_epoch','target','gallery_revision','face_identity_id'}:
        raise ValueError('Invalid binding face owner')
    target=target_key(guard['target'])
    if (not _identifier(guard['service_epoch']) or not _identifier(guard['camera_epoch'])
       or target['camera_epoch']!=guard['camera_epoch'] or type(guard['gallery_revision']) is not int
       or not 0<=guard['gallery_revision']<=2**53-1
       or guard['face_identity_id'] is not None and not _identifier(guard['face_identity_id'])):
        raise ValueError('Invalid binding face lifecycle')
    if value['confirmed_existing'] and guard['face_identity_id'] is None:raise ValueError('No original known face for explicit reuse')
    return copy.deepcopy(value)
