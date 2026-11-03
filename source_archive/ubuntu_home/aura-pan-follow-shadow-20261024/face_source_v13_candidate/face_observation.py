"""Publish current pixels with original anchor and explicit v13 method metadata."""
from common.motion_observation import MAX_AGE_MS, PROTOCOL
from face_flow import ANCHOR_MAX_AGE_MS


def observation(state):
    with state.lock:
        face = getattr(state.identity, 'face_targets', None)
        camera_error,capture_stamp=state.camera_error,state.capture_stamp
        result = dict(protocol_version=PROTOCOL, source_kind='actual', target_kind='face',
                      board_boot_id=state.boot, service_epoch=state.epoch,
                      camera_epoch=state.camera_epoch, state='NO_TARGET', source_frame_id=None,
                      source_mono_ms=None, deadline_mono_ms=None, frame_width=640,
                      frame_height=480, mirror_horizontal=True, target=None)
    if face is None:
        result['state'] = 'FACE_UNAVAILABLE'
        return result
    flow = getattr(face, '_edge_flow', None)
    if flow is None:
        result['state'] = 'FACE_UNAVAILABLE'
        return result
    value, error = flow.snapshot()
    result['face_tracking'] = flow.diagnostics()
    with face.lock:
        now=state.clock()
        timing=getattr(face,'_edge_latest_detector_timing',None)
        if timing is not None:
            result['detector_timing']=dict(timing)
        if (camera_error or error or face.error or face.closed
                or face.fault_latched or not face.ready):
            result['state'] = 'FACE_ERROR'
        elif face.count > 1:
            result['state'] = 'MULTIPLE_FACES'
        elif value is None:
            result['state'] = 'UNCONFIRMED'
        elif (not 0 <= now-value['stamp'] < MAX_AGE_MS
              or not 0 <= now-value['anchor_stamp'] < min(face.ttl, ANCHOR_MAX_AGE_MS)
              or face.stamp is None or not 0 <= now-face.stamp < min(face.ttl, ANCHOR_MAX_AGE_MS)
              or capture_stamp is None or not 0 <= now-capture_stamp < MAX_AGE_MS):
            result['state'] = 'EXPIRED'
        elif (face.count == 1 and (face.key is None or value['detector_key'] != face.key)):
            result['state'] = 'UNCONFIRMED'
        elif face.count == 0 and (value['frame_id'] < face.tracker.last_frame
                                 or value['stamp'] < face.stamp):
            # Detection can publish a miss AFTER Flow has already matched
            # the same/newer actual image. Require pixels at least as new
            # as that miss, not that the worker saw its publication first.
            result['state'] = 'UNCONFIRMED'
        elif face.count == 0 and face.continuity_key != value['detector_key']:
            result['state'] = 'UNCONFIRMED'
        else:
            result.update(state='READY', source_frame_id=value['frame_id'],
                          source_mono_ms=value['stamp'], deadline_mono_ms=value['stamp']+MAX_AGE_MS,
                          measurement_method='current_face_fixed_anchor_v13',
                          measurement_details=dict(method=value.get('measurement_method'),
                              match_score=value.get('match_score'),lk_inliers=value.get('lk_inliers'),
                              lk_scale=value.get('lk_scale'),lk_rotation_degrees=value.get('lk_rotation_degrees')),
                          face_detection_mono_ms=value['anchor_stamp'],
                          evaluated_mono_ms=now, face_detection_age_ms=now-value['anchor_stamp'],
                          detection_miss=face.count == 0,
                          detector_snapshot_frame_id=value['detector_frame_id'],
                          latest_detection_frame_id=face.tracker.last_frame,
                          target=dict(track_id=value['key']['track_id'],
                                      track_generation=value['key']['track_generation'],
                                      box=value['box'], score=value['score']))
    return result
