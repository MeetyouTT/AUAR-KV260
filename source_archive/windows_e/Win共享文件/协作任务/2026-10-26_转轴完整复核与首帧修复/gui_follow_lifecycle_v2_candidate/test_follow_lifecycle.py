"""Behavioral owner/reaping checks; no GTK, camera, MMIO, model or board."""
import importlib.util,json,signal,subprocess,sys,threading,types,unittest
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


cleanup=load('candidate_follow_cleanup',HERE/'follow_process_cleanup.py')
tools=types.ModuleType('tools');tools.__path__=[]
pan=types.ModuleType('tools.pan_controls');pan.stage_type=lambda base,factory:base
with patch.dict(sys.modules,{'tools':tools,'tools.pan_controls':pan,
                            'tools.follow_process_cleanup':cleanup}):
    controls=load('candidate_face_pan_controls',HERE/'face_pan_controls.py')


class Output:
    def exists(self):return True
    def read_text(self):
        return json.dumps(dict(status='CONTINUOUS_FACE_ZONE_STOPPED',
            result=dict(reason='OPERATOR_STOP',commands_accepted=1,stopped=dict(flags=0))))


class Manual:
    def __init__(self,events,sign):
        self.events=events;self.sign=sign;self.closed=False;self.stops=0
    def close(self):self.closed=True;self.events.append('manual-close')
    def read(self):return dict(state='CLOSED' if self.closed else 'READY',left_sign=self.sign,
                              readback=dict(flags=0,lease_left_ms=0))
    def reverse(self):self.sign=-self.sign;self.events.append('manual-sign-restored')
    def stop(self):self.stops+=1;return dict(ok=True)


class Child:
    pid=31415
    def __init__(self,*,communicate_error=None,term_works=True,kill_works=True,wait_results=None):
        self.alive=True;self.returncode=None;self.communicate_error=communicate_error
        self.term_works=term_works;self.kill_works=kill_works;self.signals=[];self.kills=0
        self.wait_results=list(wait_results or []);self.wait_timeouts=[];self.entered=threading.Event()
    def communicate(self,timeout):
        self.entered.set()
        if self.communicate_error:raise self.communicate_error
        self.alive=False;self.returncode=0;return '',''
    def poll(self):return None if self.alive else self.returncode
    def send_signal(self,value):
        self.signals.append(value)
        if not self.term_works:raise OSError('sigterm-failed')
        self.alive=False;self.returncode=-value
    def kill(self):
        self.kills+=1
        if not self.kill_works:raise OSError('kill-failed')
        self.alive=False;self.returncode=-signal.SIGKILL
    def wait(self,timeout):
        self.wait_timeouts.append(timeout)
        if self.wait_results:
            result=self.wait_results.pop(0)
            if isinstance(result,BaseException):raise result
            if type(result) is int:self.alive=False;self.returncode=result
            return result
        if self.alive:raise subprocess.TimeoutExpired('fake-child',timeout)
        return self.returncode


class Harness:
    def __init__(self,child,*,fail_reopen=False):
        self.child=child;self.events=[];self.manuals=[];self.launched=False;self.fail_reopen=fail_reopen
        self.factory_calls=0
        def factory():
            self.factory_calls+=1
            if self.launched:
                if self.child.poll() is None:raise AssertionError('Attempted second motor owner')
                self.events.append('old-follow-exit-confirmed')
                if self.fail_reopen:raise RuntimeError('manual-reopen-failed')
            m=Manual(self.events,-1 if not self.manuals else 1);self.manuals.append(m)
            self.events.append('manual-created');return m
        self.face=controls.FacePanProcess({'left_button_pulse_sign':-1},manual_factory=factory)
        self.face.arguments=lambda:(['never-a-motor-process'],Output())
    def popen(self,*args,**kwargs):
        if not self.manuals[0].closed:raise AssertionError('Manual owner not released before follow')
        self.launched=True;self.events.append('follow-launched');return self.child
    def run(self):
        self.face.running=True
        with patch.object(controls.subprocess,'Popen',side_effect=self.popen):self.face.work()
    def join(self):
        if self.face.thread:self.face.thread.join(timeout=1)
        if self.face.thread and self.face.thread.is_alive():raise AssertionError('Test cleanup thread did not finish')


