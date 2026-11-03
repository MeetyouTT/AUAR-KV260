"""Publish only a fresh v9 current-image face measurement."""
from common.motion_observation import MAX_AGE_MS, PROTOCOL
from face_flow import ANCHOR_MAX_AGE_MS


def observation(state):
    with state.lock:
        face = getattr(state.identity, 'face_targets', None)
        now = state.clock()
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
            if (state.camera_error or error or face.error or face.closed
                    or face.fault_latched or not face.ready):
                result['state'] = 'FACE_ERROR'
            elif face.count > 1:
                result['state'] = 'MULTIPLE_FACES'
            elif value is None:
                result['state'] = 'UNCONFIRMED'
            elif (not 0 <= now-value['stamp'] < MAX_AGE_MS
                  or not 0 <= now-value['anchor_stamp'] < min(face.ttl, ANCHOR_MAX_AGE_MS)
                  or face.stamp is None or not 0 <= now-face.stamp < min(face.ttl, ANCHOR_MAX_AGE_MS)
                  or state.capture_stamp is None or not 0 <= now-state.capture_stamp < MAX_AGE_MS):
                result['state'] = 'EXPIRED'
            elif (face.count == 1 and (face.key is None or value['detector_key'] != face.key)):
                result['state'] = 'UNCONFIRMED'
            elif face.count == 0 and face.tracker.last_frame != value['detector_frame_id']:
                # Wait for a pixel measurement after each newly reported miss.
                result['state'] = 'UNCONFIRMED'
            elif face.count == 0 and face.continuity_key != value['detector_key']:
                result['state'] = 'UNCONFIRMED'
            else:
                result.update(state='READY', source_frame_id=value['frame_id'],
                              source_mono_ms=value['stamp'], deadline_mono_ms=value['stamp']+MAX_AGE_MS,
                              measurement_method='current_face_template_visible_clip_v9',
                              face_detection_mono_ms=value['anchor_stamp'],
                              evaluated_mono_ms=now, face_detection_age_ms=now-value['anchor_stamp'],
                              detection_miss=value['detection_miss'],
                              target=dict(track_id=value['key']['track_id'],
                                          track_generation=value['key']['track_generation'],
                                          box=value['box'], score=value['score']))
        return result
