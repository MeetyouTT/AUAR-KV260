# -*- coding: utf-8 -*-
"""avatar_assets 纯逻辑单测 + AvatarPanel 帧序列接入集成测试。

基于方案：玩偶帧序列素材（assets/avatar/<素材名>/）优先，缺失回退 B2V 矢量。
不依赖 pytest-qt：使用最小 QApplication 单例 fixture（offscreen 平台）。
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QApplication

from board.interaction import avatar_assets as av

ALL_STATES = ("IDLE", "PRESENT", "LISTENING", "THINKING", "SPEAKING", "SPEAKING_LOW",
              "CAMERA_LOST", "NETWORK_LOST", "CANCELLED", "ERROR")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _make_frames(root, name, count=3):
    """在 root/<name>/ 生成 count 张 8x8 PNG 帧，返回该目录。"""
    from PySide6.QtGui import QColor, QImage
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        img = QImage(8, 8, QImage.Format_ARGB32)
        img.fill(QColor(0, 255, 0, 255))
        assert img.save(str(d / ("%06d.png" % i)), "PNG")
    return d


# --------------------------------------------------------------------------- #
# 纯逻辑
# --------------------------------------------------------------------------- #
def test_state_asset_mapping_defaults():
    assert av.asset_name("IDLE") == "idle_normal"
    assert av.asset_name("SPEAKING") == "talking_normal"
    assert av.asset_name("SPEAKING_LOW") == "talking_low"   # 低落播报
    assert av.asset_name("NOT_A_STATE") == "idle_normal"  # 未知回退 IDLE


def test_all_states_have_asset_name():
    assert set(ALL_STATES).issubset(set(av.STATE_ASSET.keys()))
    for state in ALL_STATES:
        assert av.asset_name(state)


def test_frames_absent_returns_none(tmp_path):
    assert av.frames_dir("IDLE", root=tmp_path) is None
    assert av.has_frames("IDLE", root=tmp_path) is False
    assert av.list_frames(tmp_path / "not_exist") == []


def test_frames_dir_found_and_sorted(tmp_path):
    d = _make_frames(tmp_path, "idle_normal", count=3)
    assert av.frames_dir("IDLE", root=tmp_path) == d
    assert [p.name for p in av.list_frames(d)] == [
        "000000.png", "000001.png", "000002.png"]


def test_list_frames_ignores_non_images(tmp_path):
    d = _make_frames(tmp_path, "idle_normal", count=2)
    (d / "meta.json").write_text("{}", encoding="utf-8")
    (d / "notes.txt").write_text("x", encoding="utf-8")
    assert [p.name for p in av.list_frames(d)] == ["000000.png", "000001.png"]


def test_frames_fps_default_and_meta(tmp_path):
    d = _make_frames(tmp_path, "idle_normal")
    assert av.frames_fps(d) == av.DEFAULT_FPS
    (d / "meta.json").write_text('{"fps": 12}', encoding="utf-8")
    assert av.frames_fps(d) == 12.0
    (d / "meta.json").write_text('{"fps": 0}', encoding="utf-8")
    assert av.frames_fps(d) == av.DEFAULT_FPS
    (d / "meta.json").write_text("not json", encoding="utf-8")
    assert av.frames_fps(d) == av.DEFAULT_FPS


def test_frames_dir_falls_back_to_idle(tmp_path):
    # 无 PRESENT 专属素材，但存在兜底 idle_normal → 回退兜底
    d = _make_frames(tmp_path, "idle_normal")
    assert av.frames_dir("PRESENT", root=tmp_path) == d


# --------------------------------------------------------------------------- #
# 状态专属中间兜底（FALLBACK_BY_STATE）
# --------------------------------------------------------------------------- #
def test_fallback_chain_speaking_low():
    assert av.fallback_chain("SPEAKING_LOW") == ("talking_low", "talking_normal",
                                                 "idle_normal")
    # 未定义中间兜底的状态 → 链与旧行为一致
    assert av.fallback_chain("THINKING") == ("idle_thinking", "idle_normal")
    assert av.fallback_chain("NOT_A_STATE") == ("idle_normal",)  # 去重


def test_speaking_low_prefers_talking_normal_before_idle(tmp_path):
    """低落播报素材未入库时，回退到 talking_normal（而不是待机素材）。"""
    normal = _make_frames(tmp_path, "talking_normal")
    _make_frames(tmp_path, "idle_normal")
    assert av.frames_dir("SPEAKING_LOW", root=tmp_path) == normal


def test_speaking_low_uses_own_asset_when_present(tmp_path):
    low = _make_frames(tmp_path, "talking_low")
    _make_frames(tmp_path, "talking_normal")
    assert av.frames_dir("SPEAKING_LOW", root=tmp_path) == low


# --------------------------------------------------------------------------- #
# AvatarPanel 接入集成
# --------------------------------------------------------------------------- #
def _render(panel, state="IDLE"):
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QImage, QPainter
    device = QImage(568, 397, QImage.Format_ARGB32)
    painter = QPainter(device)
    try:
        panel._render_avatar(painter, QRect(0, 0, 568, 397), panel.style,
                             {"runtime_state": state, "avatar_anim": {"enabled": False}})
    finally:
        painter.end()


def _panel(tmp_path):
    from board.interaction.qt_widgets import AvatarPanel
    from board.interaction.ui_state import UiState
    return AvatarPanel(UiState(), sprite_root=tmp_path)


def test_panel_prefers_sprite_when_frames_present(qapp, tmp_path, monkeypatch):
    """有素材帧序列时走帧序列分支，不再调用 B2V 矢量主体。"""
    from board.interaction.qt_widgets import _SpriteSequence
    _make_frames(tmp_path, "idle_normal")
    panel = _panel(tmp_path)

    called = []
    monkeypatch.setattr(panel, "_draw_sprite_base",
                        lambda p, rect, st, spec: called.append(rect))
    monkeypatch.setattr(panel, "_anim_state",
                        lambda t: {"blink_close": 0.0, "look_dx": 0.0,
                                   "scale": 1.0, "mouth": 0.0})

    seq = panel._sprite_sequence("IDLE", QRectF(0, 0, 568, 397))
    assert isinstance(seq, _SpriteSequence)
    assert len(seq.frames) == 3

    _render(panel, "IDLE")
    assert called == []  # 未走矢量分支


def test_panel_falls_back_to_vector_without_frames(qapp, tmp_path, monkeypatch):
    """无素材时回退 B2V 矢量主体（保持既有行为）。"""
    panel = _panel(tmp_path)  # 空目录 → 无素材

    called = []
    monkeypatch.setattr(panel, "_draw_sprite_base",
                        lambda p, rect, st, spec: called.append(rect))
    monkeypatch.setattr(panel, "_anim_state",
                        lambda t: {"blink_close": 0.0, "look_dx": 0.0,
                                   "scale": 1.0, "mouth": 0.0})

    _render(panel, "IDLE")
    assert len(called) == 1
