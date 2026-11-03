# -*- coding: utf-8 -*-
"""scripts/ui_mock_draft（UI 设计草案渲染器）的单测。

覆盖：腰部以上裁切比例 / contain 等比缩放 / 安全边 / 三区尺寸自洽 /
玩偶区像素级验证（素材被画进框内 + 裁切确实切掉了下部）/ 板端草案 PNG 端到端落盘。
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter

from scripts import ui_mock_draft as mock

SRC_W, SRC_H = 720, 1280          # 真实绿幕素材尺寸（Seedance 竖屏 9:16）


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtGui import QGuiApplication
    return QGuiApplication.instance() or QGuiApplication([])


def _fake_matted() -> QImage:
    """合成一张"素材"：上部红带（腰部以上，应保留）、
    绿带正好落在裁切线（源 y=742）下方（= 腰部以下，裁切后应消失）。"""
    img = QImage(SRC_W, SRC_H, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.fillRect(QRect(0, 0, SRC_W, 200), QColor(255, 0, 0))
    p.fillRect(QRect(0, 760, SRC_W, 60), QColor(0, 255, 0))
    p.end()
    return img


def _has_color(img: QImage, name: str) -> bool:
    for y in range(0, img.height(), 3):
        for x in range(0, img.width(), 3):
            if img.pixelColor(x, y).name() == name:
                return True
    return False


def _board_box() -> QRect:
    """板端玩偶框（与 avatar_panel 内部推导一致）。"""
    prof = mock.PROFILES["board"]
    w, h = prof["w"] - prof["left"], prof["h"] - prof["bar"]
    iw, ih = w - 2 * prof["pad"], h - 2 * prof["pad"]
    return QRect(prof["pad"], prof["pad"] + prof["label_h"], iw, ih - prof["label_h"])


# --------------------------------------------------------------------------- #
# 1) 腰部以上裁切
# --------------------------------------------------------------------------- #
def test_crop_bottom_keeps_upper_58pct():
    out = mock.crop_bottom(_fake_matted(), 0.42)
    assert (out.width(), out.height()) == (720, 742)     # 1280 × 0.58 = 742.4


def test_crop_bottom_54pct_variant():
    assert mock.crop_bottom(_fake_matted(), 0.46).height() == 691


def test_crop_bottom_zero_ratio_keeps_full_height():
    assert mock.crop_bottom(_fake_matted(), 0.0).height() == SRC_H


# --------------------------------------------------------------------------- #
# 2) contain 等比缩放 + 安全边
# --------------------------------------------------------------------------- #
def test_contain_full_bleed_uses_panel_width():
    box = _board_box()
    img = mock.contain(mock.crop_bottom(_fake_matted()), box.width(), box.height())
    assert (img.width(), img.height()) == (423, 436)
    assert abs(img.width() / img.height() - 720 / 742) < 0.01


def test_contain_respects_safe_margin():
    box = _board_box()
    img = mock.contain(mock.crop_bottom(_fake_matted()),
                       box.width() - 2 * mock.SAFE_MARGIN, box.height())
    # Qt 等比缩放会取整：理论 407×419，实际可能少 1px
    assert img.height() == 419 and 406 <= img.width() <= 407
    assert img.width() <= box.width() - 2 * mock.SAFE_MARGIN


# --------------------------------------------------------------------------- #
# 3) 三区尺寸自洽（板端 1024×600 单档）
# --------------------------------------------------------------------------- #
def test_board_profile_three_zone_split():
    board = mock.PROFILES["board"]
    assert set(mock.PROFILES) == {"board"}        # PC 1280×720 档已废弃
    assert (board["w"] - board["left"], board["h"] - board["bar"]) == (439, 556)
    assert board["w"] == 1024 and board["h"] == 600 and board["left"] == 585


# --------------------------------------------------------------------------- #
# 4) 像素级：素材画进框内 + 裁切确实切掉下部
# --------------------------------------------------------------------------- #
def test_avatar_panel_draws_and_crops_waist_up(qapp):
    box = _board_box()
    img = QImage(439, 556, QImage.Format_ARGB32)
    img.fill(QColor(mock.C["bg"]))
    p = QPainter(img)
    mock.avatar_panel(p, mock.PROFILES["board"], 0, 0, 439, 556, _fake_matted())
    p.end()

    drawn = mock.contain(mock.crop_bottom(_fake_matted()), box.width(), box.height())
    top = box.y() + box.height() - drawn.height()          # 素材与框底对齐
    assert img.pixelColor(box.x() + box.width() // 2, top + 20).name() == "#ff0000"
    assert not _has_color(img, "#00ff00"), "裁切后腰部以下不应出现"


def test_avatar_panel_without_crop_shows_full_body(qapp):
    box = _board_box()
    img = QImage(439, 556, QImage.Format_ARGB32)
    img.fill(QColor(mock.C["bg"]))
    p = QPainter(img)
    mock.avatar_panel(p, mock.PROFILES["board"], 0, 0, 439, 556, _fake_matted(),
                      crop=False)
    p.end()
    # 不裁切：整张素材被压进框内 → 更窄但占满框高，腰部以下可见
    keep = mock.contain(mock.crop_bottom(_fake_matted()), box.width(), box.height())
    full = mock.contain(_fake_matted(), box.width(), box.height())
    assert full.width() < keep.width() and full.height() > keep.height()
    assert _has_color(img, "#00ff00"), "不裁切时应能看到腰部以下（膝上全身）"


# --------------------------------------------------------------------------- #
# 5) 端到端：板端草案 PNG 落盘
# --------------------------------------------------------------------------- #
def test_render_board_writes_1024x600_png(qapp, tmp_path):
    path = mock.render_board(mock.PROFILES["board"], _fake_matted(), tmp_path)
    assert path.name == "board_1024x600.png" and path.is_file()
    out = QImage(str(path))
    assert (out.width(), out.height()) == (1024, 600)
