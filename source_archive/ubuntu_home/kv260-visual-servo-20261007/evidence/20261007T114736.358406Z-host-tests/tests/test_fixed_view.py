"""Stationary-camera behaviour with fictitious TEST_DOUBLE calibration."""
from dataclasses import replace
import unittest
from test_control import Registers, reference, frame
from vsrv_driver import VSRVDriver
from face_servo_control import FaceServoController
from physical_motion_service import PhysicalMotionService
from fixed_view_mapping import FixedViewMapping, REFERENCE_X_PX


def mapping(polarity=1):
    return FixedViewMapping('boot','setup','cam',1460,polarity,160,1460-20*polarity,
                            480,1460+20*polarity,'FICTITIOUS_TEST_ANCHORS',True)


class FixedCameraTests(unittest.TestCase):
    def setup_control(self,polarity=1):
        regs=Registers();driver=VSRVDriver(regs,123,'boot',lambda:regs.time)
        driver.confirm_and_arm(reference(camera_moves_with_axis=False,polarity=polarity),11,22,authorized=True)
        control=FaceServoController(driver,'cam',fixed_view_mapping=mapping(polarity))
        return regs,driver,control

    def observe(self,regs,control,fid,center):
        source=1.+fid*.1;regs.time=source+.05
        return control.observe(frame(fid,source,center),640,480,regs.time,'boot')

    def test_missing_mapping_cannot_enable_independent_camera_control(self):
        regs=Registers();driver=VSRVDriver(regs,123,'boot',lambda:regs.time)
        driver.confirm_and_arm(reference(camera_moves_with_axis=False),11,22,authorized=True)
        with self.assertRaises(ValueError):FaceServoController(driver,'cam')
        with self.assertRaises(ValueError):PhysicalMotionService(driver,'cam')
        self.assertFalse(driver.status()['active'])

    def test_mapping_requires_measured_anchors_and_matching_context(self):
        for change in ({'confirmed':False},{'evidence':''},{'left_x_px':320},
                       {'right_x_px':640},{'left_us':1461},{'polarity':0},{'right_us':1700}):
            with self.subTest(change=change),self.assertRaises(ValueError):replace(mapping(),**change)
        ref=reference(camera_moves_with_axis=False)
        for change in ({'boot_id':'new'},{'setup_id':'new'},{'camera_epoch':'new'},
                       {'reference_us':1461}):
            self.assertFalse(replace(mapping(),**change).matches(ref,'cam'))

    def test_same_person_at_right_stops_at_mapped_target_without_drift(self):
        regs,driver,control=self.setup_control()
        for fid in range(1,31):
            before=control.accepted_us;result=self.observe(regs,control,fid,480)
            self.assertLessEqual(abs(control.accepted_us-before),4)
            if fid>1:self.assertEqual(result['outcome'],'ACCEPTED')
            if fid>=7:self.assertEqual(control.accepted_us,1480)
        self.assertEqual(control.mode,'FIXED_VIEW_POSITION')
        self.assertEqual(driver.accepted_target_us,1480)
        self.assertLess(control.accepted_us,control.high)

    def test_blue_line_commands_reference_not_arbitrary_middle_pulse(self):
        regs,driver,control=self.setup_control()
        self.assertEqual(control.reference_x_px,REFERENCE_X_PX)
        for fid in range(1,8):self.observe(regs,control,fid,REFERENCE_X_PX)
        self.assertEqual(control.accepted_us,1460)
        self.assertEqual(driver.accepted_target_us,1460)

    def test_returning_to_blue_line_returns_to_reference_with_slew(self):
        regs,driver,control=self.setup_control()
        for fid in range(1,12):self.observe(regs,control,fid,480)
        self.assertEqual(control.accepted_us,1480)
        for fid in range(12,31):
            previous=control.accepted_us;self.observe(regs,control,fid,REFERENCE_X_PX)
            self.assertLessEqual(abs(control.accepted_us-previous),4)
        self.assertEqual(control.accepted_us,1460)

    def test_left_and_reversed_polarity_use_calibrated_direction(self):
        for polarity,center,pulse in ((1,160,1440),(-1,480,1440)):
            regs,driver,control=self.setup_control(polarity)
            for fid in range(1,15):self.observe(regs,control,fid,center)
            self.assertEqual(control.accepted_us,pulse)

    def test_rejection_does_not_advance_position_mapping_slew(self):
        regs,driver,control=self.setup_control();self.observe(regs,control,1,480)
        regs.reject=True;result=self.observe(regs,control,2,480)
        self.assertEqual(result['outcome'],'REJECTED');self.assertEqual(control.accepted_us,1460)
        self.assertEqual(control.requested_continuous,1460)
        regs.reject=False;self.observe(regs,control,3,480)
        self.assertEqual(control.accepted_us,1464)

    def test_context_change_stops_and_does_not_reuse_calibration(self):
        regs,driver,control=self.setup_control();self.observe(regs,control,1,480)
        self.observe(regs,control,2,480)
        snapshot=frame(3,1.3);snapshot['epoch']='new'
        regs.time=1.35;result=control.observe(snapshot,640,480,regs.time,'boot')
        self.assertEqual(result['reason'],'CAMERA_CONTEXT_CHANGED');self.assertFalse(driver.status()['active'])

    def test_fixed_mapping_cannot_be_applied_to_axis_mounted_camera(self):
        regs=Registers();driver=VSRVDriver(regs,123,'boot',lambda:regs.time)
        driver.confirm_and_arm(reference(),11,22,authorized=True)
        with self.assertRaises(ValueError):FaceServoController(driver,'cam',fixed_view_mapping=mapping())


if __name__=='__main__':unittest.main()
