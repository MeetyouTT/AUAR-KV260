"""Run the frozen controller against a synthetic scene and software clock."""
import sys
import unittest
import test_left_episode
import test_hardware_slew
import test_rearm_stability

suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m)
    for m in (test_left_episode, test_hardware_slew, test_rearm_stability))
result=unittest.TextTestRunner(verbosity=1).run(suite)
if any(m in sys.modules for m in ('vsrv_driver','vsrv_transport','live_writer')):
    raise SystemExit('Unexpected hardware writer imported')
sys.exit(0 if result.wasSuccessful() else 1)
