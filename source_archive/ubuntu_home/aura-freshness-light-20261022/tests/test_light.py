import importlib.util
from pathlib import Path
import threading
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('light_metrics',ROOT/'candidate/aura/board/identity/face_freshness_metrics.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class LightTests(unittest.TestCase):
    def make(self):return module.FaceFreshnessMetrics(ttl_ms=1000)

    def publish(self,r,stamp,check,observe,count=0):
        token=r.begin(stamp);token.update(input_now_ms=check,pre_commit_check_now_ms=check,outcome_code=5)
        r.publish(token,observe,count);r.finish(token)

    def test_no_instrumentation_clock(self):
        r=self.make();self.assertIsNone(r.mark());self.publish(r,0,100,110)
        self.assertFalse(r.snapshot()['per_attempt_wall_or_thread_cpu_collected'])

    def test_gap_uses_source_stamp_not_previous_publication(self):
        r=self.make();self.publish(r,0,100,110);self.publish(r,1200,1250,1300)
        s=r.snapshot()['summaries'];self.assertEqual(s['clipped_gap_lower_bound_ms']['last_ms'],250)
        self.assertEqual(s['clipped_gap_upper_bound_ms']['last_ms'],300)

    def test_observation_expired_does_not_equal_input_gate_failure(self):
        r=self.make();self.publish(r,0,900,1100)
        c=r.snapshot()['counters'];self.assertEqual(c['post_commit_at_or_over_ttl'],1)
        self.assertEqual(c['publish_ttl_discarded'],0)

    def test_null_backward_and_boolean_clock_not_zero(self):
        for value in (None,-1,True):
            r=self.make();self.publish(r,0,100,value)
            s=r.snapshot();self.assertEqual(s['counters']['invalid_source_ages'],1)
            self.assertEqual(s['summaries']['post_commit_source_age_ms']['count'],0)
        r=self.make();self.publish(r,100,90,110)
        # The same backward source pair invalidates two distinct observations:
        # post-commit publish and the input-age summary at finish.
        self.assertEqual(r.snapshot()['counters']['invalid_source_ages'],2)

    def test_backward_source_pair_omits_gap_instead_of_fake_zero(self):
        r=self.make();self.publish(r,100,200,210);self.publish(r,90,190,200)
        s=r.snapshot();self.assertEqual(s['counters']['source_clock_pairs_rejected'],1)
        self.assertEqual(s['summaries']['clipped_gap_upper_bound_ms']['count'],0)
        self.assertIsNone(s['summaries']['clipped_gap_upper_bound_ms']['mean_ms'])

    def test_missing_input_age_is_not_reported_as_zero(self):
        r=self.make();t=r.begin(None);r.finish(t)
        s=r.snapshot();self.assertEqual(s['summaries']['input_source_age_ms']['count'],0)
        self.assertIsNone(s['summaries']['input_source_age_ms']['mean_ms'])
        self.assertEqual(s['counters']['invalid_source_ages'],1)
        self.assertNotIn('attempt_thread_cpu_ms',s['summaries'])

    def test_negative_positive_and_multiface_counts(self):
        r=self.make()
        for index,count in enumerate((0,1,2)):self.publish(r,index*100,index*100,index*100,count)
        c=r.snapshot()['counters'];self.assertEqual((c['published_negative'],c['published_positive'],c['published_multiface']),(1,2,1))

    def test_consecutive_rejections_reset_on_any_other_outcome(self):
        r=self.make()
        for code in (2,2,1,2,5):
            t=r.begin(0);t.update(input_now_ms=0,outcome_code=code);r.finish(t)
        c=r.snapshot()['counters'];self.assertEqual(c['maximum_consecutive_slot_rejections'],2)
        self.assertEqual(c['consecutive_slot_rejections'],0)

    def test_events_bounded_and_finish_idempotent(self):
        r=self.make()
        for _ in range(20):
            t=r.begin(0);t.update(input_now_ms=0,outcome_code=2);r.finish(t);r.finish(t)
        s=r.snapshot();self.assertEqual(len(s['events']),16);self.assertEqual(s['counters']['events_evicted'],4)
        self.assertEqual(s['counters']['attempts_finished'],20);self.assertEqual(s['counters']['active_attempts'],0)

    def test_snapshot_detached_and_concurrent_consistent(self):
        r=self.make();worker=threading.Thread(target=lambda:[r.offer(accepted=True,replaced=False) for _ in range(50)])
        worker.start();snapshots=[r.snapshot() for _ in range(20)];worker.join(2)
        self.assertFalse(worker.is_alive())
        for s in snapshots:self.assertEqual(s['counters']['offers'],s['counters']['offers_accepted'])
        snapshots[0]['counters']['offers']=-1;self.assertEqual(r.snapshot()['counters']['offers'],50)

    def test_close_freezes_collection(self):
        r=self.make();r.close();a=r.snapshot();r.close();r.offer(accepted=True,replaced=True)
        self.assertIsNone(r.begin(0));self.assertEqual(a,r.snapshot())

    def test_saturation_and_first_last_not_extrapolated(self):
        r=self.make();r.counters['offers']=module.LIMIT;r.offer(accepted=True,replaced=False)
        self.assertEqual(r.snapshot()['counters']['counter_saturation'],1)
        self.publish(r,0,10,20);r.close();self.assertEqual(r.snapshot()['summaries']['clipped_gap_upper_bound_ms']['count'],0)


if __name__=='__main__':unittest.main()
