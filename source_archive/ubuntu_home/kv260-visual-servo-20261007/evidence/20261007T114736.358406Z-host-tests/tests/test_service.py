"""Real tracker records -> injected physical protocol double; no actuation."""
import unittest
from test_control import Registers, reference
from vision_core import FaceTracks
from physical_motion_service import PhysicalMotionService
from vsrv_driver import VSRVDriver, COMMIT


class InferenceBridgeTests(unittest.TestCase):
    def setup_service(self):
        regs = Registers()
        driver = VSRVDriver(regs,123,'boot',lambda:regs.time)
        driver.confirm_and_arm(reference(),11,22,authorized=True)
        return regs, driver, PhysicalMotionService(driver,'cam'), FaceTracks('cam')

    def observe(self, regs, service, tracker, fid, source, faces=True):
        # This is exactly the snapshot contract used by the inference callback.
        snapshot = tracker.update([[440,100,80,80]+[0]*10+[.95]] if faces else [], fid, source,640,480)
        regs.time = source+.05
        return service.observe(snapshot,640,480,regs.time,'boot')

    def start(self, regs, service, tracker):
        for fid in range(1,7):
            state = self.observe(regs,service,tracker,fid,1.+.1*fid)
        return state

    def test_pipeline_has_one_target_one_ack_and_no_assumed_angle(self):
        regs,driver,service,tracker = self.setup_service()
        for fid in range(1,6):
            state=self.observe(regs,service,tracker,fid,1.+.1*fid)
            self.assertFalse(state['motion_command_emitted'])
        state=self.observe(regs,service,tracker,6,1.6)
        self.assertEqual(state['scope'],'PHYSICAL_VSRV_BENCH')
        self.assertEqual(state['controller_accepted_seq'],1)
        self.assertEqual(state['control']['source_frame_id'],6)
        self.assertEqual(state['physical_submit_attempts'],1)
        self.assertEqual(state['relative_pulse_us'],2)
        self.assertFalse(state['mechanical_angle_measured'])

    def test_polling_and_display_never_renew_source_lease(self):
        regs,driver,service,tracker=self.setup_service();self.start(regs,service,tracker)
        deadline=regs.deadline;writes=len(regs.writes)
        for delta in (.01,.02,.04):
            regs.time=1.65+delta;state=service.poll(regs.time);service.status()
        self.assertEqual(regs.deadline,deadline);self.assertEqual(len(regs.writes),writes)
        regs.time=deadline+.01;state=service.poll(regs.time)
        self.assertEqual(state['state'],'DISARMED')
        self.assertFalse(state['actuation_authorized']);self.assertFalse(state['readback']['active'])

    def test_loss_stops_and_regained_face_cannot_resume(self):
        regs,driver,service,tracker=self.setup_service();self.start(regs,service,tracker)
        state=self.observe(regs,service,tracker,7,1.7,False)
        self.assertEqual(state['reason'],'TARGET_LOST')
        count=sum(value==COMMIT and offset==0x24 for offset,value in regs.writes)
        for fid in range(8,15):self.observe(regs,service,tracker,fid,1.+fid*.1)
        self.assertEqual(service.status()['state'],'DISARMED')
        self.assertEqual(sum(value==COMMIT and offset==0x24 for offset,value in regs.writes),count)

    def test_unarmed_service_is_rejected(self):
        regs,driver,service,tracker=self.setup_service();driver.stop()
        with self.assertRaises(ValueError):PhysicalMotionService(driver,'cam')


if __name__=='__main__':unittest.main()
