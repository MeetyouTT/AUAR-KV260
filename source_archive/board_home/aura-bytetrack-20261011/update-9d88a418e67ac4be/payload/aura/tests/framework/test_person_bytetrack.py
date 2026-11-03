"""Real NumPy ByteTrack association, source-time lifetimes and target ownership."""
import itertools
import math
import unittest

from common.contracts import Detection
try:
    import numpy as np
except ImportError:
    np = None


@unittest.skipIf(np is None, 'NumPy is required for the actual tracking tests')
class PersonByteTrackTests(unittest.TestCase):
    def tracker(self):
        from board.vision.person_bytetrack import PersonByteTracks
        return PersonByteTracks('camera', {'track_threshold':.5,'new_track_threshold':.6,
            'match_threshold':.8,'nominal_hz':10,'lost_ms':500,'confirm_observations':2}, verify=False)

    def person(self, x=10., score=.8):
        return Detection((x,20.,100.,200.),score)

    def test_high_then_low_score_rescues_existing_track_only(self):
        t=self.tracker()
        first=t.update([self.person()],1,1.,640,480)['tracks'][0]
        second=t.update([self.person(12.,.2)],2,1.1,640,480)['tracks'][0]
        self.assertEqual(first['track_id'],second['track_id'])
        self.assertTrue(second['confirmed'])
        self.assertAlmostEqual(second['score'],.2)
        empty=self.tracker().update([self.person(score=.2)],1,1.,640,480)
        self.assertEqual(empty['tracks'],[])

    def test_threshold_boundary_is_not_dropped(self):
        t=self.tracker()
        t.update([self.person()],1,1.,640,480)
        value=t.update([self.person(score=.5)],2,1.1,640,480)
        self.assertEqual(len(value['tracks']),1)

    def test_geometry_is_actual_measurement_not_kalman_prediction(self):
        t=self.tracker()
        t.update([self.person()],1,1.,640,480)
        value=t.update([self.person(25.)],2,1.2,640,480)['tracks'][0]
        self.assertEqual(value['box'],[25.,20.,100.,200.])
        self.assertEqual(value['frame_id'],2)
        self.assertEqual(value['captured_at'],1.2)
        self.assertAlmostEqual(value['velocity'][0],75.)
        self.assertAlmostEqual(t.tracker.kalman_filter._motion_mat[0,4],2.)

    def test_empty_frame_clears_target_and_never_publishes_prediction(self):
        t=self.tracker()
        t.update([self.person()],1,1.,640,480)
        observed=t.update([self.person()],2,1.1,640,480)
        tid=observed['tracks'][0]['track_id'];t.target_id=tid
        missing=t.update([],3,1.2,640,480)
        self.assertEqual(missing['tracks'],[])
        self.assertIsNone(missing['target_id'])
        new=t.update([self.person()],4,1.3,640,480)['tracks'][0]
        self.assertEqual(new['track_id'],tid)
        self.assertEqual(new['generation'],2)
        self.assertFalse(new['confirmed'])
        again=t.update([self.person()],5,1.4,640,480)
        self.assertTrue(again['tracks'][0]['confirmed'])
        self.assertIsNone(again['target_id'])

    def test_long_source_gap_expires_before_association(self):
        t=self.tracker()
        first=t.update([self.person()],1,1.,640,480)['tracks'][0]['track_id']
        t.update([self.person()],2,1.1,640,480)
        t.update([self.person()],3,1.7,640,480)
        final=t.update([self.person()],4,1.8,640,480)
        ids={v['track_id'] for v in final['tracks']}
        self.assertTrue(ids)
        self.assertNotIn(first,ids)
        self.assertNotIn(first,t.history)

    def test_two_people_require_explicit_selection_and_stay_one_to_one(self):
        t=self.tracker()
        a=t.update([self.person(),self.person(300.)],1,1.,640,480)
        b=t.update([self.person(302.),self.person(12.)],2,1.1,640,480)
        self.assertEqual(len({r['track_id'] for r in b['tracks']}),2)
        self.assertIsNone(b['target_id'])
        tid=min(b['tracks'],key=lambda r:r['box'][0])['track_id']
        t.target_id=tid
        c=t.update([self.person(304.),self.person(14.)],3,1.2,640,480)
        self.assertEqual(c['target_id'],tid)
        self.assertLess(t.tracks[tid]['box'][0],100.)
        self.assertEqual({r['track_id'] for r in a['tracks']},{r['track_id'] for r in c['tracks']})

    def test_replayed_source_is_rejected(self):
        t=self.tracker();t.update([],1,1.,640,480)
        for fid,stamp in [(1,1.1),(2,1.),(2,float('nan'))]:
            with self.assertRaises(ValueError):t.update([],fid,stamp,640,480)

    def test_retained_state_is_bounded_after_many_people_exit(self):
        t=self.tracker()
        for fid in range(1,601):
            t.update([self.person()] if fid%3==1 else [],fid,1.+fid*.1,640,480)
        self.assertLessEqual(len(t.history),6)
        self.assertLessEqual(len(t.tracker.removed_stracks),128)

    def test_assignment_matches_independent_exhaustive_optional_optimum(self):
        from board.vision.bytetrack.matching import linear_assignment
        rng=np.random.RandomState(19)
        for m,n in [(1,3),(3,1),(3,3),(4,3)]:
            for _ in range(12):
                costs=rng.uniform(0.,1.,(m,n));thresh=.8
                pairs,ua,ub=linear_assignment(costs,thresh)
                actual=sum(costs[i,j] for i,j in pairs)+thresh/2.*(len(ua)+len(ub))
                best=math.inf
                for size in range(min(m,n)+1):
                    for rows in itertools.combinations(range(m),size):
                        for cols in itertools.permutations(range(n),size):
                            if all(costs[i,j]<=thresh for i,j in zip(rows,cols)):
                                candidate=sum(costs[i,j] for i,j in zip(rows,cols))+thresh/2.*(m+n-2*size)
                                best=min(best,candidate)
                self.assertAlmostEqual(actual,best)

    def test_global_assignment_avoids_greedy_trap_and_respects_gate(self):
        from board.vision.bytetrack.matching import linear_assignment
        pairs,ua,ub=linear_assignment(np.array([[.1,.2],[.11,.9]]),.8)
        self.assertEqual(set(map(tuple,pairs)),{(0,1),(1,0)})
        self.assertEqual((ua,ub),((),()))
        pairs,ua,ub=linear_assignment(np.array([[.9]]),.8)
        self.assertEqual(pairs.shape,(0,2))
        self.assertEqual((ua,ub),((0,),(0,)))

    def test_independent_trackers_do_not_share_prediction_delta(self):
        a,b=self.tracker(),self.tracker()
        a.update([self.person()],1,1.,640,480);b.update([self.person()],1,1.,640,480)
        a.update([self.person()],2,1.2,640,480);b.update([self.person()],2,1.05,640,480)
        self.assertAlmostEqual(a.tracker.kalman_filter.dt,2.)
        self.assertAlmostEqual(b.tracker.kalman_filter.dt,.5)


if __name__=='__main__':unittest.main()
