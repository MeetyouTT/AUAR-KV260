import threading,unittest
from session_shutdown import shutdown_face_session


class MotorStopError(RuntimeError):pass
class ControlError(RuntimeError):pass
class SnapshotError(RuntimeError):pass


class Session:
    def __init__(self,events,*,stop_error=None,snapshot_error=None,flags=0):
        self.events=events;self.stop_error=stop_error;self.snapshot_error=snapshot_error
        self.flags=flags;self.stopped=False
    def status(self):
        self.events.append('snapshot')
        if self.snapshot_error:raise self.snapshot_error
        return dict(state='FOLLOWING')
    def close(self):
        self.events.append('stop')
        if self.stop_error:raise self.stop_error
        self.stopped=True
        return dict(state='STOPPED',readback=dict(flags=self.flags,lease_left_ms=0))


class Reader:
    def __init__(self,events,error=None):self.events=events;self.error=error
    def close(self):
        self.events.append('reader_close')
        if self.error:raise self.error


class ShutdownTests(unittest.TestCase):
    def test_motor_is_stopped_while_reader_close_is_still_blocked(self):
        events=[];entered=threading.Event();release=threading.Event();errors=[];result={}
        session=Session(events)
        class BlockingReader:
            def close(self):
                events.append('reader_close_entered');entered.set()
                if not release.wait(timeout=1):raise RuntimeError('test-release-timeout')
        def work():
            try:result['final']=shutdown_face_session(session,BlockingReader(),{})
            except BaseException as exc:errors.append(exc)
        worker=threading.Thread(target=work,daemon=True);worker.start()
        try:
            self.assertTrue(entered.wait(timeout=.5))
            self.assertTrue(worker.is_alive())
            self.assertTrue(session.stopped)
            self.assertEqual(events,['snapshot','stop','reader_close_entered'])
        finally:release.set();worker.join(timeout=1)
        self.assertFalse(worker.is_alive());self.assertEqual(errors,[])
        self.assertEqual(result['final']['readback']['flags'],0)
    def test_reader_error_after_verified_stop_is_recorded(self):
        events=[];report={};session=Session(events)
        final=shutdown_face_session(session,Reader(events,RuntimeError('reader-close-failed')),report)
        self.assertTrue(session.stopped);self.assertEqual(events,['snapshot','stop','reader_close'])
        self.assertEqual(final['readback']['flags'],0)
        self.assertEqual(report['reader_close_error'],'RuntimeError: reader-close-failed')
    def test_original_control_error_is_not_masked_by_reader_error(self):
        events=[];report={};session=Session(events)
        original=ControlError('control-failed')
        try:
            try:raise original
            finally:shutdown_face_session(session,Reader(events,RuntimeError('reader-failed')),report)
        except ControlError as received:self.assertIs(received,original)
        else:self.fail('Original control exception disappeared')
        self.assertTrue(session.stopped);self.assertIn('reader_close_error',report)
    def test_stop_failure_is_not_masked_by_reader_error(self):
        events=[];report={};original=MotorStopError('stop-failed')
        with self.assertRaises(MotorStopError) as received:
            shutdown_face_session(Session(events,stop_error=original),Reader(events,RuntimeError('reader-failed')),report)
        self.assertIs(received.exception,original);self.assertEqual(events,['snapshot','stop','reader_close'])
        self.assertIn('reader_close_error',report)
    def test_snapshot_failure_still_attempts_and_verifies_stop(self):
        events=[];report={};session=Session(events,snapshot_error=SnapshotError('snapshot-failed'))
        with self.assertRaises(SnapshotError):shutdown_face_session(session,Reader(events),report)
        self.assertTrue(session.stopped);self.assertEqual(events,['snapshot','stop','reader_close'])
        self.assertEqual(report['result']['readback']['flags'],0)
    def test_unconfirmed_stop_is_rejected_before_reader_cleanup(self):
        events=[];report={}
        with self.assertRaisesRegex(RuntimeError,'STOP was not confirmed'):
            shutdown_face_session(Session(events,flags=15),Reader(events,RuntimeError('reader-failed')),report)
        self.assertEqual(events,['snapshot','stop','reader_close'])
    def test_stop_failure_keeps_original_control_error_as_context(self):
        events=[];report={};primary=ControlError('primary');stop=MotorStopError('stop')
        try:
            try:raise primary
            finally:shutdown_face_session(Session(events,stop_error=stop),Reader(events,RuntimeError('reader')),report)
        except MotorStopError as received:
            self.assertIs(received,stop);self.assertIs(received.__context__,primary)
        else:self.fail('Stop failure disappeared')
    def test_primary_control_error_beats_failed_optional_snapshot(self):
        events=[];report={};primary=ControlError('primary');session=Session(events,snapshot_error=SnapshotError('snapshot'))
        try:
            try:raise primary
            finally:shutdown_face_session(session,Reader(events,RuntimeError('reader')),report)
        except ControlError as received:self.assertIs(received,primary)
        else:self.fail('Primary control exception disappeared')
        self.assertTrue(session.stopped);self.assertIn('pre_stop_snapshot_error',report)


if __name__=='__main__':unittest.main()
