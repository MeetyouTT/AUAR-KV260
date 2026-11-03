"""Retain the exact existing face input and remove this request's full photos."""
import hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OUT=HERE/'enrollment_review'
review=json.loads((OUT/'review.json').read_text(encoding='utf-8'))
face=(OUT/'aligned.png').read_bytes();face_sha=hashlib.sha256(face).hexdigest()
assert review['token']=='aafc3f7a021c47108cbf023caffd31a4'
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import hashlib,json,os,sqlite3,sys
from pathlib import Path
import cv2,numpy as np
cv2.setNumThreads(2)
review=REVIEW
face_sha=FACE_SHA
directory=Path('/home/root/.local/share/aura/enrollment-review')/review['token']
assert directory.resolve()==directory and not directory.is_symlink()
candidate=json.loads((directory/'candidate.json').read_text());assert candidate['consent']=='USER_CONFIRMED_AND_COMMITTED'
face=(directory/'aligned.png').read_bytes();assert hashlib.sha256(face).hexdigest()==face_sha
old_photo_sha=candidate['photo_sha256'];full=directory/'review.png'
assert not full.is_symlink() and hashlib.sha256(full.read_bytes()).hexdigest()==old_photo_sha==review['photo_sha256']
db=Path(candidate['database']);before=hashlib.sha256(db.read_bytes()).hexdigest()
sys.path.insert(0,candidate['camera_runtime'])
from board.vision.reference_faces import SFaceCompat
camera_config=Path('/home/root/aura-identity-validation-20261018/candidate-d843e37e7d4a/camera_live_config/board_identity.json')
cfg=json.loads(camera_config.read_text());assert cfg['threshold']==.85
image=cv2.imdecode(np.frombuffer(face,np.uint8),cv2.IMREAD_COLOR);assert image.shape==(112,112,3)
vector=SFaceCompat(cfg['embedding_model']).feature(image).astype(np.float64);vector/=np.linalg.norm(vector)
assert float(vector@np.asarray(candidate['embedding'],np.float64))>.999999
connection=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True)
revision=connection.execute("SELECT value FROM metadata WHERE key='revision'").fetchone()[0]
raw=connection.execute('SELECT embedding FROM templates WHERE identity_id=? AND model_id=?',
 (candidate['identity_id'],candidate['model_id'])).fetchone()[0]
connection.close();stored=np.asarray(json.loads(raw),np.float64);stored/=np.linalg.norm(stored)
same_enrolled_input=float(vector@stored)>.999999
fd=os.open(str(directory/'face.png'),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,'wb') as stream:stream.write(face)
candidate.update(schema='aura-manual-enrollment-review-2',photo_scope='aligned_face_only',photo_file='face.png',
 photo_sha256=face_sha,registration_source_full_frame_sha256=old_photo_sha,full_frame_file_removed=True)
(directory/'candidate.json').write_text(json.dumps(candidate));(directory/'candidate.json').chmod(0o600)
receipt=json.loads((directory/'commit_receipt.json').read_text())
receipt.update(photo_scope='aligned_face_only',photo_file='face.png',photo_sha256=face_sha,
 registration_source_full_frame_sha256=old_photo_sha,full_frame_file_removed=True,retained_face_verified_against_enrolled_template=same_enrolled_input)
(directory/'commit_receipt.json').write_text(json.dumps(receipt,indent=2));(directory/'commit_receipt.json').chmod(0o600)
full.unlink()  # Exactly the full photo created for this request; no directory traversal.
assert hashlib.sha256(db.read_bytes()).hexdigest()==before
result={'status':'FACE_ONLY_PHOTO_RETAINED','photo_sha256':face_sha,'photo_dimensions':[112,112],
 'photo_file':'face.png','photo_scope':'aligned_face_only','board_full_frame_removed':True,
 'database_unchanged':True,'database_revision':revision,'threshold':cfg['threshold'],
 'face_matches_enrolled_template':same_enrolled_input,'templates_exported':False}
print(json.dumps(result))
'''.replace('REVIEW',repr(review),1).replace('FACE_SHA',repr(face_sha),1)
result=json.loads(ssh('python3 -B -',remote,timeout=35))
# All file operations are limited to two named images from this request.
assert OUT.resolve().parent==HERE.resolve() and not OUT.is_symlink()
(OUT/'face.png').write_bytes(face)
full=OUT/'review.png'
assert not full.is_symlink() and hashlib.sha256(full.read_bytes()).hexdigest()==review['photo_sha256']
full.unlink()
preview=OUT/'current_preview.jpg'
if preview.exists():
    meta=json.loads((OUT/'current_preview.json').read_text(encoding='utf-8'))
    assert not preview.is_symlink() and hashlib.sha256(preview.read_bytes()).hexdigest()==meta['image_sha256']
    preview.unlink();meta['full_frame_file_removed']=True
    (OUT/'current_preview.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
old_sha=review['photo_sha256']
review.update(photo_sha256=face_sha,photo_scope='aligned_face_only',photo_file='face.png',photo_dimensions=[112,112],
 registration_source_full_frame_sha256=old_sha,full_frame_file_removed=True)
(OUT/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
receipt=json.loads((OUT/'commit_receipt.json').read_text(encoding='utf-8'))
receipt.update(photo_sha256=face_sha,photo_scope='aligned_face_only',photo_file='face.png',
 registration_source_full_frame_sha256=old_sha,full_frame_file_removed=True,
 retained_face_verified_against_enrolled_template=result['face_matches_enrolled_template'])
(OUT/'commit_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
result.update(local_full_frame_images_removed=True)
(OUT/'face_only_cleanup.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
