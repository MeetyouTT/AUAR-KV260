# -*- coding: utf-8 -*-
"""潜动层（L0）纯逻辑单测：呼吸 / 重心 / 微摆（`avatar_timing.idle_offsets`）。

不依赖 Qt / PIL —— 潜动层是**纯解析函数**，播放层（qt_widgets / demo_stage）与
出片脚本（tools/make_alive_sample.py）都调用它，故这里只测数学与设计约束。
"""
import pytest

from board.interaction import avatar_timing as at

NEUTRAL = at.IdleOffsets(0.0, 0.0, 1.0, 0.0)
#: 合同显示框（板端与 PC 一致）：waist-up 素材按宽铺满 423、高 436
DISPLAY_H = 436.0


def _sample(seconds, step=0.01):
    n = int(round(seconds / step))
    return [at.idle_offsets(i * step) for i in range(n + 1)]


def _dist(a, b):
    """两个姿态的显示距离（像素）：位移直接算，缩放/旋转折算成像素。"""
    return (abs(a.dx - b.dx) + abs(a.dy - b.dy)
            + abs(a.scale_y - b.scale_y) * DISPLAY_H
            + abs(a.tilt_deg - b.tilt_deg) * 3.14159265 / 180.0 * DISPLAY_H * 0.5)


# --------------------------------------------------------------------------- #
# I1~I3 中性位：进场不跳变、可一键关闭
# --------------------------------------------------------------------------- #
def test_neutral_at_zero():
    assert at.idle_offsets(0.0) == NEUTRAL


def test_neutral_when_time_not_positive():
    assert at.idle_offsets(-1e-9) == NEUTRAL
    assert at.idle_offsets(-5.0) == NEUTRAL


def test_neutral_when_gain_zero():
    assert at.idle_offsets(3.3, gain=0.0) == NEUTRAL


# --------------------------------------------------------------------------- #
# I4 幅度与方向：呼吸/微摆单向（只隆起、只偏一侧），重心双向
# --------------------------------------------------------------------------- #
def test_amplitude_within_design():
    for off in _sample(300.0):
        assert abs(off.dx) <= at.IDLE_SWAY_AMP_X + 1e-9
        assert 0.0 <= off.dy <= at.IDLE_SWAY_AMP_Y + 1e-9
        assert 1.0 <= off.scale_y <= 1.0 + at.IDLE_BREATH_AMP + 1e-9
        assert 0.0 <= off.tilt_deg <= at.IDLE_TILT_AMP_DEG + 1e-9


def test_breathing_never_shrinks():
    """呼吸只"隆起"不"缩小" —— 素材是静止基线，缩到负值会穿帮。"""
    assert all(off.scale_y >= 1.0 for off in _sample(120.0))


def test_sway_is_two_way():
    """重心左右双向摆动（看得到 ±），否则像"单侧漂移"。"""
    xs = [off.dx for off in _sample(60.0)]
    assert min(xs) < -0.9 and max(xs) > 0.9


# --------------------------------------------------------------------------- #
# I5 平滑度：24fps 下帧间变化必须是亚像素级（否则观感是"抖"）
# --------------------------------------------------------------------------- #
def test_no_jump_at_24fps():
    offs = _sample(60.0, step=1.0 / 24.0)
    worst = max(_dist(a, b) for a, b in zip(offs, offs[1:]))
    assert worst < 0.25, "24fps 最大帧间变化 %.3f px 过大" % worst


# --------------------------------------------------------------------------- #
# I6 不重复：200 秒尺度上不能回到同一姿态
# --------------------------------------------------------------------------- #
def test_not_repeating_within_200s():
    dists = [_dist(at.idle_offsets(i * 0.25), at.idle_offsets(i * 0.25 + 200.0))
             for i in range(240)]
    assert min(dists) > 0.02, "存在 t 与 t+200s 几乎重合（周期太短）"
    assert sum(dists) / len(dists) > 0.2, "平均姿态距离过小"


# --------------------------------------------------------------------------- #
# I7~I8 周期：复合周期远超观感时长；呼吸周期真为 3.7s
# --------------------------------------------------------------------------- #
def test_composite_period_is_long():
    period = at.idle_composite_period()
    assert 200.0 < period < 1e9


def test_breath_period_peak_count():
    vals = [off.scale_y for off in _sample(60.0, step=0.05)]
    peaks = sum(1 for i in range(1, len(vals) - 1)
                if vals[i] > vals[i - 1] and vals[i] >= vals[i + 1])
    assert abs(peaks - 60.0 / at.IDLE_BREATH_PERIOD) <= 1.0


# --------------------------------------------------------------------------- #
# I9 增益线性：样品对比档 ×1 / ×2 / ×4 可信（便于选幅度）
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("t", [0.7, 1.9, 3.7, 8.3, 12.5])
def test_gain_scales_linearly(t):
    base = at.idle_offsets(t)
    for gain in (2.0, 4.0):
        got = at.idle_offsets(t, gain=gain)
        assert got.dx == pytest.approx(base.dx * gain)
        assert got.dy == pytest.approx(base.dy * gain)
        assert got.tilt_deg == pytest.approx(base.tilt_deg * gain)
        assert got.scale_y == pytest.approx(1.0 + (base.scale_y - 1.0) * gain)
