"""Anonymous, source-bound YuNet face observations and a finite push stream."""
import json
import threading
import time
from urllib.parse import parse_qs, urlsplit
from common.motion_observation import MAX_AGE_MS, PROTOCOL

GET_PATH = '/v1/motion/face/observation'
STREAM_PATH = '/v1/motion/face-stream'


def observation(state):
    with state.lock:
        face = getattr(state.identity, 'face_targets', None)
        now = state.clock()
        result = {'protocol_version': PROTOCOL, 'source_kind': 'actual', 'target_kind': 'face',
                  'board_boot_id': state.boot, 'service_epoch': state.epoch,
                  'camera_epoch': state.camera_epoch, 'state': 'NO_TARGET',
                  'source_frame_id': None, 'source_mono_ms': None, 'deadline_mono_ms': None,
                  'frame_width': 640, 'frame_height': 480, 'mirror_horizontal': True, 'target': None}
        if face is None:
            result['state'] = 'FACE_UNAVAILABLE'
            return result
        with face.lock:
            stamp = face.stamp
            fid = face.tracker.last_frame
            result.update(source_frame_id=fid, source_mono_ms=stamp,
                          deadline_mono_ms=stamp+MAX_AGE_MS if stamp is not None else None)
            if state.camera_error or face.error or face.closed or face.fault_latched or not face.ready:
                result['state'] = 'FACE_ERROR'
            elif (stamp is None or not 0 <= now-stamp < MAX_AGE_MS or state.capture_stamp is None
                  or not 0 <= now-state.capture_stamp < MAX_AGE_MS):
                result['state'] = 'EXPIRED'
            elif face.count > 1:
                result['state'] = 'MULTIPLE_FACES'
            elif face.key is not None and face.count == 1:
                key = face.key
                track = face.tracker.tracks.get(key['track_id'])
                if (track is None or not track['visible'] or not track['confirmed']
                        or track['frame_id'] != fid or abs(track['observed_time']*1000-stamp) > 1):
                    result['state'] = 'INCONSISTENT_FACE_SOURCE'
                else:
                    result.update(state='READY', target={'track_id': key['track_id'],
                        'track_generation': key['track_generation'], 'box': list(track['box']), 'score': track['score']})
        return result


def install(camera, *, interval_ms=100):
    if getattr(camera, '_edge_face_source_installed', False):
        return
    if type(interval_ms) is not int or not 50 <= interval_ms <= 200:
        raise ValueError('Bounded face refresh interval required')
    from board.identity.face_targets import FaceTargetService
    initialize = FaceTargetService.__init__
    base_handler = camera.handler_for

    def initialize_signalled(self, factory, on_face, camera_epoch, **kwargs):
        self._edge_signal = threading.Condition()
        self._edge_revision = 0
        self._edge_stream_lock = threading.Lock()
        def announced(*args, **options):
            with self._edge_signal:
                self._edge_revision += 1
                self._edge_signal.notify_all()
            return on_face(*args, **options)
        kwargs['interval_ms'] = interval_ms
        initialize(self, factory, announced, camera_epoch, **kwargs)
        # The existing worker sleeps self.interval AFTER a detection round.
        # Count that round toward the requested period so 100ms of detection
        # plus 100ms of sleeping does not produce a 5Hz, stale motion source.
        # Admission, retries, fault budgets and the 250ms source TTL stay intact.
        round_call = self._process_with_retry if self.slot_retry else self.process
        def paced_round(*args, **options):
            started = time.monotonic()
            try:
                return round_call(*args, **options)
            finally:
                self.interval = max(0., interval_ms-(time.monotonic()-started)*1000.)
        if self.slot_retry:
            self._process_with_retry = paced_round
        else:
            self.process = paced_round

    def handler_for(state):
        class Handler(base_handler(state)):
            def do_GET(self):
                url = urlsplit(self.path)
                if url.path == GET_PATH:
                    return self.respond(200, observation(state))
                if url.path != STREAM_PATH:
                    return super().do_GET()
                face = getattr(state.identity, 'face_targets', None)
                if face is None:
                    return self.respond(503, {'error': 'Face source unavailable'})
                values = parse_qs(url.query).get('duration_ms', ['10000'])
                if len(values) != 1 or not values[0].isdigit() or not 1 <= int(values[0]) <= 10000:
                    return self.respond(400, {'error': 'Use 1..10000ms'})
                if not face._edge_stream_lock.acquire(blocking=False):
                    return self.respond(409, {'error': 'One face stream at a time'})
                try:
                    self.connection.settimeout(.25)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/x-ndjson')
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    self.close_connection = True
                    end = time.monotonic()+int(values[0])/1000.
                    with face._edge_signal:
                        revision = face._edge_revision
                    while time.monotonic() < end:
                        raw = (json.dumps(observation(state), separators=(',', ':'))+'\n').encode()
                        if len(raw) > 8192:
                            raise ValueError('Face observation exceeds packet bound')
                        self.wfile.write(raw)
                        self.wfile.flush()
                        with face._edge_signal:
                            wait = max(0., min(.05, end-time.monotonic()))
                            if face._edge_revision == revision and wait:
                                face._edge_signal.wait(timeout=wait)
                            revision = face._edge_revision
                except (OSError, ValueError):
                    self.close_connection = True
                finally:
                    face._edge_stream_lock.release()
        return Handler

    FaceTargetService.__init__ = initialize_signalled
    camera.handler_for = handler_for
    camera._edge_face_source_installed = True
