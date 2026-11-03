"""Answer a direct question with a fresh observed face, never inferred speaker identity."""
from common import voice_enrollment as speech
from board.interaction.ui_contract import validate_snapshot,target_key


def answer_current_face(current,start,boot_id,now_ms):
    unavailable=lambda:speech.result('identity_unavailable')
    try:
        current=validate_snapshot(current,boot_id,now_ms)
        # capture_started already validated start with the board clock. Validate
        # its structure again at that instant, not at the later ASR reply time.
        start=validate_snapshot(start,boot_id,start['observed_mono_ms'])
        if any(s['source_kind']!='actual' for s in (current,start)):return unavailable()
        if (start['observed_mono_ms']>now_ms or now_ms-start['observed_mono_ms']>120000
                or current['service_epoch']!=start['service_epoch']):return unavailable()
        identity=current['modules']['identity'];previous=start['modules']['identity']
        if any(i.get('target_kind')!='face' for i in (identity,previous)):return unavailable()
        if any(i.get('face_count',0)>1 for i in (identity,previous)):
            return speech.result('identity_multiple')
        if any(i.get('face_count')!=1 or not i.get('face_target') for i in (identity,previous)):
            return unavailable()
        key=target_key(identity['face_target'])
        if (key!=target_key(previous['face_target']) or identity['db_version']!=previous['db_version']
                or current['modules']['camera']['state']!='READY'):return unavailable()
        if identity['state']=='ERROR':return unavailable()
        if identity['state']!='KNOWN':return speech.result('identity_unknown')
        fid,stamp=identity.get('source_frame_id'),identity.get('source_mono_ms')
        if (identity.get('target')!=key or type(fid) is not int or fid<1 or type(stamp) is not int
                or not 0<=now_ms-stamp<3000):return unavailable()
        ref=identity.get('face_preview')
        if ref and (ref['target']!=key or ref['frame_id']!=fid or ref['captured_mono_ms']!=stamp
                or not 0<=now_ms-stamp<min(3000,ref['ttl_ms'])):return unavailable()
        person,name=identity.get('person_id'),identity.get('display_name')
        if (not person or not speech.valid_name(name) or not any(row['person_id']==person
                and row['display_name']==name for row in identity['people'])):return unavailable()
        if previous['state']=='KNOWN' and previous.get('person_id')!=person:return unavailable()
        return speech.result('identity_seen',name)
    except (ValueError,KeyError,TypeError):return unavailable()
