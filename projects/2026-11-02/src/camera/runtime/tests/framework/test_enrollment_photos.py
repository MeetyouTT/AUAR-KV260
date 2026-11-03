"""Real face-only files, source attribution, cancellation and held-out frame labels."""
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from board.identity.photo_archive import EnrollmentPhotoArchive,configuration
from board.identity.sampling import EnrollmentSampling
from tests.framework.test_face_features import png

POSE={'yaw':0.,'roll':0.,'pixels':100.,'eye_distance':40.,'blur':200.}
OWNER={'camera_epoch':'camera','track_id':1,'track_generation':1}
SID='a'*32

class PhotoArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.config={'enabled':True,'directory':str(Path(self.temp.name)/'photos'),'max_images_per_session':192}
        self.a=EnrollmentPhotoArchive(self.config)

    def row(self,fid=1,raw=None):return {'fid':fid,'stamp':1000+fid*700,'face_png':png() if raw is None else raw,
        'embedding':(1.,0.),'target':dict(OWNER),'revision':0}
    def begin(self):self.assertTrue(self.a.begin(SID,0,.8,.1,'frontal_medoid_v1'))
    def manifest(self):return json.loads((self.a.root/SID/'manifest.json').read_text())

    def test_disabled_and_invalid_paths_never_create_photos(self):
        off=dict(self.config,enabled=False,directory=str(Path(self.temp.name)/'off'))
        a=EnrollmentPhotoArchive(off);self.assertFalse(a.begin(SID,0,.8,.1,'test'))
        self.assertFalse(a.root.exists())
        for config in (dict(self.config,directory='relative'),dict(self.config,max_images_per_session=999),
                       dict(self.config,enabled=1)):
            with self.assertRaises(ValueError):configuration(config)
        self.assertFalse(self.a.begin('../escape',0,.8,.1,'test'))

    def test_exact_png_selected_and_five_validation_labels_survive_restart(self):
        self.begin()
        for fid in range(1,8):self.assertTrue(self.a.sample(SID,self.row(fid),POSE,'collect'))
        self.assertTrue(self.a.select(SID,self.row(2)))
        self.assertTrue(self.a.validated(SID,[3,4,5,6,7],[.91]*5))
        self.assertTrue(self.a.finish(SID,'committed',1))
        m=self.manifest();self.assertEqual(m['outcome'],'committed');self.assertEqual(m['database_revision_after'],1)
        self.assertEqual(m['validation_frame_ids'],[3,4,5,6,7]);self.assertEqual(m['selected']['frame_id'],2)
        self.assertEqual((self.a.root/SID/'selected.png').read_bytes(),png())
        self.assertNotIn('embedding',json.dumps(m).replace('contains_embeddings_or_names',''))
        self.assertEqual(EnrollmentPhotoArchive(self.config).health()['image_count'],7)
        if os.name!='nt':self.assertEqual((self.a.root/SID/'selected.png').stat().st_mode&0o777,0o600)

    def test_full_frames_duplicates_and_stale_sessions_are_not_saved(self):
        self.begin();self.assertFalse(self.a.sample(SID,self.row(raw=png(640,480)),POSE,'collect'))
        self.assertEqual(list((self.a.root/SID).glob('*.png')),[])
        self.assertTrue(self.a.sample(SID,self.row(),POSE,'collect'))
        self.assertTrue(self.a.sample(SID,self.row(),POSE,'collect'))
        self.assertEqual(len(self.manifest()['images']),1)
        self.assertFalse(self.a.sample('b'*32,self.row(2),POSE,'collect'))
        self.a.finish(SID,'cancelled');self.assertFalse(self.a.sample(SID,self.row(2),POSE,'collect'))
        self.assertTrue((self.a.root/SID/'frame_0000000001.png').is_file())

    def test_bounds_keep_selected_photo_and_report_truncation(self):
        self.a=EnrollmentPhotoArchive(dict(self.config,max_images_per_session=8));self.begin()
        for fid in range(1,12):self.a.sample(SID,self.row(fid),POSE,'collect')
        self.a.select(SID,self.row(11));m=self.manifest()
        self.assertEqual(len(m['images']),8);self.assertTrue(m['truncated'])
        self.assertEqual(m['omitted_image_count'],3);self.assertEqual(m['selected']['frame_id'],11)
        self.assertTrue((self.a.root/SID/'selected.png').is_file())

    def test_io_failure_is_reported_and_does_not_change_identity_decisions(self):
        self.begin()
        with patch.object(self.a,'_atomic',side_effect=OSError('storage unavailable')):
            self.assertFalse(self.a.sample(SID,self.row(),POSE,'collect'))
        self.assertIn('storage unavailable',self.a.health()['error'])
        self.assertEqual(self.a.health()['error_count'],1)

    def test_sampling_saves_only_active_owned_faces_and_keeps_failed_attempts(self):
        now=[1000];s=EnrollmentSampling(.8,.1,lambda:now[0],self.a)
        s.offer(self.row(),POSE,None);self.assertIsNone(self.a.health()['latest_session'])
        s.start(OWNER,0,anchor=(1.,0.));sid=s.session_id
        row=self.row();row['stamp']=now[0]=1700;s.offer(row,POSE,None)
        other=self.row(2);other.update(stamp=2400,target=dict(OWNER,track_generation=2),embedding=(0.,1.))
        now[0]=2400;s.offer(other,POSE,None)
        self.assertEqual(self.a.health()['image_count'],1)
        s.fail('timeout');s.reset()
        self.assertEqual(json.loads((self.a.root/sid/'manifest.json').read_text())['outcome'],'failed')

    def test_only_the_last_successful_validation_run_is_marked_final(self):
        now=[1000];s=EnrollmentSampling(.8,.1,lambda:now[0],self.a);s.start(OWNER,0);sid=s.session_id
        fid=0
        def feed(vector=(1.,0.)):
            nonlocal fid
            fid+=1;now[0]+=700;row=self.row(fid);row.update(stamp=now[0],embedding=vector);s.offer(row,POSE,None)
        for _ in range(22):feed()
        feed();feed();feed((.7,math.sqrt(1-.7**2)))
        for _ in range(5):feed()
        self.assertEqual(s.stage,'ready');m=json.loads((self.a.root/sid/'manifest.json').read_text())
        self.assertEqual(m['validation_frame_ids'],list(range(fid-4,fid+1)))
        self.assertEqual(len(m['validation_scores']),5);s.reset(outcome='committed',revision=1)
        self.assertEqual(json.loads((self.a.root/sid/'manifest.json').read_text())['outcome'],'committed')