class FailingThread:
    def __init__(self,*args,**kwargs):pass
    def start(self):raise RuntimeError('thread-start-failed')
    def is_alive(self):return False
    def join(self,timeout):raise AssertionError('Cannot join a thread which never started')


class LifecycleTests(unittest.TestCase):
    def test_normal_exit_reopens_manual_only_after_exit_and_keeps_configured_sign(self):
        child=Child();h=Harness(child);h.run()
        self.assertEqual(h.events,['manual-created','manual-close','follow-launched',
            'old-follow-exit-confirmed','manual-created','manual-sign-restored'])
        self.assertEqual(h.face.manual.sign,-1);self.assertFalse(h.face.running)
        self.assertIsNone(h.face.child);self.assertEqual(child.signals,[])
        self.assertTrue(h.face.result['process_cleanup']['exit_confirmed'])
    def test_communicate_oserror_terminates_and_reaps_live_child_before_reopen(self):
        child=Child(communicate_error=OSError('broken-communicate'));h=Harness(child);h.run()
        self.assertFalse(child.alive);self.assertIn(signal.SIGTERM,child.signals)
        self.assertEqual(child.wait_timeouts,[2.]);self.assertEqual(h.factory_calls,2)
        self.assertIsNone(h.face.child);self.assertFalse(h.face.running)
        self.assertIn('broken-communicate',h.face.result['reason'])
    def test_communicate_unexpected_error_uses_same_cleanup_path(self):
        child=Child(communicate_error=ValueError('bad-pipe-decode'));h=Harness(child);h.run()
        self.assertFalse(child.alive);self.assertIsNone(h.face.child)
        self.assertIn('bad-pipe-decode',h.face.result['reason'])
    def test_wait_timeout_escalates_to_kill_and_wait(self):
        child=Child(communicate_error=OSError('pipe'),term_works=False);h=Harness(child);h.run()
        self.assertEqual(child.kills,1);self.assertEqual(child.wait_timeouts,[2.,2.])
        self.assertFalse(child.alive);self.assertIsNone(h.face.child)
        self.assertTrue(h.face.result['process_cleanup']['kill_requested'])
    def test_wait_oserror_escalates_and_preserves_primary_error(self):
        child=Child(communicate_error=OSError('primary-pipe'),wait_results=[OSError('wait-failed')])
        h=Harness(child);h.run()
        self.assertEqual(child.kills,1);self.assertIsNone(h.face.child)
        self.assertIn('primary-pipe',h.face.result['reason'])
        self.assertIn('wait-failed',' '.join(h.face.result['process_cleanup']['errors']))
    def test_unconfirmed_termination_keeps_handle_stop_controls_and_single_owner(self):
        child=Child(communicate_error=OSError('primary-pipe'),term_works=False,kill_works=False)
        h=Harness(child);h.run()
        self.assertTrue(child.alive);self.assertIs(h.face.child,child)
        self.assertTrue(h.face.running);self.assertTrue(h.face.cleanup_pending)
        self.assertEqual(h.factory_calls,1);self.assertFalse(h.face.cleanup_running)
        state=h.face.read();self.assertTrue(state['automatic_following'])
        self.assertIn('停止尚未确认',state['message'])
        with self.assertRaises(ValueError):h.face.start()
        with self.assertRaises(ValueError):h.face.jog('left')
        self.assertIn('primary-pipe',h.face.result['reason'])
    def test_stop_retries_unconfirmed_child_and_restores_manual_after_confirmed_exit(self):
        child=Child(communicate_error=OSError('pipe'),term_works=False,kill_works=False)
        h=Harness(child);h.run();child.term_works=True
        h.face.stop();h.join()
        self.assertFalse(child.alive);self.assertIsNone(h.face.child)
        self.assertFalse(h.face.running);self.assertEqual(h.factory_calls,2)
        self.assertEqual(h.face.manual.sign,-1)
    def test_close_retries_but_never_creates_a_manual_owner_after_closing(self):
        child=Child(communicate_error=OSError('pipe'),term_works=False,kill_works=False)
        h=Harness(child);h.run();child.term_works=True;h.face.close()
        self.assertFalse(child.alive);self.assertIsNone(h.face.child)
        self.assertFalse(h.face.running);self.assertEqual(h.factory_calls,1)
    def test_failed_close_still_retains_child_and_can_be_retried(self):
        child=Child(communicate_error=OSError('pipe'),term_works=False,kill_works=False)
        h=Harness(child);h.run();h.face.close()
        self.assertIs(h.face.child,child);self.assertTrue(h.face.running)
        self.assertEqual(h.factory_calls,1)
        child.term_works=True;h.face.close()
        self.assertIsNone(h.face.child);self.assertFalse(h.face.running)
        self.assertEqual(h.factory_calls,1)
    def test_cleanup_helper_failure_keeps_primary_error_and_live_owner(self):
        child=Child(communicate_error=OSError('primary-pipe'));h=Harness(child)
        with patch.object(controls,'terminate_follow_child',side_effect=RuntimeError('cleanup-helper-failed')):h.run()
        self.assertIs(h.face.child,child);self.assertTrue(h.face.running)
        self.assertEqual(h.factory_calls,1);self.assertIn('primary-pipe',h.face.result['reason'])
        self.assertIn('cleanup-helper-failed',' '.join(h.face.result['process_cleanup']['errors']))
        h.face.stop();h.join();self.assertIsNone(h.face.child)
    def test_manual_reopen_failure_does_not_replace_original_communicate_error(self):
        child=Child(communicate_error=OSError('primary-pipe'));h=Harness(child,fail_reopen=True);h.run()
        self.assertIn('primary-pipe',h.face.result['reason'])
        self.assertIn('manual-reopen-failed',h.face.result['manual_reopen_error'])
        self.assertIsNone(h.face.child);self.assertFalse(h.face.running)
    def test_cancel_before_launch_restores_manual_without_creating_follow_child(self):
        child=Child();h=Harness(child)
        # There is no launched child; allow the second manual factory here.
        h.face.cancelled.set();h.face.running=True
        with patch.object(controls.subprocess,'Popen',side_effect=AssertionError('Cancelled follow launched')):
            h.face.work()
        self.assertFalse(h.launched);self.assertFalse(h.face.running);self.assertEqual(h.factory_calls,2)
    def test_user_stop_reaps_active_worker_and_reopens_one_manual_owner(self):
        class WaitingChild(Child):
            def communicate(self,timeout):
                self.entered.set()
                if self.alive:
                    threading.Event().wait(timeout=.005)
                    raise subprocess.TimeoutExpired('waiting-child',timeout)
                return '',''
        child=WaitingChild();h=Harness(child)
        with patch.object(controls.subprocess,'Popen',side_effect=h.popen):
            h.face.start();self.assertTrue(child.entered.wait(timeout=.5));h.face.stop();h.join()
        self.assertFalse(child.alive);self.assertIsNone(h.face.child)
        self.assertFalse(h.face.running);self.assertEqual(h.factory_calls,2)
        self.assertEqual(h.face.manual.sign,-1)
    def test_initial_thread_start_failure_leaves_existing_manual_owner_ready(self):
        h=Harness(Child())
        with patch.object(controls.threading,'Thread',FailingThread):
            with self.assertRaisesRegex(RuntimeError,'thread-start-failed'):h.face.start()
        self.assertFalse(h.face.running);self.assertIsNone(h.face.child)
        self.assertFalse(h.manuals[0].closed);self.assertEqual(h.factory_calls,1)
    def test_live_status_refresh_cannot_overwrite_original_error_during_cleanup(self):
        entered=threading.Event();release=threading.Event()
        class WaitingCleanupChild(Child):
            def send_signal(self,value):self.signals.append(value)
            def wait(self,timeout):
                entered.set()
                if not release.wait(timeout=1):raise RuntimeError('test-release-timeout')
                self.alive=False;self.returncode=-signal.SIGTERM;return self.returncode
        child=WaitingCleanupChild(communicate_error=OSError('primary-pipe'));h=Harness(child)
        with patch.object(controls.subprocess,'Popen',side_effect=h.popen):
            h.face.start()
            try:
                self.assertTrue(entered.wait(timeout=.5));state=h.face.read()
                self.assertIn('primary-pipe',state['face_follow']['reason'])
                self.assertTrue(state['automatic_following']);self.assertEqual(h.factory_calls,1)
            finally:release.set();h.join()
        self.assertIn('primary-pipe',h.face.result['reason']);self.assertEqual(h.factory_calls,2)
    def test_stop_between_exception_and_cleanup_does_not_start_second_reaper(self):
        entered=threading.Event();release=threading.Event();entries=[];entry_threads=[]
        child=Child(communicate_error=OSError('primary-pipe'));h=Harness(child)
        finish=h.face.finish_owner
        def paused_before_cleanup(released):
            entries.append(1);entry_threads.append(threading.current_thread());entered.set()
            if not release.wait(timeout=1):raise RuntimeError('test-release-timeout')
            return finish(released)
        h.face.finish_owner=paused_before_cleanup
        with patch.object(controls.subprocess,'Popen',side_effect=h.popen):
            h.face.start();original_worker=h.face.thread
            try:
                self.assertTrue(entered.wait(timeout=.5))
                self.assertTrue(h.face.cleanup_pending);self.assertFalse(h.face.cleanup_running)
                self.assertTrue(original_worker.is_alive())
                for _ in range(3):h.face.stop()
                self.assertIs(h.face.thread,original_worker)
                self.assertEqual(len(entries),1);self.assertEqual(h.factory_calls,1)
            finally:
                release.set();original_worker.join(timeout=1)
                for worker in entry_threads:
                    if worker is not original_worker:worker.join(timeout=1)
        self.assertFalse(h.face.running);self.assertIsNone(h.face.child)
        self.assertEqual(h.factory_calls,2);self.assertEqual(len(h.manuals),2)
    def test_retry_thread_start_failure_keeps_handle_and_allows_later_retry(self):
        child=Child(communicate_error=OSError('pipe'),term_works=False,kill_works=False)
        h=Harness(child);h.run()
        with patch.object(controls.threading,'Thread',FailingThread):h.face.stop()
        self.assertIs(h.face.child,child);self.assertTrue(h.face.running)
        self.assertFalse(h.face.cleanup_running);self.assertIn('stop_retry_error',h.face.result)
        child.term_works=True;h.face.stop();h.join()
        self.assertIsNone(h.face.child);self.assertFalse(h.face.running)
    def test_real_unrelated_sleep_process_is_reaped_after_pipe_error(self):
        real_popen=subprocess.Popen
        child=real_popen([sys.executable,'-c','import time; time.sleep(20)'],
                         stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        class BrokenPipeChild:
            def __getattr__(self,name):return getattr(child,name)
            def communicate(self,timeout):raise OSError('real-child-pipe-error')
        h=Harness(BrokenPipeChild())
        try:
            h.run();self.assertIsNotNone(child.poll());self.assertIsNone(h.face.child)
            self.assertFalse(h.face.running);self.assertEqual(h.factory_calls,2)
        finally:
            if child.poll() is None:child.kill();child.wait(timeout=2)


class CleanupTests(unittest.TestCase):
    def test_already_exited_child_needs_no_signals(self):
        c=Child();c.alive=False;c.returncode=0;r=cleanup.terminate_follow_child(c)
        self.assertTrue(r['exit_confirmed']);self.assertEqual(c.signals,[]);self.assertEqual(c.wait_timeouts,[])
    def test_poll_failure_still_terminates_and_waits(self):
        c=Child();c.poll=lambda:(_ for _ in ()).throw(OSError('poll-failed'))
        r=cleanup.terminate_follow_child(c)
        self.assertTrue(r['exit_confirmed']);self.assertEqual(c.wait_timeouts,[2.])
        self.assertIn('poll-failed',' '.join(r['errors']))
    def test_non_integer_wait_results_never_confirm_exit(self):
        c=Child(wait_results=[None,None]);r=cleanup.terminate_follow_child(c)
        self.assertFalse(r['exit_confirmed']);self.assertEqual(c.wait_timeouts,[2.,2.])
    def test_both_wait_failures_keep_exit_unconfirmed(self):
        c=Child(wait_results=[OSError('first-wait'),OSError('second-wait')])
        r=cleanup.terminate_follow_child(c)
        self.assertFalse(r['exit_confirmed']);self.assertEqual(c.wait_timeouts,[2.,2.])
        self.assertIn('first-wait',' '.join(r['errors']));self.assertIn('second-wait',' '.join(r['errors']))


if __name__=='__main__':unittest.main()
