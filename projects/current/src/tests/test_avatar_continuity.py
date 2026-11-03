"""Continuity constraints catch pose jumps that ordinary FSM tests miss."""
import math
import random
import pytest
from PIL import Image
from board.interaction.avatar_player import AvatarPlayer
from board.interaction.avatar_timing import Segments, IdleOffsets


def player():
    p = AvatarPlayer(rng=random.Random(7))
    p.idle_gain = 0
    return p


@pytest.mark.parametrize('hz', [12, 30, 60])
def test_disconnected_windows_never_cut_and_entry_has_no_random_phase(hz):
    p = player()
    seg = Segments((0, 12), (12, 19), (19, 38), ((12, 19), (28, 35), (20, 27)))
    positions = []
    for i in range(hz * 20):
        t, _, alpha = p.segment_stage_time('SPEAKING_NEUTRAL', seg, 24, 1.2, i / hz)
        positions.append(t * 24)
        assert alpha == 0  # Never blend unrelated poses.
    assert max(abs(a - b) for a, b in zip(positions, positions[1:])) <= 24 / hz + 1e-6
    assert min(positions[hz:]) >= 12
    assert max(positions) <= 19


def test_phase_and_tick_frequency_cannot_change_segment_pose():
    seg = Segments((0, 28), (28, 35), (35, 38))
    dense, sparse = player(), player()
    for i in range(300):
        dense.segment_stage_time('SPEAKING_NEUTRAL', seg, 24, 0.8, i / 30)
    got = dense.segment_stage_time('SPEAKING_NEUTRAL', seg, 24, 0.8, 10)[0]
    assert sparse.segment_stage_time('SPEAKING_NEUTRAL', seg, 24, 0.1, 10)[0] == pytest.approx(got)


@pytest.mark.parametrize('stop', [0.05, 0.6, 1.0, 1.4, 2.0])
def test_interruption_follows_adjacent_frames_and_recovers_under_one_second(stop):
    p = player()
    seg = Segments((0, 12), (12, 19), (19, 38))
    p.segment_stage_time('SPEAKING_NEUTRAL', seg, 24, 0, 0)
    before = p.segment_stage_time('SPEAKING_NEUTRAL', seg, 24, 0, stop)[0]
    p.request_exit()
    got = [p.segment_stage_time('SPEAKING_NEUTRAL', seg, 24, 0, stop + i / 60)[0] * 24
           for i in range(61)]
    assert got[0] == pytest.approx(before * 24)
    assert max(abs(a - b) for a, b in zip(got, got[1:])) <= 0.4 + 1e-6
    assert p._exit_done and got[-1] in (0, 38)
    # No backward restart when diagnostic blend becomes exit.
    sign = 1 if got[-1] >= got[0] else -1
    assert all(sign * (b - a) >= -1e-6 for a, b in zip(got, got[1:]))


def test_pool_rotation_recovers_to_last_frame_before_next_asset():
    p = player()
    seg = Segments((0, 12), (12, 19), (19, 38))
    p.segment_stage_time('SPEAKING_NEUTRAL', seg, 24, 0, 1)
    p._switch_pending = True
    p.request_exit()
    p.segment_stage_time('SPEAKING_NEUTRAL', seg, 24, 0, 1)
    got = p.segment_stage_time('SPEAKING_NEUTRAL', seg, 24, 0, 3)[0] * 24
    assert p._exit_done and got == 38


def test_single_frame_window_and_reset_have_no_stale_exit():
    p = player()
    seg = Segments((0, 4), (4, 4), (4, 8))
    assert p.segment_stage_time('SPEAKING', seg, 24, 9, 100)[0] * 24 == 4
    p.request_exit()
    p.segment_stage_time('SPEAKING', seg, 24, 0, 100)
    p.reset_playback()
    assert p.segment_stage_time('SPEAKING', seg, 24, 0, 0)[0] == 0
    assert not p._exit_done and not p._exit_requested


def test_fractional_offsets_do_not_round_to_whole_pixel_steps():
    image = Image.new('RGBA', (32, 40), (0, 0, 0, 0))
    image.paste((200, 80, 40, 255), (8, 8, 24, 32))
    # idle_offsets returns a named tuple; construct using its actual field names.
    from board.interaction.avatar_timing import idle_offsets
    base = idle_offsets(0, gain=0)
    a = AvatarPlayer._apply_offsets(image, base._replace(dx=0.1))
    b = AvatarPlayer._apply_offsets(image, base._replace(dx=0.2))
    assert a.tobytes() != b.tobytes()
