"""Boundary tests; synthetic identities and no hardware/model access."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'aura'))
from board.identity.live import IdentityService
from board.identity.store import IdentityStore
from common.speaker_attribution import SpeakerContext,evaluate
from tools.check_motion_readiness import assess


class FaceDiagnostics(unittest.TestCase):
    def setUp(self):
        self.now=1000
        self.key={'camera_epoch':'test','track_id':1,'track_generation':1}
        self.store=IdentityStore(':memory:','synthetic',2,.5,.1)
        self.service=IdentityService(self.store,None,lambda:self.key,clock=lambda:self.now)
        self.service.ready=True
        self.addCleanup(self.service.close)

    def result(self,vector=(1.,0.)):
        self.service.result={'target':copy.deepcopy(self.key),'fid':42,'stamp':self.now,
            'revision':self.store.revision,'match':self.store.match(vector)}

    def test_empty_gallery_is_not_low_similarity(self):
        self.result()
        self.assertEqual(self.service.recognition_diagnostics()['reason_code'],'EMPTY_GALLERY')

    def test_low_similarity_and_matched(self):
        self.store.enroll('opaque','fixture',(1.,0.),consent=True,expected_revision=0,max_people=32)
        self.result((0.,1.))
        self.assertEqual(self.service.recognition_diagnostics()['reason_code'],'LOW_SIMILARITY')
        self.result()
        d=self.service.recognition_diagnostics()
        self.assertEqual(d['reason_code'],'MATCHED');self.assertEqual(d['source_frame_id'],42)
        self.assertFalse({'person_id','display_name','embedding'}&d.keys())

    def test_expired_result_does_not_export_score(self):
        self.result();self.now+=1500
        d=self.service.recognition_diagnostics()
        self.assertEqual(d['reason_code'],'STALE_OR_FOREIGN_RESULT');self.assertNotIn('score',d)

    def test_changed_target_does_not_export_score(self):
        self.result();self.key['track_generation']=2
        self.assertEqual(self.service.recognition_diagnostics()['reason_code'],'STALE_OR_FOREIGN_RESULT')

    def test_not_ready_and_missing_target(self):
        self.service.ready=False
        self.assertEqual(self.service.recognition_diagnostics()['reason_code'],'MODEL_LOADING')
        self.service.ready=True;self.key=None
        self.assertEqual(self.service.recognition_diagnostics()['reason_code'],'NO_FACE_OR_TARGET')


class SpeakerBoundaries(unittest.TestCase):
    def setUp(self):
        self.context=SpeakerContext('capture',4,'model',3)
        self.result=dict(capture_id='capture',turn_generation=4,model_id='model',gallery_revision=3,
             started_ms=0,ended_ms=3500,deadline_ms=4500,voiced_ms=3100,
             single_speaker_verified=True,face_identity_conflict=False,scores={'opaque-a':.85,'opaque-b':.5})

    def check(self,**kwargs):
        args=dict(threshold=.8,margin=.1,minimum_voiced_ms=3000,field_calibrated=True)
        args.update(kwargs)
        return evaluate(self.result,self.context,4000,**args)

    def test_valid_candidate_never_unlocks_personal_memory(self):
        r=self.check();self.assertTrue(r['accepted']);self.assertFalse(r['personal_memory_allowed'])

    def test_not_calibrated_and_cancelled(self):
        self.assertEqual(self.check(field_calibrated=False)['reason'],'NOT_FIELD_CALIBRATED')
        self.assertEqual(self.check(cancelled=True)['reason'],'CANCELLED')

    def test_context_changes(self):
        for key,value in [('capture_id','old'),('turn_generation',3),('gallery_revision',2),('model_id','old'),('turn_generation',True)]:
            with self.subTest(key=key,value=value):
                before=copy.deepcopy(self.result);self.result[key]=value
                self.assertEqual(self.check()['reason'],'CONTEXT_MISMATCH');self.result=before

    def test_window_and_short_speech(self):
        self.result['deadline_ms']=4000
        self.assertEqual(self.check()['reason'],'EXPIRED_OR_INVALID_WINDOW')
        self.result['deadline_ms']=4500;self.result['voiced_ms']=250
        self.assertEqual(self.check()['reason'],'INSUFFICIENT_OR_INVALID_SPEECH')

    def test_ambiguity_invalid_and_overlap(self):
        for score,reason in [(.79,'LOW_SIMILARITY'),(float('nan'),'INVALID_SCORES')]:
            self.result['scores']['opaque-a']=score
            self.assertEqual(self.check()['reason'],reason)
        self.result['scores']={'opaque-a':.85,'opaque-b':.84}
        self.assertEqual(self.check()['reason'],'AMBIGUOUS')
        self.result['single_speaker_verified']=False
        self.assertEqual(self.check()['reason'],'SPEAKER_OVERLAP_UNVERIFIED')

    def test_face_conflict_and_missing_verification(self):
        for value in (True,None):
            self.result['face_identity_conflict']=value
            self.assertEqual(self.check()['reason'],'FACE_CONFLICT_OR_UNVERIFIED')


class MotionPreflight(unittest.TestCase):
    def test_actual_unverified_configuration_is_blocked(self):
        import tools.check_motion_readiness as readiness
        root=Path(readiness.__file__).resolve().parents[1]
        import json
        calibration=json.loads((root/'config/servo_calibration.json').read_text())
        d=assess({'boot_id':'old','fdt_sha256':'fdt'},calibration,boot_id='current',
                 fdt_sha256='fdt',manual_state={'state':'FAULT'})
        self.assertIn('BOOT_MISMATCH',d['blockers']);self.assertIn('MECHANICS_NOT_VERIFIED',d['blockers'])
        self.assertFalse(d['physical_actuation_performed'])

    def test_valid_metadata_never_authorizes_motion(self):
        calibration=dict(verified=True,boot_id='boot',setup_id='setup',evidence='fixture',
                         reference_us=1500,polarity=1,camera_moves_with_axis=True)
        d=assess(dict(boot_id='boot',fdt_sha256='hash'),calibration,boot_id='boot',
                 fdt_sha256='hash',manual_state={'state':'READY'},firmware='aura-visual-servo-b4096-v1.bit.bin')
        self.assertEqual(d['state'],'PREFLIGHT_ONLY');self.assertFalse(d['automatic_following_authorized'])
        self.assertIn('JOINT_FIRMWARE_REQUIRED',assess({},calibration,boot_id='boot',
            fdt_sha256='hash',manual_state={},firmware='kv260-benchmark-b4096.bit.bin')['blockers'])
        calibration['reference_us']=True
        self.assertIn('REFERENCE_NOT_MEASURED',assess({},calibration,boot_id='boot',fdt_sha256='hash',manual_state={})['blockers'])

if __name__=='__main__':unittest.main(verbosity=2)
