"""Optional read-only route around the existing, single-owner camera service.

Install from tools/board_camera_motion.py. No camera/identity source edit, new
camera handle, image export, DPU runner, register write, or implicit ARM.
"""
from urllib.parse import urlsplit
from common.motion_observation import MAX_AGE_MS, PATH, PROTOCOL, number


def observation(state):
    with state.lock:
        now, source, fid = state.clock(), state.processed_stamp, state.observation_fid
        value = {'protocol_version': PROTOCOL, 'source_kind': 'actual',
                 'board_boot_id': state.boot, 'service_epoch': state.epoch,
                 'camera_epoch': state.camera_epoch, 'state': 'NO_TARGET',
                 'source_frame_id': fid, 'source_mono_ms': source,
                 'deadline_mono_ms': None if source is None else source+MAX_AGE_MS,
                 'frame_width': 640, 'frame_height': 480, 'mirror_horizontal': True,
                 'target': None}
        if state.camera_error:
            value['state'] = 'CAMERA_ERROR'
        elif state.detector_error:
            value['state'] = 'DETECTOR_ERROR'
        elif state.requested_target is not None:
            value['state'] = 'TARGET_PENDING'
        elif (state.capture_stamp is None or not 0 <= now-state.capture_stamp < MAX_AGE_MS
              or source is None or not 0 <= now-source < MAX_AGE_MS):
            value['state'] = 'EXPIRED'
        elif state.observation is not None:
            selected = [t for t in state.observation['tracks']
                        if t.get('track_id') == state.selected_id and t.get('visible') is True
                        and t.get('confirmed') is True]
            if len(selected) == 1:
                t = selected[0]
                stamp = t.get('captured_at', t.get('observed_time'))
                if (t.get('frame_id') != fid or not number(stamp)
                        or abs(stamp*1000-source) > 1):
                    value['state'] = 'INCONSISTENT_SOURCE'
                else:
                    value['state'] = 'READY'
                    value['target'] = {'track_id': t['track_id'], 'track_generation': t['generation'],
                                       'box': list(t['box']), 'score': t['score']}
        return value


def install(camera_module):
    """Extend the handler factory before run(); keep every existing route intact."""
    if getattr(camera_module, '_motion_feed_installed', False):
        return
    original = camera_module.handler_for

    def handler_for(state):
        class Handler(original(state)):
            def do_GET(self):
                if urlsplit(self.path).path == PATH:
                    self.respond(200, observation(state))
                else:
                    super().do_GET()
        return Handler

    camera_module.handler_for = handler_for
    camera_module._motion_feed_installed = True
