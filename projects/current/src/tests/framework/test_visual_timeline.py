import copy

import pytest

from board.visual_timeline import VisualTimelineCollector


def health(frame, count=1, **changes):
    result = dict(board_boot_id='boot', service_epoch='service', camera_epoch='camera',
                  role='DPU_YOLOX_PERSON_PREVIEW', detector={'count_kind': 'people'},
                  observation_frame_id=frame, people_count=count, observation_age_ms=10,
                  capture_age_ms=5, camera_error='', detector_error='',
                  timestamp_kind='appsink_dequeue_monotonic',
                  identity={'person_id': 'PRIVATE_ID', 'display_name': 'PRIVATE_NAME'},
                  jpeg_base64='PRIVATE_IMAGE')
    result.update(changes)
    return result


def collector(sink=None):
    saved = []
    sink = sink or (lambda *args, **kwargs: saved.append((args, copy.deepcopy(kwargs))))
    observer = VisualTimelineCollector('boot', sink, {'kind': 'device', 'id': 'device'},
                                       utc_clock=lambda: 10000)
    return observer, saved


def feed(observer, frame, stamp, count=1, **changes):
    return observer.ingest_health(health(frame, count, **changes),
                                  requested_mono_ms=stamp, received_mono_ms=stamp + 10)


def test_stability_uses_new_detection_frames_and_never_copies_private_fields():
    observer, saved = collector()
    assert feed(observer, 1, 1000) is None
    assert feed(observer, 1, 1500) is None
    assert feed(observer, 2, 1700) is None
    assert feed(observer, 3, 1800)
    assert len(saved) == 1
    assert 'PRIVATE' not in repr(saved)
    assert saved[0][0][2] == 'camera_observed'
    assert {'field':'source_frame_id','value':3} in saved[0][1]['metadata']['claims']
    assert observer.health()['identity_access_granted'] is False


def test_jitter_and_repeated_stable_counts_do_not_fill_timeline():
    observer, saved = collector()
    for frame, stamp, count in [(1,1000,1),(2,1300,0),(3,1600,1),(4,1900,1),(5,2200,1),
                                (6,2500,1),(7,2800,1)]:
        feed(observer, frame, stamp, count)
    assert len(saved) == 1


def test_unavailable_camera_cannot_be_recorded_as_departure():
    observer, saved = collector()
    for frame, stamp in [(1,1000),(2,1300),(3,1600)]:
        feed(observer, frame, stamp)
    for frame in range(4,8):
        assert feed(observer, frame, 2000+frame*300, 0, camera_error='lost') is None
    assert len(saved) == 1
    assert observer.health()['current_count'] is None
    for frame, stamp in [(8,5000),(9,5300),(10,5600)]:
        event = feed(observer, frame, stamp, 0)
    assert {'field':'event_kind','value':'no_person_detected'} in event['metadata']['claims']
    assert '离开' not in event['text']


@pytest.mark.parametrize('changes', [
    {'board_boot_id':'other'}, {'role':'CPU_FACE_PREVIEW'},
    {'detector':{'count_kind':'faces'}}, {'detector':None}, {'detector':[]},
    {'observation_age_ms':800},
    {'capture_age_ms':800}, {'observation_age_ms':float('nan')},
    {'people_count':True}, {'observation_frame_id':True},
])
def test_wrong_boot_model_stale_and_invalid_data_fail_closed(changes):
    observer, saved = collector()
    for frame, stamp in [(1,1000),(2,1400),(3,1800)]:
        assert feed(observer, frame, stamp, **changes) is None
    assert not saved


def test_late_response_and_old_epoch_do_not_rollback_source():
    observer, saved = collector()
    feed(observer, 1, 1000)
    feed(observer, 2, 1300)
    feed(observer, 3, 1600)
    feed(observer, 1, 2000, camera_epoch='new-camera')
    assert feed(observer, 4, 1900) is None
    assert feed(observer, 5, 2100) is None
    feed(observer, 2, 2300, camera_epoch='new-camera')
    assert feed(observer, 3, 2600, camera_epoch='new-camera')
    assert len(saved) == 2


def test_uncertain_sink_write_retries_identical_event_id_and_payload():
    calls = []
    def sink(*args, **kwargs):
        calls.append((args, copy.deepcopy(kwargs)))
        if len(calls) == 1:
            raise OSError('commit acknowledgement lost')
    observer, _ = collector(sink)
    feed(observer, 1, 1000)
    feed(observer, 2, 1300)
    with pytest.raises(OSError):
        feed(observer, 3, 1600)
    assert feed(observer, 4, 1700)
    assert calls[0] == calls[1]


def test_fixtures_require_explicit_opt_in():
    observer, saved = collector()
    assert observer.ingest_health(health(1),requested_mono_ms=1000,
                                  received_mono_ms=1010,source_kind='fixture') is None
    assert not saved
