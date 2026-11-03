"""Opt-in Linux ARM capture-consumer priority; no device work on construction.

Only _read_pcm's existing consumer TID is changed. arecord is already owned
and launched at its caller's original nice before this method. The bounded PCM
pump is created inside this method and inherits this consumer's Linux nice.
All original endpoint/queue/PCM/ACK/clock and Mcp01Capture cleanup stay intact.
"""
import os
import platform
import sys
import threading

from board.runtime.audio.board_capture import BoardAutomaticCapture,BoardBargeCapture


class CapturePriorityRejected(RuntimeError):pass


class CaptureThreadPriority:
    def __init__(self, publish):
        self.publish=publish
        self.tid=self.original=None
        self.report=dict(requested_nice=-10,original_nice=None,effective_nice=None,
                         restored_nice=None,restoration_confirmed=False,status='not_started',
                         scope='capture_consumer_tid_and_inherited_pcm_pump_only')

    def _publish(self):
        codes=dict(unsupported_platform='capture_thread_priority_unsupported',
            permission_denied='capture_thread_priority_permission_denied',apply_failed='capture_thread_priority_apply_failed',
            not_applied='capture_thread_priority_not_applied',restore_wrong_thread='capture_thread_priority_restore_wrong_thread',
            restore_failed='capture_thread_priority_restore_failed')
        self.publish(dict(self.report,native_tid=self.tid,applied=self.report['effective_nice']==-10,
            restored=self.report['restoration_confirmed'],error_code=codes.get(self.report['status'],'')))

    def acquire(self):
        if (sys.platform!='linux' or platform.machine().lower() not in ('aarch64','arm64') or
                not all(hasattr(os,n) for n in ('PRIO_PROCESS','getpriority','setpriority')) or
                not callable(getattr(threading,'get_native_id',None))):
            self.report['status']='unsupported_platform';self._publish()
            raise CapturePriorityRejected('capture_thread_priority_unsupported')
        self.tid=threading.get_native_id()
        try:
            self.original=os.getpriority(os.PRIO_PROCESS,self.tid)
            self.report['original_nice']=self.original
            os.setpriority(os.PRIO_PROCESS,self.tid,-10)
            effective=os.getpriority(os.PRIO_PROCESS,self.tid)
            self.report.update(effective_nice=effective,status='active')
            self._publish()
            if effective!=-10:
                self.report['status']='not_applied';self._publish()
                raise CapturePriorityRejected('capture_thread_priority_not_applied')
        except PermissionError:
            self.report['status']='permission_denied';self._publish()
            raise CapturePriorityRejected('capture_thread_priority_permission_denied') from None
        except OSError:
            self.report['status']='apply_failed';self._publish()
            raise CapturePriorityRejected('capture_thread_priority_apply_failed') from None

    def restore(self):
        if self.original is None:return
        if threading.get_native_id()!=self.tid:
            self.report['status']='restore_wrong_thread';self._publish()
            raise CapturePriorityRejected('capture_thread_priority_restore_wrong_thread')
        try:
            os.setpriority(os.PRIO_PROCESS,self.tid,self.original)
            restored=os.getpriority(os.PRIO_PROCESS,self.tid)
            self.report.update(restored_nice=restored,restoration_confirmed=restored==self.original)
            if restored!=self.original:raise OSError('restore_mismatch')
            if self.report['status']=='active':self.report['status']='restored'
            self._publish()
        except OSError:
            self.report['status']='restore_failed';self._publish()
            raise CapturePriorityRejected('capture_thread_priority_restore_failed') from None


class _ConsumerPriority:
    def _read_pcm(self,process):
        def publish(report):self._capture_priority_report=report
        lease=CaptureThreadPriority(publish)
        entered=False
        try:
            lease.acquire()
            entered=True
            return super()._read_pcm(process)
        finally:
            try:
                # The endpoint/pool lease was prepared before Mcp01Capture
                # started this consumer. Failed priority admission must retire
                # it even though the original read loop was never entered.
                if not entered:self._priority_setup_cleanup()
            finally:
                lease.restore()

    def snapshot(self):
        value=super().snapshot()
        value['capture_priority']=dict(getattr(self,'_capture_priority_report',
            dict(requested_nice=-10,status='not_started',restoration_confirmed=False,
                 original_nice=None,effective_nice=None,restored_nice=None,
                 applied=False,restored=False,error_code='',native_tid=None,
                 scope='capture_consumer_tid_and_inherited_pcm_pump_only')))
        pump=getattr(self,'_board_pcm_input',None)
        value['capture_priority']['pump_native_tid']=getattr(getattr(pump,'thread',None),'native_id',None)
        return value


class PriorityBoardAutomaticCapture(_ConsumerPriority,BoardAutomaticCapture):
    def _priority_setup_cleanup(self):self._close_endpoint()


class PriorityBoardBargeCapture(_ConsumerPriority,BoardBargeCapture):
    def _priority_setup_cleanup(self):self._release_echo()
