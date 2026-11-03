import unittest
from policy import choose_boot,readiness

class Policy(unittest.TestCase):
    def test_current_and_later_boots_have_no_delay(self):
        self.assertEqual(choose_boot('a','a',None),'UNCHANGED_SOURCE_BOOT')
        self.assertEqual(choose_boot('a','c','b'),'UNCHANGED_LATER_BOOT')
    def test_only_one_new_boot_is_selected(self):
        self.assertEqual(choose_boot('a','b',None),'CLAIM_NEW_BOOT')
        self.assertEqual(choose_boot('a','b','b'),'TRIAL_BOOT')
    def test_delay_requires_actual_readiness_and_minimum_uptime(self):
        self.assertEqual(readiness(uptime=20,elapsed=10,scanout_active=False,camera_ready=True),'WAIT')
        self.assertEqual(readiness(uptime=80,elapsed=10,scanout_active=False,camera_ready=False),'WAIT')
        self.assertEqual(readiness(uptime=80,elapsed=60,scanout_active=False,camera_ready=True),'READY_FOR_FIRST_XSERVER_OUTPUT')
    def test_already_active_is_not_labeled_first_scanout(self):
        self.assertEqual(readiness(uptime=80,elapsed=10,scanout_active=True,camera_ready=True),'INVALID_SCANOUT_ALREADY_ACTIVE')
    def test_wait_is_bounded_even_when_camera_unavailable(self):
        self.assertEqual(readiness(uptime=91,elapsed=90,scanout_active=False,camera_ready=False),'FALLBACK_WAIT_LIMIT')

if __name__=='__main__':unittest.main()
