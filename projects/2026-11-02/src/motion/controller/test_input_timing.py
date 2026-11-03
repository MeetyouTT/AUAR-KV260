import queue,threading,unittest
from unittest.mock import patch
from face_stream import FaceStream
from input_timing import InputTiming


class InputTimingTests(unittest.TestCase):
    def test_duplicate_packets_never_count_as_independent_sources(self):
        t=InputTiming();p=dict(state='READY',source_frame_id=1,source_mono_ms=1000,face_detection_mono_ms=950,
            evaluated_mono_ms=1010,service_epoch='s',camera_epoch='c',face_tracking={'reason':'FACE_TEMPLATE_VISIBLE_CLIP'})
        for _ in range(30):t.observe(p,{'reason':'EDGE_FOLLOW','control':{'new_source':True}},1020)
        v=t.snapshot();self.assertEqual(v['counts']['distinct_ready_sources'],1)
        self.assertEqual(v['counts']['duplicate_ready_packets'],29)
        self.assertEqual(v['counts']['admitted_distinct_sources'],1)
    def test_stale_anchor_and_transport_age_are_counted_separately(self):
        t=InputTiming();p=dict(state='READY',source_frame_id=1,source_mono_ms=1000,
            face_detection_mono_ms=700,evaluated_mono_ms=1100)
        t.observe(p,{'reason':'SOURCE_EXPIRED'},1250);v=t.snapshot()
        self.assertEqual(v['counts']['image_expired_on_receipt'],1)
        self.assertEqual(v['counts']['anchor_expired_on_receipt'],1)
        self.assertEqual(v['distributions']['publish_to_consume_ms']['p95'],150)
        self.assertNotIn('admitted_distinct_sources',v['counts'])
    def test_timing_buffers_are_bounded(self):
        t=InputTiming()
        for i in range(1000):t.observe(dict(state='READY',source_frame_id=i,source_mono_ms=i*80),{},i*80+20)
        self.assertEqual(len(t.recent),32)
        self.assertTrue(all(len(v)<=256 for v in t.windows.values()))
    def test_queue_diagnostics_never_drop_loss_or_fault_before_new_face(self):
        s=FaceStream.__new__(FaceStream);s.queue=queue.Queue(256);s.closed=threading.Event()
        s.maximum_queue_depth=0;s.maximum_queue_wait_ms=s.last_queue_wait_ms=0.
        original=dict(state='READY',source_mono_ms=1)
        with patch('face_stream.time.monotonic',return_value=10.):
            s.send('packet',{'state':'NO_TARGET'});s.send('fault','malformed');s.send('packet',original)
        with patch('face_stream.time.monotonic',return_value=10.05):values=s.drain()
        self.assertEqual([x[0] for x in values],['packet','fault','packet'])
        self.assertEqual(values[0][1]['state'],'NO_TARGET');self.assertIs(values[-1][1],original)
        self.assertEqual(original['source_mono_ms'],1)
        self.assertEqual(s.diagnostics()['maximum_queue_depth'],3)
        self.assertAlmostEqual(s.maximum_queue_wait_ms,50.)
