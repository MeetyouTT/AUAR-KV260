"""Verify the offline review with synthetic face-only bytes, never camera photos."""
import base64
import json
import sys
import tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'aura'))
from board.identity.photo_archive import EnrollmentPhotoArchive
from tests.framework.test_face_features import png
from export_latest import save_review

with tempfile.TemporaryDirectory() as temporary:
    root=Path(temporary)
    archive=EnrollmentPhotoArchive({'enabled':True,'directory':str(root/'source'),'max_images_per_session':192})
    sid='b'*32
    assert archive.begin(sid,14,.8,.1,'frontal_medoid_v1')
    pose={'yaw':0.,'roll':0.,'pixels':100.,'eye_distance':40.,'blur':200.}
    rows=[{'fid':i,'stamp':1000+i*700,'face_png':png()} for i in range(1,8)]
    for row in rows:
        assert archive.sample(sid,row,pose,'collect' if row['fid']<3 else 'validation_pass')
    assert archive.select(sid,rows[1])
    assert archive.validated(sid,[3,4,5,6,7],[.92]*5)
    assert archive.finish(sid,'committed',15)
    folder=archive.root/sid
    manifest=json.loads((folder/'manifest.json').read_text())
    names=[row['filename'] for row in manifest['images']]+[manifest['selected']['filename']]
    payload={'manifest':manifest,'files':{name:base64.b64encode((folder/name).read_bytes()).decode() for name in names}}
    report=save_review(payload,root/'review')
    assert report['image_count']==7 and len(report['validation_images'])==5
    assert Path(report['selected']).read_bytes()==(folder/'selected.png').read_bytes()
    page=Path(report['gallery']).read_text(encoding='utf-8')
    assert page.count('最终独立验证图')==5 and page.count('最终选中模板')==1
    payload['manifest']['session_id']='../escape'
    try:
        save_review(payload,root/'review')
    except ValueError:
        pass
    else:
        raise AssertionError('Unsafe path accepted')
    result={'status':'PASS_SYNTHETIC_GALLERY_EXPORT','image_count':7,
        'selected_png_bytes_preserved':True,'final_validation_labels':5,'unsafe_path_rejected':True,
        'actual_user_photos_used':False}
(HERE/'review_export_test.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
