"""Enrollment quality, held-out validation and real temporary-store commands."""
import copy
import math
import unittest
from board.identity.sampling import EnrollmentSampling, pose_quality


QUALITY={'yaw':0.,'roll':0.,'pixels':100.,'eye_distance':40.,'blur':200.}
OWNER={'camera_epoch':'camera','track_id':1,'track_generation':1}


class SamplingTests(unittest.TestCase):
    def setUp(self):
        self.now=1000;self.fid=0
        self.s=EnrollmentSampling(.85,.1,lambda:self.now);self.s.start(OWNER,0)

    def feed(self,yaw=0.,vector=(1.,0.),other=None,**quality):
        self.now+=700;self.fid+=1
        row={'fid':self.fid,'stamp':self.now,'target':copy.deepcopy(OWNER),'revision':0,
             'embedding':vector,'face_png':b'RAM-only'}
        q=dict(QUALITY,yaw=yaw,**quality);self.s.offer(row,q,other);return row,q

    def train(self):
        for yaw in [0.]*4+[-.1]*3+[.1]*3:self.feed(yaw)

    def test_ten_training_frames_then_five_different_validation_frames(self):
        self.train();self.assertEqual(self.s.stage,'validate');candidate=self.s.candidate['fid']
        for i in range(4):self.feed(vector=(.9,math.sqrt(1-.9**2)))
        self.assertEqual(self.s.stage,'validate');self.feed(vector=(.9,math.sqrt(1-.9**2)))
        self.assertEqual(self.s.stage,'ready');self.assertLessEqual(candidate,10)
        self.assertEqual(self.s.candidate['embedding'],(1.,0.));self.assertEqual(len(self.s.validation_scores),5)
        self.assertEqual(self.s.public()['counts'],{'front':4,'left':3,'right':3,'validate':5})
        self.assertNotIn('embedding',repr(self.s.public()));self.assertEqual(self.s.training,[])

    def test_one_low_score_fails_without_weakening_point85(self):
        self.train();self.feed(vector=(.8499,math.sqrt(1-.8499**2)))
        self.assertEqual(self.s.stage,'failed');self.assertIsNone(self.s.candidate)

    def test_gallery_margin_is_checked_as_well_as_same_face_score(self):
        self.train();self.feed(other=.95)
        self.assertEqual(self.s.stage,'failed')

    def test_duplicate_frame_and_fast_replay_do_not_count(self):
        row,q=self.feed();self.s.offer(row,q,None)
        self.assertEqual(self.s.public()['total'],1)
        row=dict(row,fid=100,stamp=row['stamp']+100);self.s.offer(row,q,None)
        self.assertEqual(self.s.public()['total'],1)

    def test_wrong_pose_small_blurred_and_rolled_faces_do_not_count(self):
        for quality in ({'yaw':.3},{'pixels':50.},{'blur':20.},{'roll':20.}):
            self.feed(**quality)
        self.assertEqual(self.s.public()['total'],0)
        for _ in range(4):self.feed()
        for _ in range(3):self.feed(yaw=.1)
        self.assertEqual(self.s.counts['left'],0)

    def test_changed_owner_revision_and_timeout_drop_ram_candidate(self):
        for owner,revision in ((dict(OWNER,track_generation=2),0),(None,0),(OWNER,1)):
            self.s.start(OWNER,0);self.train();self.s.check(owner,revision)
            self.assertEqual(self.s.stage,'failed');self.assertIsNone(self.s.candidate)
        self.s.start(OWNER,0);self.now+=90001;self.s.check(OWNER,0)
        self.assertEqual(self.s.stage,'failed')

    def test_ready_session_expires_and_never_reuses_old_token(self):
        self.train()
        for _ in range(5):self.feed()
        token=self.s.session_id;self.now+=60001;self.s.check(OWNER,0)
        self.assertEqual(self.s.stage,'failed');self.s.start(OWNER,0)
        self.assertNotEqual(self.s.session_id,token)

    def test_landmark_pose_uses_roll_corrected_eye_axis(self):
        face=[0,0,100,100,30,30,70,30,50,50,35,75,65,75,.99]
        q=pose_quality(face,200);self.assertAlmostEqual(q['yaw'],0);self.assertAlmostEqual(q['roll'],0)
        face[8]=46;self.assertAlmostEqual(pose_quality(face,200)['yaw'],-.1)
        face[6:8]=face[4:6];self.assertIsNone(pose_quality(face,200))


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        from tests.framework import test_camera_identity as fixture
        self.fixture=fixture
        self.c=fixture.LiveIdentityTests('test_no_auto_enrollment_or_photos_written');self.c.setUp()
        self.addCleanup(self.c.doCleanups)
        self.c.service.sampling=EnrollmentSampling(.85,.1,lambda:self.c.now)
        self.c.infer()

    def start(self,replace=None):
        params={'target':self.c.state.identity_target()}
        if replace:params.update(replace_person_id=replace,db_version=self.c.store.revision)
        self.starts=getattr(self,'starts',0)+1
        ack=self.c.state.command(self.c.command('identity_sample_start',params,'start-'+str(self.starts)))
        self.assertTrue(ack['accepted'],ack)

    def feed(self,yaw=0.,vector=(1.,0.,0.,0.)):
        self.c.now+=700;fid=self.c.now;self.c.frame(fid=fid)
        extractor=self.fixture.Extractor(vector);extractor.enrollment_quality=dict(QUALITY,yaw=yaw)
        self.c.infer(extractor,fid)

    def ready(self):
        for yaw in [0.]*4+[-.1]*3+[.1]*3+[0.]*5:self.feed(yaw)
        self.assertEqual(self.c.service.sampling.stage,'ready')

    def test_command_cannot_save_until_heldout_validation_and_confirmation(self):
        self.assertFalse(self.c.state.command(self.c.enrollment(cid='early'))['accepted'])
        self.start();self.ready();self.assertEqual(self.c.store.people(),[])
        cmd=self.c.enrollment(cid='save');cmd['params']['confirmed']=False
        self.assertFalse(self.c.state.command(cmd)['accepted']);self.assertEqual(self.c.store.revision,0)
        self.assertTrue(self.c.state.command(self.c.enrollment(cid='good'))['accepted'])
        self.assertEqual(self.c.store.revision,1);self.assertEqual(self.c.service.sampling.stage,'idle')

    def test_readiness_is_revoked_on_new_face_or_database_change(self):
        self.start();self.ready();self.c.frame(tid=2,fid=90000)
        self.assertFalse(self.c.state.command(self.c.enrollment())['accepted'])
        self.assertEqual(self.c.store.people(),[])

    def test_matching_failure_writes_nothing(self):
        self.start()
        for yaw in [0.]*4+[-.1]*3+[.1]*3:self.feed(yaw)
        self.feed(vector=(0.,1.,0.,0.))
        self.assertFalse(self.c.state.command(self.c.enrollment())['accepted'])
        self.assertEqual(self.c.store.revision,0)

    def test_explicit_replacement_preserves_id_count_and_other_people(self):
        self.c.store.enroll('original','原身份',(0.,1.,0.,0.),consent=True)
        self.c.store.enroll('other','另一身份',(0.,0.,1.,0.),consent=True)
        self.feed();self.start('original');self.ready()
        command=self.c.enrollment('原身份');command['params'].update(replace_person_id='original',db_version=2)
        self.assertTrue(self.c.state.command(command)['accepted'])
        self.assertEqual(self.c.store.revision,3);self.assertEqual(len(self.c.store.people()),2)
        self.assertEqual(self.c.store.match((1,0,0,0)).identity_id,'original')
        self.assertEqual(self.c.store.match((0,0,1,0)).identity_id,'other')

    def test_cancel_and_stale_session_do_not_affect_new_sampling(self):
        self.start();sid=self.c.service.sampling.session_id
        ack=self.c.state.command(self.c.command('identity_sample_cancel',{'session_id':sid},'cancel'))
        self.assertTrue(ack['accepted']);self.assertEqual(self.c.service.sampling.stage,'idle')
        self.start();self.assertNotEqual(self.c.service.sampling.session_id,sid)
        ack=self.c.state.command(self.c.command('identity_sample_cancel',{'session_id':sid},'old-cancel'))
        self.assertFalse(ack['accepted']);self.assertEqual(self.c.service.sampling.stage,'front')


if __name__=='__main__':unittest.main()
