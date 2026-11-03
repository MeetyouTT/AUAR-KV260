import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from live_writer import LatestReportWriter,close_after_stop


class LiveWriterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'report.json'

    def test_blocked_disk_never_blocks_later_control_submissions_and_queue_is_latest_only(self):
        entered=threading.Event();release=threading.Event();values=[]
        def disk(raw,cancel):
            entered.set();release.wait(1)
            if not cancel.is_set():values.append(raw)
        writer=LatestReportWriter(self.path,write=disk)
        try:
            writer.submit('0');self.assertTrue(entered.wait(.5))
            started=time.monotonic()
            for index in range(100):writer.submit(str(index))
            self.assertLess(time.monotonic()-started,.1)
            self.assertEqual(writer.diagnostics()['pending'],1)
            self.assertEqual(writer.diagnostics()['coalesced'],99)
            release.set()
            deadline=time.monotonic()+.5
            while writer.diagnostics()['written']<2 and time.monotonic()<deadline:time.sleep(.001)
            self.assertEqual(values,['0','99'])
        finally:release.set();writer.close()

    def test_normal_atomic_report_is_valid_and_last_live_cannot_overwrite_final_after_exit(self):
        writer=LatestReportWriter(self.path)
        writer.submit(json.dumps({'state':'RUNNING'}))
        deadline=time.monotonic()+.5
        while writer.diagnostics()['written']<1 and time.monotonic()<deadline:time.sleep(.001)
        self.assertEqual(json.loads(self.path.read_text())['state'],'RUNNING')
        writer.close();self.path.write_text('{"state":"STOPPED"}')
        time.sleep(.01)
        self.assertEqual(json.loads(self.path.read_text())['state'],'STOPPED')
        self.assertFalse(list(self.path.parent.glob('*.live-*')))

    def test_immutable_snapshot_is_not_changed_by_later_control_updates(self):
        entered=threading.Event();release=threading.Event();values=[]
        def disk(raw,cancel):entered.set();release.wait(1);values.append(json.loads(raw))
        writer=LatestReportWriter(self.path,write=disk)
        try:
            snapshot={'control':{'pulse':1420}}
            writer.submit(json.dumps(snapshot));self.assertTrue(entered.wait(.5))
            snapshot['control']['pulse']=1450;release.set()
            deadline=time.monotonic()+.5
            while not values and time.monotonic()<deadline:time.sleep(.001)
            self.assertEqual(values,[{'control':{'pulse':1420}}])
        finally:release.set();writer.close()

    def test_close_cancels_pending_and_waits_before_final_proof(self):
        entered=threading.Event();release=threading.Event();writes=[]
        def disk(raw,cancel):
            entered.set();release.wait(1)
            if not cancel.is_set():writes.append(raw)
        writer=LatestReportWriter(self.path,write=disk,join_timeout_s=.01)
        writer.submit('old');self.assertTrue(entered.wait(.5));writer.submit('pending')
        try:
            with self.assertRaisesRegex(RuntimeError,'did not exit'):writer.close()
            self.assertEqual(writer.diagnostics()['pending'],0)
            release.set();writer.thread.join(.5);writer.close()
            self.assertEqual(writes,[])
            with self.assertRaises(RuntimeError):writer.submit('cannot-restart')
        finally:release.set();writer.thread.join(.5)

    def test_write_failure_is_reported_and_does_not_spin_retry(self):
        calls=[]
        def disk(raw,cancel):calls.append(raw);raise OSError('injected disk failure')
        writer=LatestReportWriter(self.path,write=disk);writer.submit('x');writer.thread.join(.5)
        with self.assertRaisesRegex(RuntimeError,'writer failed'):writer.check()
        with self.assertRaises(RuntimeError):writer.close()
        with self.assertRaises(RuntimeError):writer.submit('y')
        self.assertEqual(calls,['x'])

    def test_control_or_stop_error_wins_over_writer_cleanup_error(self):
        original=ValueError('control or STOP failed')
        def disk(raw,cancel):raise OSError('disk failed')
        with self.assertRaises(ValueError) as caught:
            with LatestReportWriter(self.path,write=disk) as writer:
                writer.submit('x');writer.thread.join(.5);raise original
        self.assertIs(caught.exception,original)

    def test_payload_is_bounded_before_writing(self):
        with LatestReportWriter(self.path) as writer:
            for raw in ({'mutable':True},'x'*65537,'中'*22000):
                with self.assertRaises(ValueError):writer.submit(raw)
            self.assertEqual(writer.diagnostics()['submitted'],0)

    def test_explicit_finally_close_preserves_control_error_and_never_reaches_proof(self):
        import sys
        report={};proof=[];original=ValueError('primary control failure')
        class Writer:
            def close(self):raise OSError('writer close failed')
        with self.assertRaises(ValueError) as caught:
            try:raise original
            finally:
                pending=sys.exc_info()[1]
                close_after_stop(Writer(),report,pending)
                proof.append('must not write final proof')
        self.assertIs(caught.exception,original)
        self.assertEqual(proof,[])
        self.assertIn('writer close failed',report['live_writer_close_error'])
        self.assertIsInstance(original.__cause__,OSError)

    def test_explicit_finally_writer_error_without_control_error_is_fatal(self):
        report={}
        class Writer:
            def close(self):raise OSError('only writer failed')
        with self.assertRaisesRegex(OSError,'only writer failed'):
            close_after_stop(Writer(),report)
        self.assertIn('only writer failed',report['live_writer_close_error'])


if __name__=='__main__':unittest.main()
