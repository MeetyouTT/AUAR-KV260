"""Real CPU-model offline identity check. No camera/device/user database opened."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))


def check(image_path):
    import cv2
    from board.identity.camera_faces import CameraFaceExtractor, config_for
    from board.identity.live import IdentityService
    from board.identity.store import IdentityStore
    from board.interaction.ui_contract import millis, validate_snapshot
    from board.vision.ui_camera_service import CameraState
    cv2.setNumThreads(2)
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError('Cannot read reference image')
    h, w = image.shape[:2]
    config = config_for(AURA, 'config/board_identity.json')
    state = CameraState('offline-reference-only', 'offline-identity-check')
    checks = []
    timings = []
    def require(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)
    def wait(predicate, keepalive=None):
        deadline = time.monotonic()+15
        while time.monotonic() < deadline:
            if predicate():
                return
            if keepalive is not None:
                keepalive()
            time.sleep(.005)
        raise AssertionError('Identity worker did not finish: '+str(state.identity.health()))
    def frame(fid, tid=1, visible=True):
        stamp = millis()
        state.captured(stamp)
        obs = {'target_id': tid, 'tracks': [{'track_id': tid, 'generation': 1, 'visible': visible,
                                           'confirmed': True, 'box': (0, 0, w, h)}]}
        state.observed(fid, stamp, obs, 0.)
        return stamp, obs
    def infer(fid, tid=1, source=None):
        stamp, obs = frame(fid, tid)
        count = state.identity.processed+state.identity.discarded
        state.identity.offer(image if source is None else source, fid, stamp, obs, state.camera_epoch)
        started = time.monotonic()
        # A static replay still needs current capture/detection ownership while
        # ARM CPU inference runs. Live capture updates it independently too.
        # Do not relax production result expiry or manufacture a second job.
        wait(lambda: state.identity.processed+state.identity.discarded > count,
             keepalive=lambda: frame(fid, tid))
        timings.append(round((time.monotonic()-started)*1000, 2))
        return validate_snapshot(state.snapshot(), state.boot, millis())['modules']['identity']
    def command(action, params, cid):
        value = state.snapshot(); now = millis()
        return state.command({'protocol_version': 'aura-ui-1', 'board_boot_id': state.boot,
            'service_epoch': state.epoch, 'command_id': cid, 'ui_epoch': 'offline-test-ui', 'ui_generation': 0,
            'context': value['context'], 'snapshot_sequence': value['sequence'], 'issued_mono_ms': now,
            'deadline_mono_ms': now+2500, 'action': action, 'params': params})
    with tempfile.TemporaryDirectory(prefix='aura-identity-reference-') as temp:
        store = IdentityStore(Path(temp)/'reference.sqlite3', config['model_id'], 128,
                              config['threshold'], config['ambiguity_margin'], allow_cross_thread=True)
        service = state.identity = IdentityService(store, lambda: CameraFaceExtractor(config),
            state.identity_target, lock=state.lock, interval_ms=100)
        service.start()
        try:
            wait(lambda: service.ready or bool(service.error))
            require('real_models_loaded', service.ready and not service.error)
            first = infer(1)
            require('unknown_before_enrollment', first['state'] == 'UNKNOWN' and service.result is not None)
            require('real_embedding_has_128_dimensions', len(service.result['embedding']) == 128)
            ack = command('identity_enroll', {'target': state.identity_target(), 'display_name': '参考样本',
                                             'confirmed': True}, 'offline-enroll')
            require('enrollment_committed', ack['accepted'])
            require('known_after_enrollment', state.snapshot()['modules']['identity']['state'] == 'KNOWN')
            reopened = IdentityStore(Path(temp)/'reference.sqlite3', config['model_id'], 128,
                                      config['threshold'], config['ambiguity_margin'])
            try:
                require('sqlite_persistence', reopened.match(service.result['embedding']).state == 'KNOWN')
            finally:
                reopened.close()
            frame(2, visible=False)
            require('lost_target_hides_identity', not state.snapshot()['modules']['identity']['display_name'])
            returned = infer(3, tid=9)
            require('same_image_new_track_recognized', returned['state'] == 'KNOWN')
            import numpy as np
            blank = infer(4, tid=9, source=np.zeros_like(image))
            require('blank_frame_clears_old_name', blank['state'] == 'UNKNOWN' and not blank['display_name'])
            require('blank_frame_cannot_enroll', not state.snapshot()['capabilities']['identity_enroll'])
            identity = infer(5, tid=9)
            ack = command('identity_delete', {'person_id': identity['person_id'],
                'db_version': identity['db_version'], 'confirmed': True}, 'offline-delete')
            require('deletion_committed', ack['accepted'] and not store.people())
            require('unknown_after_deletion', infer(6, tid=9)['state'] == 'UNKNOWN')
            require('no_photos_persisted', all(p.suffix in ('.sqlite3',) for p in Path(temp).iterdir()))
        finally:
            service.close()
    return {'status': 'PASS', 'scope': 'HOST_REAL_CPU_MODELS_STATIC_IMAGE_NOT_BOARD',
            'opencv': cv2.__version__, 'reference_image_sha256': hashlib.sha256(Path(image_path).read_bytes()).hexdigest(),
            'checks': checks, 'worker_round_trip_ms': timings, 'embedding_exported': False,
            'user_database_modified': False, 'board_verified': False,
            'accuracy_calibrated': False, 'identity_backend': 'CPU_SFACE_REFERENCE',
            'ownership_refresh': 'replayed_static_frame_not_live_camera'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True, help='Public reference face, not a camera capture')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = check(args.image)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
