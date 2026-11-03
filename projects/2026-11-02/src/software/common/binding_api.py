"""Strict local typed binding protocol; no generic signing operation."""
import base64,copy,json,re
from common.asr_wire import context
from common.speaker_visual import validate_visual

DECISION_FIELDS={'route','reply','attempt_id','board_text','reason','skip_legacy_device_command','unified_saved','personal_memory_allowed'}
GALLERY_FIELDS={'store_id','model_id','revision','source_kind'}
def token(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{48}',value):raise ValueError('Invalid identity exchange token')
    return value
def attempt(value):
    if not isinstance(value,str) or not re.fullmatch('(?:name-wait-)?[0-9a-f]{32}',value):raise ValueError('Invalid binding attempt')
    return value
def text(value,maximum=2000):
    if not isinstance(value,str) or not 0<len(value)<=maximum or '\0' in value:raise ValueError('Invalid bounded binding text')
    return value
def gallery(value,meta,visual):
    if value is None:return None
    if (not isinstance(value,dict) or not GALLERY_FIELDS<=set(value)<=GALLERY_FIELDS|{'identity_id','template_fingerprint'}
        or value['source_kind']!='actual' or type(value['revision']) is not int or value['revision']<0
        or not isinstance(value['store_id'],str) or not re.fullmatch('[A-Za-z0-9_-]{1,96}',value['store_id'])
        or not isinstance(value['model_id'],str) or not 1<=len(value['model_id'])<=160):raise ValueError('Invalid board gallery reference')
    if value.get('identity_id') is not None:
        if (not isinstance(value['identity_id'],str) or not re.fullmatch('[A-Za-z0-9_-]{1,96}',value['identity_id'])
            or not isinstance(value.get('template_fingerprint'),str) or not re.fullmatch('[0-9a-f]{64}',value['template_fingerprint'])):
            raise ValueError('Invalid original face template reference')
    elif 'template_fingerprint' in value:raise ValueError('Template fingerprint has no identity')
    v=validate_visual(visual,meta)
    if v['state']=='FACE_AT_CAPTURE_BOUNDARIES':
        e=v['evidence']
        if e['gallery_revision']!=value['revision'] or e['face_identity_id']!=value.get('identity_id'):raise ValueError('Board gallery belongs to a different captured face')
    return copy.deepcopy(value)
def decode_gallery_header(header,meta,visual):
    if header is None:return None
    from common.face_binding_wire import decode_gallery_header as decode
    return decode(header,meta)
def decision(value):
    if not isinstance(value,dict) or set(value)!=DECISION_FIELDS:raise ValueError('Invalid binding decision')
    if value['route'] not in ('ordinary','ordinary_skip_speaker','face_exchange','device_reply'):raise ValueError('Unknown binding route')
    if value['personal_memory_allowed'] is not False or type(value['unified_saved']) is not bool or type(value['skip_legacy_device_command']) is not bool:
        raise ValueError('Binding does not grant authorization')
    if value['skip_legacy_device_command']!=(value['route']!='ordinary'):raise ValueError('Binding route lost legacy skip guard')
    for key in ('reply','board_text'):
        if value[key] is not None:text(value[key])
    if value['attempt_id'] is not None:attempt(value['attempt_id'])
    if value['route']=='face_exchange' and (value['attempt_id'] is None or value['reply'] is not None):raise ValueError('Face route cannot be intercepted by device reply')
    return copy.deepcopy(value)
def response(value,meta):
    if not isinstance(value,dict) or set(value)!={'version','context','decision','binding_request','analysis_mode'} or type(value['version']) is not int or value['version']!=1:
        raise ValueError('Invalid binding response')
    if value['context']!=context(meta) or value['analysis_mode'] not in ('TRACKER','CONTROL_REUSED'):raise ValueError('Foreign binding response')
    decision(value['decision'])
    if value['decision']['route']=='face_exchange':
        request=value['binding_request']
        if (not isinstance(request,dict) or set(request)!={'version','attempt_id','origin_context','face_guard','name','board_text','confirmed_existing'}
           or type(request['version']) is not int or request['version']!=1 or type(request['confirmed_existing']) is not bool
           or request['attempt_id']!=value['decision']['attempt_id']):raise ValueError('Invalid board binding request')
        attempt(request['attempt_id']);context(request['origin_context']);text(request['board_text'])
        if not isinstance(request['name'],str) or len(request['name'])>80:raise ValueError('Invalid binding name')
        from common.face_binding_wire import validate_binding_request
        validate_binding_request(request,meta)
    elif value['binding_request'] is not None:raise ValueError('Unexpected board binding request')
    return copy.deepcopy(value)
