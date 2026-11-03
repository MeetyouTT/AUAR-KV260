# -*- coding: utf-8 -*-
"""方案 B2 执行层测试：_anim_state 帧表插值/周期优先级/intensity 与通道映射。

不依赖 pytest-qt：使用最小 QApplication 单例 fixture（offscreen 平台），
仅覆盖逻辑层可断言部分，不覆盖像素级渲染。
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture()
def avatar_panel(qapp):
    from board.interaction.qt_widgets import AvatarPanel
    from board.interaction.ui_state import UiState
    ui = UiState()
    return AvatarPanel(ui)


def test_cyclic_keyframe_value_interpolation(avatar_panel):
    """线性插值：两关键帧 [0,1] 的中点出现在 phase=0.25（position=0.5）。"""
    assert avatar_panel._cyclic_keyframe_value([0.0, 1.0], 0.25, 0.0) == pytest.approx(0.5)


def test_cyclic_keyframe_value_wraps(avatar_panel):
    """循环：超出末尾回绕到首帧。"""
    # 帧表 [0,1,0]，phase=0.5 -> position=1.5 -> 1 与 0 之间 -> 0.5
    assert avatar_panel._cyclic_keyframe_value([0.0, 1.0, 0.0], 0.5, 0.0) == pytest.approx(0.5)
    # phase=0.0 -> 首帧
    assert avatar_panel._cyclic_keyframe_value([0.0, 1.0, 0.0], 0.0, 0.0) == pytest.approx(0.0)


def test_anim_state_disabled_is_static(avatar_panel):
    """enabled=False → 静态零值（方案 C 数据层默认）。"""
    avatar_panel.ui.set_avatar_anim("blink", enabled=False)
    values = avatar_panel._anim_state(123.0)
    assert values == {
        "blink_close": 0.0,
        "look_dx": 0.0,
        "scale": 1.0,
        "mouth": 0.0,
    }


def test_anim_state_blink_peak(avatar_panel):
    """blink 周期 1000ms：phase=1/3 处闭眼程度达到峰值 1.0。"""
    avatar_panel.ui.set_avatar_anim(
        "blink", params={"period_ms": 1000}, enabled=True
    )
    first = avatar_panel._anim_state(0.0)
    peak = avatar_panel._anim_state(1.0 / 3.0)
    assert first["blink_close"] == pytest.approx(0.0)
    assert peak["blink_close"] > 0.99


def test_anim_state_channels_are_mapped(avatar_panel):
    """speak 帧表：eye 通道 → blink_close=0，mouth 通道 → mouth=0.6。"""
    avatar_panel.ui.set_avatar_anim("speak", enabled=True)
    values = avatar_panel._anim_state(0.0)
    assert values["blink_close"] == pytest.approx(0.0)
    assert values["mouth"] == pytest.approx(0.6)


def test_anim_state_period_priority(avatar_panel):
    """周期优先级：params.period_ms 覆盖 ui_tokens 缺省。"""
    avatar_panel.ui.set_avatar_anim(
        "blink", params={"period_ms": 300}, enabled=True
    )
    # 周期 300ms：phase=1/3 对应 t=100ms
    peak = avatar_panel._anim_state(0.1)
    assert peak["blink_close"] > 0.99


def test_anim_state_intensity_scales_values(avatar_panel):
    """intensity 缺省 1.0；设置为 0.5 时 blink 峰值减半、scale 回到 1。"""
    avatar_panel.ui.set_avatar_anim(
        "blink", params={"period_ms": 1000, "intensity": 0.5}, enabled=True
    )
    peak = avatar_panel._anim_state(1.0 / 3.0)
    assert peak["blink_close"] == pytest.approx(0.5, abs=1e-6)
    assert peak["scale"] == pytest.approx(1.0, abs=1e-6)


def test_face_anchor_is_normalized_and_inside_body(avatar_panel):
    """B2V：_face_anchor 由头部几何推导，锚框位于 body_rect 内且比例正确。"""
    from PySide6.QtCore import QRectF
    rect = QRectF(0.0, 0.0, 552.0, 359.0)
    anchor = avatar_panel._face_anchor(rect)
    assert 0.0 < anchor.left() < anchor.right() < rect.right()
    assert 0.0 < anchor.top() < anchor.bottom() < rect.bottom()
    assert anchor.width() == pytest.approx(rect.width() * 0.28)
    assert anchor.height() == pytest.approx(rect.height() * 0.40)


def test_panel_has_no_bitmap_base(avatar_panel):
    """B2V：位图底图相关成员已删除，矢量主体接口存在。"""
    assert not hasattr(avatar_panel, "_avatar_base")
    assert not hasattr(avatar_panel, "_fit_image_rect")
    assert not hasattr(avatar_panel, "_sprite_face_rect")
    assert hasattr(avatar_panel, "_draw_sprite_base")
    assert hasattr(avatar_panel, "_face_anchor")


def test_render_uses_vector_base(avatar_panel, monkeypatch):
    """B2V：_render_avatar 调用 _draw_sprite_base（矢量主体）且不再触碰位图。"""
    from PySide6.QtCore import QRect, QRectF
    from PySide6.QtGui import QImage, QPainter

    called = []
    monkeypatch.setattr(
        avatar_panel,
        "_draw_sprite_base",
        lambda p, rect, st, spec: called.append(rect),
    )
    monkeypatch.setattr(
        avatar_panel,
        "_anim_state",
        lambda t: {"blink_close": 0.0, "look_dx": 0.0, "scale": 1.0, "mouth": 0.0},
    )
    # 断言目标是「矢量主体」分支：强制无帧序列素材，避免磁盘素材影响确定性
    monkeypatch.setattr(avatar_panel, "_sprite_sequence", lambda *a, **k: None)

    device = QImage(568, 397, QImage.Format_ARGB32)
    painter = QPainter(device)
    try:
        avatar_panel._render_avatar(
            painter,
            QRect(0, 0, 568, 397),
            avatar_panel.style,
            {"runtime_state": "IDLE", "avatar_anim": {"enabled": False}},
        )
    finally:
        painter.end()
    assert len(called) == 1
    assert isinstance(called[0], QRectF)
