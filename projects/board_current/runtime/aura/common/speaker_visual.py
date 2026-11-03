"""Bounded face observations at capture boundaries, never active-speaker proof."""
import base64,copy,json,re
from common.asr_wire import context

FIELDS={'version','context','source_kind','state','reason','evidence'}
EVIDENCE={'service_epoch','camera_epoch','target','gallery_revision','face_identity_id',
          'boundary_start_ms','boundary_end_ms','checked_ms','source_start_ms','source_end_ms','frame_start','frame_end'}

def unavailable(meta,reason='NO_VISUAL_EVIDENCE'):
    return dict(version=1,context=context(meta),source_kind='actual',state='UNAVAILABLE',reason=reason,evidence=None)

def _id(value):return isinstance(value,str) and bool(re.fullmatch(r'[A-Za-z0-9_-]{1,96}',value))
def _integer(value):return type(value) is int and 0<=value<2**53

def validate_visual(value,meta):
    expected=context(meta)
    if not isinstance(value,dict) or set(value)!=FIELDS or value.get('version')!=1 or type(value['version']) is not int:
        raise ValueError('Invalid speaker visual envelope')
    if value['context']!=expected or value['source_kind']!='actual':raise ValueError('Foreign visual owner')
    if not isinstance(value['reason'],str) or not re.fullmatch('[A-Z0-9_]{1,64}',value['reason']):raise ValueError('Invalid visual reason')
    if value['state']=='UNAVAILABLE':
        if value['evidence'] is not None:raise ValueError('Unavailable face must not carry an identity')
        return copy.deepcopy(value)
    if value['state']!='FACE_AT_CAPTURE_BOUNDARIES' or value['reason']!='NOT_ACTIVE_SPEAKER_PROOF':raise ValueError('Unsupported visual claim')
    e=value['evidence']
    if not isinstance(e,dict) or set(e)!=EVIDENCE:raise ValueError('Invalid face observation fields')
    from board.interaction.ui_contract import target_key
    target=target_key(e['target'])
    if not _id(e['service_epoch']) or not _id(e['camera_epoch']) or target['camera_epoch']!=e['camera_epoch']:
        raise ValueError('Foreign face lifecycle')
    if e['face_identity_id'] is not None and not _id(e['face_identity_id']):raise ValueError('Invalid observed face identity')
    if any(not _integer(e[k]) for k in EVIDENCE-{'service_epoch','camera_epoch','target','face_identity_id'}):
        raise ValueError('Invalid face time/frame/revision')
    if not (e['boundary_start_ms']<=e['boundary_end_ms']<=e['checked_ms']
            and e['checked_ms']-e['boundary_start_ms']<=120000
            and 0<=e['boundary_start_ms']-e['source_start_ms']<3000
            and 0<=e['checked_ms']-e['source_end_ms']<3000
            and e['source_start_ms']<e['source_end_ms']
            and 1<=e['frame_start']<e['frame_end']):raise ValueError('Expired or unordered face boundary evidence')
    return copy.deepcopy(value)

def build_visual(start,end,meta,now_ms):
    """Run on the board clock. Two observed endpoints do not prove who spoke."""
    context(meta)
    try:
        from board.interaction.ui_contract import validate_snapshot,target_key
        if type(now_ms) is not int:raise ValueError('No board clock')
        start=validate_snapshot(start,meta['board_boot_id'],start['observed_mono_ms'])
        end=validate_snapshot(end,meta['board_boot_id'],now_ms)
        if any(s['source_kind']!='actual' for s in (start,end)):return unavailable(meta,'UNVERIFIED_VISUAL_SOURCE')
        if start['service_epoch']!=end['service_epoch']:return unavailable(meta,'CAMERA_SERVICE_CHANGED')
        a,b=(s['modules']['identity'] for s in (start,end))
        if any(s['modules']['camera']['state']!='READY' for s in (start,end)):return unavailable(meta,'CAMERA_NOT_READY')
        if any(i.get('face_count',0)>1 for i in (a,b)):return unavailable(meta,'MULTIPLE_FACES')
        if any(i.get('target_kind')!='face' or i.get('face_count')!=1 or not i.get('face_target') for i in (a,b)):
            return unavailable(meta,'NO_SINGLE_FACE')
        target=target_key(a['face_target'])
        if target!=target_key(b['face_target']) or a['db_version']!=b['db_version']:return unavailable(meta,'FACE_LIFECYCLE_CHANGED')
        if any(s.get('preview',{}).get('camera_epoch')!=target['camera_epoch'] for s in (start,end)):
            return unavailable(meta,'CAMERA_EPOCH_CHANGED')
        person=None
        if a['state']=='KNOWN' and b['state']=='KNOWN':
            if a.get('person_id')!=b.get('person_id'):return unavailable(meta,'FACE_IDENTITY_CHANGED')
            person=b.get('person_id')
            if not person or any(not any(r['person_id']==person for r in i['people']) for i in (a,b)):
                return unavailable(meta,'FACE_IDENTITY_UNVERIFIED')
        def source(snapshot,identity):
            if identity['state']=='KNOWN':
                if identity.get('target')!=target:raise ValueError('Identity target is stale')
                fid,stamp=identity['source_frame_id'],identity['source_mono_ms']
                preview=identity.get('face_preview')
                if preview and (preview['target']!=target or preview['frame_id']!=fid
                        or preview['captured_mono_ms']!=stamp):raise ValueError('Face source differs from its crop')
                if snapshot['preview']['frame_id']<fid:raise ValueError('Face belongs to an unobserved frame')
                return fid,stamp
            preview=snapshot.get('preview',{})
            if preview.get('camera_epoch')!=target['camera_epoch']:raise ValueError('Camera epoch differs')
            return preview['frame_id'],preview['captured_mono_ms']
        first,first_ms=source(start,a);last,last_ms=source(end,b)
        evidence=dict(service_epoch=end['service_epoch'],camera_epoch=target['camera_epoch'],target=target,
          gallery_revision=b['db_version'],face_identity_id=person,boundary_start_ms=start['observed_mono_ms'],
          boundary_end_ms=end['observed_mono_ms'],checked_ms=now_ms,source_start_ms=first_ms,source_end_ms=last_ms,
          frame_start=first,frame_end=last)
        return validate_visual(dict(version=1,context=dict(meta),source_kind='actual',state='FACE_AT_CAPTURE_BOUNDARIES',
          reason='NOT_ACTIVE_SPEAKER_PROOF',evidence=evidence),meta)
    except (ValueError,KeyError,TypeError):return unavailable(meta,'VISUAL_STALE_OR_INVALID')

def encode_visual_header(value,meta):
    raw=json.dumps(validate_visual(value,meta),separators=(',',':')).encode()
    encoded=base64.b64encode(raw).decode('ascii')
    if len(encoded)>4096:raise ValueError('Speaker visual header too large')
    return encoded

def decode_visual_header(value,meta):
    if not isinstance(value,str) or not 1<=len(value)<=4096:raise ValueError('Invalid speaker visual header size')
    try:decoded=json.loads(base64.b64decode(value,validate=True))
    except (ValueError,UnicodeError,RecursionError) as exc:raise ValueError('Invalid speaker visual header') from exc
    return validate_visual(decoded,meta)
