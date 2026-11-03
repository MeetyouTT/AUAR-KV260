"""Numeric, bounded per-source detector timing; no model/scheduler changes."""
import time


def install(service_type=None):
    if service_type is None:
        from board.identity.face_targets import FaceTargetService
        service_type=FaceTargetService
    if getattr(service_type,'_edge_detector_timing_v13',False):return
    original=service_type.process

    def process(self,packet,detector,*args,**kwargs):
        fid,stamp=packet[1:];began=time.monotonic_ns()
        runner=getattr(detector,'runner',None)
        before=getattr(runner,'last_report',None)
        try:
            return original(self,packet,detector,*args,**kwargs)
        finally:
            # Diagnostic failure must neither hide nor manufacture a result.
            try:
                finished=time.monotonic_ns()
                record=dict(frame_id=fid,source_mono_ms=stamp,
                    process_begin_mono_ns=began,process_return_mono_ns=finished,
                    input_source_age_ms=round(began/1e6-stamp,3),
                    process_wall_ms=round((finished-began)/1e6,3),
                    process_return_source_age_ms=round(finished/1e6-stamp,3))
                report=getattr(runner,'last_report',None)
                if isinstance(report,dict) and report is not before:
                    fields=('task','submitted','completed','outcome','business_ready','result_fresh',
                            'start_ns','native_return_ns','release_decision_ns','after_unlock_ns')
                    native={k:report[k] for k in fields if type(report.get(k)) is int}
                    record['native']=native
                    start=native.get('start_ns');release=native.get('release_decision_ns')
                    if start and release and began<=start<=release<=finished:
                        record.update(before_native_start_ms=round((start-began)/1e6,3),
                            native_lease_ms=round((release-start)/1e6,3),
                            after_native_release_ms=round((finished-release)/1e6,3))
                with self.lock:
                    record.update(published_frame_id=self.tracker.last_frame,
                                  detector_count=self.count,published_source_mono_ms=self.stamp)
                    self._edge_latest_detector_timing=record
                    self._edge_detector_timed_rounds=getattr(self,'_edge_detector_timed_rounds',0)+1
            except Exception:
                # Timing is best effort, never a new business recovery path.
                pass

    service_type.process=process
    service_type._edge_detector_timing_v13=True
