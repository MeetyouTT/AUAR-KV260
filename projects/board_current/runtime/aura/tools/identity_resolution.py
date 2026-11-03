"""Construct naming proofs only from original matcher results and private metadata."""
import hashlib
from common.asr_wire import context
from common.speaker_visual import validate_visual

def voice_proof(device,meta,voice,*,store_id,now):
    """Conservative default: three distinct field-calibrated matches, no profile grant."""
    context(meta)
    if (not device.calibrated or voice.get('field_calibrated') is not True or voice.get('state')!='CANDIDATE_STABLE'
       or voice.get('consecutive_distinct')!=3 or voice.get('gallery_revision')!=device.store.revision
       or voice.get('model_id')!=device.encoder.model_id):return None
    identity=voice.get('candidate_id')
    if not any(p['person_id']==identity for p in device.store.people()):return None
    row=device.store.db.execute('SELECT embedding FROM templates WHERE identity_id=? AND model_id=?',(identity,device.encoder.model_id)).fetchone()
    if row is None:return None
    return dict(context=dict(meta),modality='voice',store_id=store_id,source_kind='actual',match_state='KNOWN',original_matcher_accepted=True,
      field_calibrated=True,identity_id=identity,model_id=device.encoder.model_id,gallery_revision=device.store.revision,
      template_fingerprint=hashlib.sha256(row[0].encode()).hexdigest(),observed_at=now,expires_at=now+2)

def face_proof(meta,visual,gallery,*,now):
    """gallery must be fresh board-store metadata, not a guessed same-name link."""
    value=validate_visual(visual,meta)
    if value['state']!='FACE_AT_CAPTURE_BOUNDARIES' or value['evidence']['face_identity_id'] is None:return None
    identity=value['evidence']['face_identity_id']
    if (not isinstance(gallery,dict) or gallery.get('identity_id')!=identity
        or gallery.get('revision')!=value['evidence']['gallery_revision'] or gallery.get('source_kind')!='actual'):
        return None
    return dict(context=context(meta),modality='face',source_kind='actual',match_state='KNOWN',original_matcher_accepted=True,
      store_id=gallery['store_id'],identity_id=identity,model_id=gallery['model_id'],gallery_revision=gallery['revision'],
      template_fingerprint=gallery.get('template_fingerprint'),observed_at=now,expires_at=now+2)