class PhotoArchiveIntegrationTests(unittest.TestCase):
    def test_formal_store_commit_finishes_archive_without_serializing_names_or_vectors(self):
        from tests.framework.test_enrollment_sampling import IntegrationTests
        case=IntegrationTests();case.setUp();self.addCleanup(case.doCleanups)
        with tempfile.TemporaryDirectory() as directory:
            a=EnrollmentPhotoArchive({'enabled':True,'directory':str(Path(directory)/'photos'),'max_images_per_session':192})
            case.c.service.photo_archive=a;case.c.service.sampling.photo_archive=a
            case.start();sid=case.c.service.sampling.session_id
            for _ in range(27):
                case.c.now+=700;fid=case.c.now;case.c.frame(fid=fid)
                extractor=case.fixture.Extractor((1.,0.,0.,0.));extractor.enrollment_quality=dict(POSE);extractor.preview_png=png()
                case.c.infer(extractor,fid)
            self.assertTrue(case.c.state.command(case.c.enrollment(cid='archive-commit'))['accepted'])
            m=json.loads((a.root/sid/'manifest.json').read_text())
            self.assertEqual(m['outcome'],'committed');self.assertEqual(m['database_revision_after'],1)
            self.assertEqual(len(m['validation_frame_ids']),5);self.assertEqual(len(m['images']),27)
            self.assertFalse(m['contains_embeddings_or_names'])

if __name__=='__main__':unittest.main()
