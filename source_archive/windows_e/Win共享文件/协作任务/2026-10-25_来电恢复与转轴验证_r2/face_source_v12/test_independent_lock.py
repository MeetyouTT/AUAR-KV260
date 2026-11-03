import threading,unittest
import test_face_source_v11 as source_tests
from face_observation import observation
from face_lock import install


class LockTests(unittest.TestCase):
    def setUp(self):
        self.fx=source_tests.SourceTests();self.fx.setUp()
    def test_flow_snapshot_does_not_hold_the_camera_lock(self):
        self.fx.frame(1,1000)
        original=self.fx.flow.snapshot
        def snapshot():
            self.assertFalse(self.fx.state.lock._is_owned())
            return original()
        self.fx.flow.snapshot=snapshot
        self.assertEqual(observation(self.fx.state)['state'],'READY')

    def test_time_is_checked_after_acquiring_the_face_lock(self):
        self.fx.frame(1,1000);test=self.fx
        class Delayed:
            def __enter__(self):test.now=1501
            def __exit__(self,*args):pass
        self.fx.face.lock=Delayed()
        self.assertEqual(observation(self.fx.state)['state'],'EXPIRED')

    def test_isolated_service_lock_preserves_the_clock_and_callback(self):
        class Service:
            def __init__(self,factory,callback,epoch,**kwargs):
                self.lock=kwargs['lock'];self.options=kwargs;self.callback=callback
        install(Service);shared=threading.RLock();callback=lambda:None;clock=lambda:10
        s=Service(None,callback,'camera',lock=shared,clock=clock,slot_retry=True)
        self.assertIsNot(s.lock,shared);self.assertIs(s.callback,callback)
        self.assertIs(s.options['clock'],clock);self.assertTrue(s.options['slot_retry'])
    def test_real_capture_offer_does_not_wait_for_the_camera_lock(self):
        from board.identity.face_targets import FaceTargetService
        original=FaceTargetService.__init__;shared=threading.RLock()
        prior=getattr(FaceTargetService,'_edge_independent_face_lock',None)
        done=threading.Event();worker=None
        try:
            install(FaceTargetService)
            service=FaceTargetService(lambda:None,lambda *a:None,'camera',lock=shared)
            self.assertIsNot(service.lock,shared)
            with shared:
                worker=threading.Thread(target=lambda:(service.offer('image',1,1000),done.set()))
                worker.start();self.assertTrue(done.wait(.5))
            self.assertEqual(service.pending,('image',1,1000))
        finally:
            FaceTargetService.__init__=original
            if prior is None:del FaceTargetService._edge_independent_face_lock
            else:FaceTargetService._edge_independent_face_lock=prior
            if worker is not None:worker.join(timeout=1)
