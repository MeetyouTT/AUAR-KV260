"""Stop and verify the motor before any potentially blocking reader cleanup."""
import sys


def _describe(error):
    try:return type(error).__name__+': '+str(error)[:250]
    except BaseException:return type(error).__name__


def shutdown_face_session(session,stream,report):
    pending_error=sys.exc_info()[1]
    snapshot_error=stop_error=None
    final=None
    try:
        try:report['pre_stop_result']=session.status()
        except BaseException as exc:snapshot_error=exc
        try:
            final=session.close()
            report['result']=final
            readback=final.get('readback') or {}
            if readback.get('flags')!=0 or readback.get('lease_left_ms')!=0:
                raise RuntimeError('Motor STOP was not confirmed before reader cleanup')
        except BaseException as exc:stop_error=exc
    finally:
        # HTTPResponse.close may wait for another thread's buffered read lock.
        # It must never stand between the controller and its explicit STOP.
        try:stream.close()
        except BaseException as exc:report['reader_close_error']=_describe(exc)
    if snapshot_error is not None:report['pre_stop_snapshot_error']=_describe(snapshot_error)
    if stop_error is not None:raise stop_error
    if snapshot_error is not None and pending_error is None:raise snapshot_error
    return final
