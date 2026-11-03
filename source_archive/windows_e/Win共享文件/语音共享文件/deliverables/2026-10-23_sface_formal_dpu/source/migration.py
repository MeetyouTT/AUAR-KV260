"""Re-embed a proven existing enrollment into its separate INT8 model domain."""
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import subprocess
from types import SimpleNamespace


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized(values):
    values=tuple(float(v) for v in values)
    if len(values)!=128 or not all(math.isfinite(v) for v in values):raise ValueError('Invalid feature')
    norm=math.sqrt(sum(v*v for v in values))
    if norm<=1e-12:raise ValueError('Zero feature')
    return tuple(v/norm for v in values)


def cosine(a,b):return sum(x*y for x,y in zip(normalized(a),normalized(b)))


def archive_plan(config):
    """Read original metadata only. Names/vectors remain process-private."""
    path=Path(config['database']).expanduser();before=sha(path)
    con=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
    try:
        revision=con.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]
        rows=con.execute('SELECT i.id,i.name,t.embedding,t.model_id,t.dimension FROM identities i '
                         'JOIN templates t ON i.id=t.identity_id').fetchall()
    finally:con.close()
    if len(rows)!=1 or rows[0][3:]!=(config['model_id'],128):
        raise ValueError('This migration requires exactly one original bound identity')
    root=Path(config['enrollment_photos']['directory']).expanduser().resolve()
    matches=[]
    for p in root.glob('*/manifest.json'):
        if p.is_symlink():raise ValueError('Archive manifest redirects')
        doc=json.loads(p.read_text())
        if doc.get('outcome')=='committed' and doc.get('database_revision_after')==revision:matches.append((p,doc))
    if len(matches)!=1:raise ValueError('No unique committed archive for current database revision')
    manifest,doc=matches[0]
    if (doc.get('schema')!='aura-enrollment-photos-1' or doc.get('truncated')
            or doc.get('template_policy')!='frontal_medoid_v1'):
        raise ValueError('Unexpected original enrollment provenance')
    files={}
    for row in doc['images']+[doc['selected']]:
        filename=row['filename']
        if not re.fullmatch(r'(frame_[0-9]{10}|selected)\.png',filename):raise ValueError('Invalid image filename')
        image=manifest.parent/filename
        if image.is_symlink() or image.resolve().parent!=manifest.parent:raise ValueError('Archive image redirects')
        if sha(image)!=row['sha256']:raise ValueError('Archive image hash mismatch')
        files[filename]=(image,row)
    validation=doc['validation_frame_ids']
    if len(validation)!=5 or len(set(validation))!=5 or doc['selected']['frame_id'] in validation:
        raise ValueError('Five held-out validation frames must be distinct from selected template')
    probes=[]
    for fid in validation:
        matches=[v for v in files.values() if v[1]['frame_id']==fid and v[1].get('decision')=='validation_pass']
        if len(matches)!=1:raise ValueError('Missing held-out validation observation')
        probes.append(matches[0][0])
    return {'database':path,'database_sha256':before,'revision':revision,'person_id':rows[0][0],
            'display_name':rows[0][1],'old_vector':normalized(json.loads(rows[0][2])),
            'manifest':manifest,'manifest_sha256':sha(manifest),'selected':files['selected.png'][0],
            'selected_sha256':sha(files['selected.png'][0]),'probes':probes,'verified_images':len(files)}


def migrate(old_config_path,new_config_path,report_path,*,source_root):
    old=json.loads(Path(old_config_path).read_text());new=json.loads(Path(new_config_path).read_text())
    plan=archive_plan(old)
    from board.identity.model_store import check_artifact_configuration,open_dpu_store,MODEL_ID
    from board.vision.dpu_vision_runtime import PinnedRunner,sface_feature,FINGERPRINT
    from board.vision.reference_faces import SFaceCompat
    import cv2
    cv2.setNumThreads(1)
    check_artifact_configuration(new)
    if Path(new['database']).exists():raise ValueError('Refuse to overwrite migration database')
    state=subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','ActiveState','--value'],timeout=5).decode().strip()
    if state!='inactive':raise ValueError('Stop camera owner before offline migration')
    config_sha=sha(old_config_path)
    selected=cv2.imread(str(plan['selected']))
    if selected is None or selected.shape!=(112,112,3):raise ValueError('Invalid selected crop')
    original=SFaceCompat(old['embedding_model']).feature(selected)
    old_match=cosine(original,plan['old_vector'])
    if old_match<.99999:raise ValueError('Committed archive does not reproduce the stored original template')
    ownership=Path('/run/aura-person-dpu.lock').open('a+')
    runner=None
    try:
        fcntl.flock(ownership,fcntl.LOCK_EX|fcntl.LOCK_NB)
        owner=SimpleNamespace(fingerprint=FINGERPRINT,ownership=ownership)
        b=new['feature_backend'];runner=PinnedRunner(b['model'],b['manifest'],owner)
        feature=normalized(sface_feature(selected,runner));scores=[]
        for image_path in plan['probes']:
            image=cv2.imread(str(image_path))
            if image is None or image.shape!=(112,112,3):raise ValueError('Invalid validation crop')
            scores.append(cosine(sface_feature(image,runner),feature))
        # The experimental threshold is fixed before these probes. A failure
        # rejects the migration; it never fits a threshold to five positives.
        if any(score<new['threshold'] for score in scores):raise ValueError('INT8 held-out archived validation failed')
        if sha(old_config_path)!=config_sha or sha(plan['database'])!=plan['database_sha256']:
            raise ValueError('Original configuration/database changed during migration')
        store=open_dpu_store(new)
        try:
            store.enroll(plan['person_id'],plan['display_name'],feature,consent=True,expected_revision=0,max_people=1)
            if len(store.people())!=1:raise ValueError('Migration did not preserve the registered identity')
            for image_path in plan['probes']:
                match=store.match(normalized(sface_feature(cv2.imread(str(image_path)),runner)))
                if match.state!='KNOWN' or match.identity_id!=plan['person_id']:raise ValueError('Migrated store validation failed')
        finally:store.close()
        if sha(plan['database'])!=plan['database_sha256']:raise ValueError('Original store was modified')
        result={'passed':True,'scope':'REEMBED_EXISTING_CONFIRMED_ENROLLMENT_ARCHIVE',
          'model_id':MODEL_ID,'identities_migrated':1,'archive_verified_images':plan['verified_images'],
          'original_template_reproduced_cosine':old_match,'held_out_original_enrollment_frames':5,
          'held_out_int8_scores':scores,'threshold':new['threshold'],'ambiguity_margin':new['ambiguity_margin'],
          'threshold_scope':'experimental fixed 0.50; archived known-person probes checked; live unknown-person not validated',
          'original_database_sha256_before_after':plan['database_sha256'],
          'original_database_revision':plan['revision'],'archive_manifest_sha256':plan['manifest_sha256'],
          'selected_crop_sha256':plan['selected_sha256'],'new_database':new['database'],
          'stored_old_fp32_vectors_reused':False,'new_int8_vectors_saved_privately':True,
          'names_ids_images_embeddings_in_report':False,'actual_offline_native_jobs':11}
        Path(report_path).write_text(json.dumps(result,indent=2)+'\n')
        return result
    finally:
        if runner is not None:runner.close()
        ownership.close()
