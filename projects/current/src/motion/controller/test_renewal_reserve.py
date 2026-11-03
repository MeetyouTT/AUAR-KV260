"""New-image renewal must precede a delayed trajectory turn, never an old image."""
import copy
import unittest
from test_recenter import Scene


class RenewalReserveTests(unittest.TestCase):
    def test_new_frame_renews_seventy_ms_lease_before_eighty_ms_control_delay(self):
        f=Scene();f.trigger();s=f.session;arms=f.device.arms
        f.device.deadline=f.now+.070
        before=len(f.device.commands);target=f.device.accepted_target_us;renewals=s.proactive_source_renewals
        packet=f.packet(.76);s.step(packet)
        self.assertGreater(len(f.device.commands),before)
        c=f.device.commands[-1]
        self.assertEqual(c['target'],target)
        self.assertEqual(c['stamp'],packet['source_mono_ms']/1000.)
        self.assertLessEqual(c['deadline'],packet['deadline_mono_ms']/1000.)
        self.assertEqual(s.proactive_source_renewals,renewals+1)
        f.now+=.080;s.tick()
        self.assertTrue(s.active);self.assertEqual(f.device.arms,arms)

    def test_status_snapshot_time_cannot_overstate_remaining_lease(self):
        f=Scene();f.trigger();s=f.session;f.device.deadline=f.now+.110
        original=f.device.status;delayed=[False]
        def status():
            rb=original()
            if not delayed[0]:delayed[0]=True;f.now+=.060
            return rb
        f.device.status=status
        before=len(f.device.commands);s.step(f.packet(.76))
        self.assertGreater(len(f.device.commands),before)
        self.assertTrue(s.active);self.assertFalse(s.fatal)
        self.assertGreater(s.fresh_image_lease_renewals,0)

    def test_duplicate_source_cannot_proactively_renew(self):
        f=Scene();f.trigger();s=f.session;f.device.deadline=f.now+.070
        # No new image: the repeated READY packet cannot invoke step renewal.
        old=copy.deepcopy(f.last);before=len(f.device.commands);count=s.proactive_source_renewals
        s.step(old)
        self.assertEqual(len(f.device.commands),before)
        self.assertEqual(s.proactive_source_renewals,count)

    def test_fresh_image_with_old_anchor_cannot_extend_anchor_deadline(self):
        f=Scene();f.trigger();s=f.session;f.device.deadline=f.now+.070
        packet=f.packet(.76);packet['face_detection_mono_ms']=round(f.now*1000)-470
        before=len(f.device.commands);s.step(packet)
        self.assertGreater(len(f.device.commands),before)
        self.assertLessEqual(f.device.commands[-1]['deadline'],packet['face_detection_mono_ms']/1000.+.5)
        f.tick(3)
        self.assertFalse(s.active);self.assertEqual(f.device.status()['flags'],0)

    def test_old_expired_hardware_permission_cannot_be_rescued_by_new_frame(self):
        f=Scene();f.trigger();f.device.deadline=f.now-.001
        before=len(f.device.commands);f.session.step(f.packet(.76))
        self.assertFalse(f.session.active)
        self.assertEqual(len(f.device.commands),before)


if __name__=='__main__':unittest.main()
