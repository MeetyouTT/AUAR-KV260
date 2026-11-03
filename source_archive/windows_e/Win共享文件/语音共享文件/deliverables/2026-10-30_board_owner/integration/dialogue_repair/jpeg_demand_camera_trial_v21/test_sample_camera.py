"""Public numeric sampling fixtures. No process or device is queried."""
import copy
import types
from unittest.mock import patch

import pytest

import sample_camera as sample


def rows():
    return [
        {'process': {'mono': 10, 'ticks': 1000, 'birth': '23', 'rss_bytes': 10000, 'system_busy_ticks': 3000},
         'health': {'pid': 12, 'board_boot_id': 'public', 'service_epoch': 'one', 'camera_epoch': 'two',
                    'capture_frames': 50, 'detected_frames': 40, 'preview_frames': 45,
                    'people_count': 1, 'face_source_age_ms': 80}},
        {'process': {'mono': 40, 'ticks': 2500, 'birth': '23', 'rss_bytes': 11000, 'system_busy_ticks': 6000},
         'health': {'pid': 12, 'board_boot_id': 'public', 'service_epoch': 'one', 'camera_epoch': 'two',
                    'capture_frames': 500, 'detected_frames': 340, 'preview_frames': 495,
                    'people_count': 1, 'face_source_age_ms': 90}},
    ]


def test_numeric_cpu_frame_and_memory_units():
    result = sample.summarize(rows(), 100)
    assert result['seconds'] == 30
    assert result['camera_cpu_cores'] == .5
    assert result['whole_system_busy_cores'] == 1
    assert result['preview_frames_per_second'] == 15
    assert result['detected_frames_per_second'] == 10
    assert result['camera_rss_max_bytes'] == 11000
    assert result['people_counts'] == [1, 1]


@pytest.mark.parametrize('section,key,value', [
    ('process', 'birth', 'new'), ('process', 'mono', 10), ('process', 'ticks', 999),
    ('process', 'system_busy_ticks', 2999), ('health', 'pid', 13),
    ('health', 'camera_epoch', 'new'), ('health', 'service_epoch', 'new'),
    ('health', 'capture_frames', 50), ('health', 'preview_frames', 45),
])
def test_changed_owner_epoch_or_nonprogressing_counter_refuses(section, key, value):
    changed = rows()
    changed[-1][section][key] = value
    with pytest.raises(ValueError):
        sample.summarize(changed, 100)


def test_gui_must_be_closed_without_retained_original_gtk():
    complete = types.SimpleNamespace(stdout='MainPID=0\nActiveState=inactive\nJob=\n')
    with patch.object(sample.subprocess, 'run', return_value=complete) as run, \
            patch.object(sample.Path, 'exists', return_value=False):
        sample.gui_closed()
        assert run.call_args.args[0][:3] == ['systemctl', 'show', '--all']
    with patch.object(sample.subprocess, 'run', return_value=complete), \
            patch.object(sample.Path, 'exists', return_value=True):
        with pytest.raises(ValueError):
            sample.gui_closed()
    running = types.SimpleNamespace(stdout='MainPID=99\nActiveState=active\nJob=\n')
    with patch.object(sample.subprocess, 'run', return_value=running):
        with pytest.raises(ValueError):
            sample.gui_closed()


def test_health_projection_excludes_identity_names_images_and_private_values():
    native = {'fenced': False, 'seed_loaded': True, 'primary_calls': 7,
              'primary_period_overruns': 0, 'optional_overruns': {'yunet': 0, 'sface': 0}}
    executor = types.SimpleNamespace(native_health=lambda _: (native, {}))
    health = {'pid': 12, 'board_boot_id': 'public', 'service_epoch': 'one', 'camera_epoch': 'two',
              'capture_frames': 50, 'detected_frames': 40, 'preview_frames': 45, 'preview_buffers': 8,
              'identity': {'ready': True, 'private_name': 'DO_NOT_EMIT',
                           'face_targets': {'ready': True, 'source_age_ms': 80}},
              'private_image': b'DO_NOT_EMIT', 'people_count': 1}
    result = sample.health_projection(health, executor)
    assert 'DO_NOT_EMIT' not in str(result)
    for key in ('camera_error', 'preview_error', 'detector_error'):
        changed = copy.deepcopy(health)
        changed[key] = 'private payload'
        with pytest.raises(ValueError):
            sample.health_projection(changed, executor)
