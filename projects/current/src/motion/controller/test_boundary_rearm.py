import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from boundary_rearm import BoundaryRearm


class RearmTests(unittest.TestCase):
    def test_distinct_sources_and_actual_stable_time_both_required(self):
        g=BoundaryRearm()
        self.assertFalse(g.observe((1,1000),True))
        self.assertFalse(g.observe((2,1080),True))
        self.assertFalse(g.observe((3,1160),True))
        self.assertFalse(g.observe((4,1240),True))
        self.assertTrue(g.observe((5,1320),True))
    def test_duplicate_reorder_outside_or_gap_does_not_extend_stability(self):
        g=BoundaryRearm();g.observe((1,1000),True);g.observe((2,1080),True)
        self.assertFalse(g.observe((2,1080),True));self.assertEqual(g.count,2)
        self.assertFalse(g.observe((1,1060),True));self.assertEqual(g.count,2)
        self.assertFalse(g.observe((3,1160),False));self.assertEqual(g.count,0)
        self.assertFalse(g.observe((4,1240),True));self.assertEqual(g.count,1)
        self.assertFalse(g.observe((5,1510),True));self.assertEqual(g.count,1)


if __name__=='__main__':unittest.main()
