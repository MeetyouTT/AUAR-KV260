"""Real board camera command contract with synthetic embeddings; no user DB."""
import copy
import unittest
import sys
from board.identity.voice_enrollment import VoiceEnrollment
from tests.framework import test_camera_identity as camera_fixture

class VoiceEnrollmentBoardTests(unittest.TestCase):
    def setUp(self):
        self.camera=camera_fixture.LiveIdentityTests('test_unknown_enroll_known_then_delete_and_unknown')
        self.camera.setUp();self.addCleanup(self.camera.doCleanups)
        self.camera.infer()
        self.flow=VoiceEnrollment('boot',self.camera.state.snapshot,self.camera.state.command,
            now_ms=lambda:self.camera.now)
        self.start=self.camera.state.snapshot()
    def test_three_spoken_turns_commit_real_sqlite_transaction_once(self):
        self.assertEqual(self.flow.handle('帮我登记身份',self.start)['code'],'ask_name')
        self.assertEqual(self.flow.handle('我叫小林',self.start)['code'],'confirm_name')
        self.assertEqual(self.camera.store.people(),[])
        self.assertEqual(self.flow.handle('确认登记',self.start)['code'],'registered')
        self.assertEqual([p['display_name'] for p in self.camera.store.people()],['小林'])
        self.assertEqual(self.camera.store.revision,1)
        self.assertIsNone(self.flow.handle('确认登记',self.start))
    def test_changed_target_between_recording_and_asr_never_commits(self):
        self.flow.handle('帮我登记身份',self.start);self.flow.handle('我叫小林',self.start)
        self.camera.frame(tid=2,fid=2);self.camera.infer(fid=2)
        self.assertEqual(self.flow.handle('确认登记',self.start)['code'],'changed')
        self.assertEqual(self.camera.store.people(),[])
    def test_cancellation_and_bad_face_do_not_persist_name(self):
        self.flow.handle('帮我登记身份',self.start);self.flow.handle('我叫小林',self.start)
        self.assertEqual(self.flow.handle('取消登记',self.start)['code'],'cancelled')
        self.assertEqual(self.camera.store.people(),[])
        self.flow.handle('帮我登记身份',self.start);self.flow.handle('我叫小林',self.start)
        self.camera.service.result=None
        self.assertEqual(self.flow.handle('确认登记',self.start)['code'],'face_unavailable')
        self.assertEqual(self.camera.store.people(),[])

class RuntimeImportTests(unittest.TestCase):
    def test_archival_asset_loader_cannot_redirect_runtime_imports(self):
        from tools.board_avatar_gtk import create_runtime_core
        before=list(sys.path)
        def factory(kind):
            self.assertEqual(kind,'reuse');sys.path.insert(0,'/unrelated-old-runtime');return 'core'
        self.assertEqual(create_runtime_core(factory),'core')
        self.assertEqual(sys.path,before)
    def test_failed_asset_loader_also_restores_import_path(self):
        from tools.board_avatar_gtk import create_runtime_core
        before=list(sys.path)
        def factory(kind):sys.path.insert(0,'/unrelated-old-runtime');raise ValueError('fixture')
        with self.assertRaises(ValueError):create_runtime_core(factory)
        self.assertEqual(sys.path,before)
