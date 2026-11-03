# -*- coding: utf-8 -*-
"""ui/ 1.1（板端 1024×600 三区）布局合同 + Qt 面板几何一致性单测。

覆盖：画布/三区数值自洽（无缝拼满）、玩偶框 423×516 与合同一致、下栏 9 项、
      左上内容不溢出、MainWindow 三区落位与离屏落盘 1024×600、
      以及帧序列**底部对齐**绘制（腰部切线贴框底）。
"""
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

_SPEC = os.path.join(os.path.dirname(__file__), "..", "ui")
CANVAS_W, CANVAS_H = 1024, 600


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtGui import QGuiApplication
    return QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture(scope="module")
def layout():
    with open(os.path.join(_SPEC, "ui_layout_spec.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def tokens():
    with open(os.path.join(_SPEC, "ui_tokens.json"), encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# 1) 合同数值自洽
# --------------------------------------------------------------------------- #
def test_schema_versions_are_1_1(layout, tokens):
    assert layout["schema_version"] == "1.1"
    assert tokens["schema_version"] == "1.2"


def test_canvas_is_board_1024x600_and_pc_keys_removed(layout):
    assert layout["canvas"] == {"width": CANVAS_W, "height": CANVAS_H}
    assert "top_bar" not in layout          # PC 档顶栏已废弃
    assert "status_bar" not in layout       # 旧键名 → bottom_bar


def test_three_zones_tile_the_canvas(layout):
    lp, rp, bb = layout["left_panel"], layout["right_panel"], layout["bottom_bar"]
    assert (lp["x0"], lp["x1"]) == (0, 585)
    assert (rp["x0"], rp["x1"]) == (585, CANVAS_W)
    assert (lp["y0"], lp["y1"]) == (0, 556)
    assert (rp["y0"], rp["y1"]) == (0, 556)
    assert (bb["x0"], bb["x1"], bb["y0"], bb["y1"]) == (0, CANVAS_W, 556, CANVAS_H)
    assert lp["x1"] == rp["x0"]                     # 左右无缝
    assert lp["y1"] == bb["y0"]                     # 上区与下栏贴合
    assert (bb["height"], layout["top_area"]["height"]) == (44, 556)
    assert (lp["x1"] - lp["x0"]) + (rp["x1"] - rp["x0"]) == CANVAS_W
    assert layout["split"]["left_width"] == 585 and layout["split"]["right_width"] == 439


def test_avatar_box_matches_frozen_framing(layout):
    ri = layout["right_inner"]
    rp = layout["right_panel"]
    assert (ri["avatar_box"]["width"], ri["avatar_box"]["height"]) == (423, 516)
    assert (ri["label_h"], ri["fade_h"]) == (24, 28)
    assert layout["framing"] == {"fit": "contain", "align": "bottom",
                                 "crop_bottom_ratio": 0.42, "safe_margin": 0}
    # 439×556 面板 - 2×8 padding - 24 标签 = 423×516（与合同玩偶框逐像素一致）
    assert rp["x1"] - rp["x0"] - 2 * rp["padding"] == 423
    assert rp["y1"] - rp["y0"] - 2 * rp["padding"] - ri["label_h"] == 516


def test_left_inner_content_fits_in_panel(layout):
    lp, li = layout["left_panel"], layout["left_inner"]
    used = (li["top_offset"] + li["video"]["height"] + li["info_line"]["height"]
            + 2 * li["separator_gap"] + li["dialogue"]["height"]
            + li["latency_line"]["height"] + li["events"]["height"])
    avail = lp["y1"] - lp["y0"] - 2 * lp["padding"]
    assert used <= avail, "左上内容 %d 超出可用高度 %d" % (used, avail)


def test_status_items_are_nine_unique(layout):
    items = layout["status_items"]
    assert len(items) == 9 and len(set(items)) == 9
    assert items == ["camera", "npu", "pl", "audio", "lan", "save",
                     "privacy", "mode", "fps"]


def test_tokens_are_board_profile(tokens):
    assert tokens["fonts"] == {"title": 16, "label": 13, "small": 11, "dialogue": 14}
    assert tokens["spacing"]["panel_padding"] == 8
    assert tokens["colors"]["panel_bg"] == "#FCFCF3"


# --------------------------------------------------------------------------- #
# 2) Qt 面板落位（两后端共用同一份合同）
# --------------------------------------------------------------------------- #
def test_mainwindow_three_zones_geometry(qapp, layout):
    from board.interaction.qt_app import MainWindow
    from board.interaction.ui_state import UiState
    win = MainWindow(UiState())
    assert (win.width(), win.height()) == (CANVAS_W, CANVAS_H)
    assert not hasattr(win, "top_bar")               # 顶栏已随 PC 档移除
    cam, av, bar = (win.camera_panel.geometry(), win.avatar_panel.geometry(),
                    win.status_bar.geometry())
    assert (cam.x(), cam.y(), cam.width(), cam.height()) == (0, 0, 585, 556)
    assert (av.x(), av.y(), av.width(), av.height()) == (585, 0, 439, 556)
    assert (bar.x(), bar.y(), bar.width(), bar.height()) == (0, 556, 1024, 44)


def test_avatar_panel_box_equals_contract_box(qapp):
    from board.interaction.qt_widgets import AvatarPanel
    from board.interaction.ui_state import UiState
    panel = AvatarPanel(UiState())
    panel.resize(439, 556)
    st = panel.style
    pad = st.layout["right_panel"]["padding"]
    label_h = st.layout["right_inner"]["label_h"]
    inner = panel.rect().adjusted(pad, pad, -pad, -pad)
    assert (inner.width(), inner.height() - label_h) == (423, 516)


def test_sprite_frame_is_bottom_aligned(qapp):
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QColor, QImage, QPainter
    from board.interaction.qt_widgets import AvatarPanel, _SpriteSequence

    frame = QImage(200, 100, QImage.Format_ARGB32)
    frame.fill(QColor(255, 0, 0))
    device = QImage(423, 516, QImage.Format_ARGB32)
    device.fill(QColor(0, 0, 0, 0))
    p = QPainter(device)
    try:
        AvatarPanel._draw_sprite_frame(p, QRectF(0, 0, 423, 516),
                                      _SpriteSequence([frame], 10.0), 0.0)
    finally:
        p.end()
    assert device.pixelColor(211, 515).name() == "#ff0000"   # 底边贴齐
    assert device.pixelColor(211, 210).alpha() == 0          # 上方留空（未垂直居中）


def test_overlay_slot_contract_and_rect(qapp, layout):
    """扩展位（D2）：合同留 80px 高、内容留空；Qt 侧矩形 = 面板内 (8,32,423,80)。"""
    from board.interaction.qt_widgets import AvatarPanel
    from board.interaction.ui_state import UiState

    slot = layout["right_inner"]["overlay_slot"]
    assert slot == {"enabled": True, "align": "top",
                    "reserved_height": 80, "content": "empty"}
    panel = AvatarPanel(UiState())
    panel.resize(439, 556)
    rect = panel.overlay_slot_rect()
    # pad 8 + label 24 → y=32；宽 = 439−2×8 = 423；高 = 合同预留 80
    assert (rect.x(), rect.y(), rect.width(), rect.height()) == (8, 32, 423, 80)


def _render_panel(panel) -> "object":
    from PySide6.QtGui import QColor, QImage
    image = QImage(panel.width(), panel.height(), QImage.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    panel.render(image)
    return image


def test_overlay_slot_default_paints_nothing(qapp, monkeypatch):
    """默认「留空」：扩展位区域保持面板底色。

    把素材绘制替换为空实现以**隔离验证扩展位本身**（现役 full 素材会顶满框高，
    腰部以上素材才留出这 80px 空档）。
    """
    from board.interaction.qt_widgets import AvatarPanel
    from board.interaction.ui_state import UiState
    panel = AvatarPanel(UiState())
    panel.resize(439, 556)
    monkeypatch.setattr(panel, "_render_avatar", lambda p, rect, st, snap: None)
    image = _render_panel(panel)
    rect = panel.overlay_slot_rect()
    assert image.pixelColor(rect.center()).name() == "#fcfcf3"


def test_overlay_slot_painter_hook_is_invoked(qapp, monkeypatch):
    """接入钩子生效：设置 painter 后由它填满扩展位，且 rect 与合同一致。"""
    from PySide6.QtGui import QColor
    from board.interaction.qt_widgets import AvatarPanel
    from board.interaction.ui_state import UiState
    panel = AvatarPanel(UiState())
    panel.resize(439, 556)
    monkeypatch.setattr(panel, "_render_avatar", lambda p, rect, st, snap: None)
    seen = []

    def painter(p, rect, st, snap):
        seen.append((rect, st, snap))
        p.fillRect(rect, QColor(255, 0, 0))

    panel.set_overlay_slot_painter(painter)
    image = _render_panel(panel)
    rect = panel.overlay_slot_rect()
    assert seen and seen[0][0] == rect
    assert image.pixelColor(rect.center()).name() == "#ff0000"
    # 扩展位下方仍为面板底色（未被扩展位覆盖）
    assert image.pixelColor(rect.center().x(), rect.bottom() + 60).name() == "#fcfcf3"


def test_overlay_slot_can_be_disabled(qapp):
    """enabled=false 或 reserved_height=0 → 空矩形（完全不绘制）；测后恢复合同原值。"""
    from board.interaction.qt_widgets import AvatarPanel
    from board.interaction.ui_state import UiState
    panel = AvatarPanel(UiState())
    panel.resize(439, 556)
    ri = panel.style.layout["right_inner"]
    original = ri["overlay_slot"]
    try:
        ri["overlay_slot"] = {"enabled": False, "align": "top",
                              "reserved_height": 80, "content": "empty"}
        assert panel.overlay_slot_rect().isNull()
        ri["overlay_slot"] = {"enabled": True, "align": "top",
                              "reserved_height": 0, "content": "empty"}
        assert panel.overlay_slot_rect().isNull()
    finally:
        ri["overlay_slot"] = original


def test_render_to_file_writes_1024x600(qapp, tmp_path):
    from PySide6.QtGui import QImage
    from board.interaction.qt_app import MainWindow
    from board.interaction.ui_state import UiState
    ui = UiState()
    ui.set_runtime_state("PRESENT")
    ui.set_dialogue(reply="我看到画面左侧有一位来访者。")
    win = MainWindow(ui)
    out = tmp_path / "board_ui.png"
    win.render_to_file(str(out))
    assert out.is_file()
    image = QImage(str(out))
    assert (image.width(), image.height()) == (CANVAS_W, CANVAS_H)
