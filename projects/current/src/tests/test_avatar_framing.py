# -*- coding: utf-8 -*-
"""取景（framing）与入库裁切单测：avatar_lod.crop_box / parse_framing + 工具端到端。

覆盖：预设比例冻结值、非法输入、**只裁纵向**、腰部以上 + 480 档 = 466×480、
      以及 scripts/prepare_avatar_frames.py `--framing waist-up` 端到端
      （真实写出 PNG + meta.json 记录 framing / crop_bottom_ratio）。
"""
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from board.interaction import avatar_lod as lod

SRC_W, SRC_H = 720, 1280        # 真实 Seedance 竖屏素材尺寸


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtGui import QGuiApplication
    return QGuiApplication.instance() or QGuiApplication([])


# --------------------------------------------------------------------------- #
# 1) 取景预设与比例解析
# --------------------------------------------------------------------------- #
def test_framing_presets_frozen_values():
    assert lod.FRAMING_PRESETS == {"full": 0.0, "waist-up": 0.42}


def test_parse_framing_uses_preset():
    assert lod.parse_framing("waist-up") == 0.42
    assert lod.parse_framing("full") == 0.0
    assert lod.parse_framing("") == 0.0                # 空 → full


def test_parse_framing_explicit_ratio_wins():
    assert lod.parse_framing("waist-up", 0.46) == 0.46


def test_parse_framing_rejects_unknown_and_out_of_range():
    with pytest.raises(ValueError):
        lod.parse_framing("waist")                     # 未知取景不静默按 full
    with pytest.raises(ValueError):
        lod.parse_framing("full", 1.0)
    with pytest.raises(ValueError):
        lod.parse_framing("full", -0.1)


# --------------------------------------------------------------------------- #
# 2) 裁切矩形：只裁纵向、原点/宽度不变
# --------------------------------------------------------------------------- #
def test_crop_box_waist_up_on_real_size():
    """720×1280 裁掉下部 42% → 720×742（与草案渲染器 crop_bottom 完全一致）。"""
    assert lod.crop_box(SRC_W, SRC_H, lod.FRAMING_PRESETS["waist-up"]) == (0, 0, 720, 742)


def test_crop_box_is_vertical_only():
    x, y, w, h = lod.crop_box(SRC_W, SRC_H, 0.46)
    assert (x, y, w) == (0, 0, SRC_W) and h == 691     # 1280 × 0.54 = 691.2 → 691


def test_crop_box_zero_ratio_keeps_size():
    assert lod.crop_box(SRC_W, SRC_H, 0.0) == (0, 0, SRC_W, SRC_H)


def test_crop_box_rejects_bad_input():
    with pytest.raises(ValueError):
        lod.crop_box(0, SRC_H, 0.42)
    with pytest.raises(ValueError):
        lod.crop_box(SRC_W, SRC_H, 1.5)


def test_waist_up_480_grade_is_466x480():
    """腰部以上 + 480 档 = 466×480 → 框内 423×436（草案实测值）。"""
    _, _, w, h = lod.crop_box(SRC_W, SRC_H, lod.FRAMING_PRESETS["waist-up"])
    assert lod.target_size(w, h, 480) == (466, 480)
    # 未裁切时同一 480 档只有 270×480（人物明显更小）
    assert lod.target_size(SRC_W, SRC_H, 480) == (270, 480)


# --------------------------------------------------------------------------- #
# 3) 工具端到端：--framing waist-up 真实写出帧 + meta.json
# --------------------------------------------------------------------------- #
def _write_frames(directory, count=2, size=(120, 240)) -> None:
    """合成素材帧：上部红带（腰部以上，须保留）、最下 20 行绿带（须被裁掉）。"""
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QColor, QImage, QPainter

    directory.mkdir(parents=True, exist_ok=True)
    w, h = size
    for i in range(count):
        image = QImage(w, h, QImage.Format_ARGB32)
        image.fill(QColor(0, 0, 0, 0))
        p = QPainter(image)
        p.fillRect(QRect(0, 0, w, 100), QColor(255, 0, 0))
        p.fillRect(QRect(0, h - 20, w, 20), QColor(0, 255, 0))
        p.end()
        image.save(str(directory / ("%06d.png" % i)), "PNG")


def _has_color(image, name: str) -> bool:
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).name() == name:
                return True
    return False


def _run_prepare(tmp_path, framing: str) -> "tuple":  # noqa: F821 - 返回 (QImage, meta)
    from PySide6.QtGui import QImage
    from scripts import prepare_avatar_frames as prep

    src = tmp_path / ("src_" + framing) / "idle_normal"
    _write_frames(src)
    root = tmp_path / ("out_" + framing)
    rc = prep.main(["--src", str(src), "--name", "idle_normal",
                    "--out-root", str(root), "--framing", framing,
                    "--max-side", "60", "--fps", "10", "--src-fps", "10",
                    "--force"])
    assert rc == 0
    out = root / "idle_normal"
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    first = sorted(out.glob("*.png"))[0]
    return QImage(str(first)), meta


def test_prepare_waist_up_crops_and_records_framing(qapp, tmp_path):
    image, meta = _run_prepare(tmp_path, "waist-up")
    # 120×240 裁掉下部 42% → 120×139 → 长边 60 档 → 52×60（偶数规整）
    assert (image.width(), image.height()) == (52, 60)
    assert _has_color(image, "#ff0000"), "上半身应保留"
    assert not _has_color(image, "#00ff00"), "腰部以下应被裁掉"
    assert meta["spec"]["framing"] == "waist-up"
    assert abs(float(meta["spec"]["crop_bottom_ratio"]) - 0.42) < 1e-9
    assert meta["size"] == [52, 60]


def test_prepare_full_keeps_lower_body(qapp, tmp_path):
    image, meta = _run_prepare(tmp_path, "full")
    # 不裁切：120×240 → 长边 60 档 → 30×60（腰/膝以下仍在）
    assert (image.width(), image.height()) == (30, 60)
    assert _has_color(image, "#00ff00"), "不裁切时应能看到下部（绿带）"
    assert meta["spec"]["framing"] == "full"
    assert float(meta["spec"]["crop_bottom_ratio"]) == 0.0


def test_status_board_reports_progress(qapp, tmp_path, capsys):
    """--status 进度看板：已入库素材显示帧数/尺寸/取景，缺的显式标注。"""
    from scripts import prepare_avatar_frames as prep

    src = tmp_path / "src_status" / "idle_normal"
    _write_frames(src)
    root = tmp_path / "out_status"
    assert prep.main(["--src", str(src), "--name", "idle_normal",
                      "--out-root", str(root), "--framing", "waist-up",
                      "--max-side", "60", "--fps", "10", "--src-fps", "10",
                      "--force"]) == 0
    capsys.readouterr()                       # 丢掉生成期输出

    rc = prep.main(["--status", "--out-root", str(root)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "idle_normal" in out and "waist-up" in out and "52x60" in out
    assert "[缺失] 待产出" in out              # 其余 7 态尚未产出
    assert "待产出状态：" in out


def test_status_marks_wrong_framing(qapp, tmp_path, capsys):
    """取景仍是 full 时看板要提醒（避免"帧齐了但口径不对"）。"""
    from scripts import prepare_avatar_frames as prep

    src = tmp_path / "src_fullstatus" / "idle_normal"
    _write_frames(src)
    root = tmp_path / "out_fullstatus"
    assert prep.main(["--src", str(src), "--name", "idle_normal",
                      "--out-root", str(root), "--framing", "full",
                      "--max-side", "60", "--fps", "10", "--src-fps", "10",
                      "--force"]) == 0
    capsys.readouterr()
    prep.main(["--status", "--out-root", str(root)])
    out = capsys.readouterr().out
    assert "≠ 板端 waist-up" in out


def test_prepare_crop_bottom_ratio_overrides_framing(qapp, tmp_path):
    from scripts import prepare_avatar_frames as prep
    src = tmp_path / "src_custom" / "idle_normal"
    _write_frames(src)
    root = tmp_path / "out_custom"
    rc = prep.main(["--src", str(src), "--name", "idle_normal",
                    "--out-root", str(root), "--framing", "full",
                    "--crop-bottom-ratio", "0.5", "--max-side", "60",
                    "--fps", "10", "--src-fps", "10", "--force"])
    assert rc == 0
    meta = json.loads((root / "idle_normal" / "meta.json").read_text(encoding="utf-8"))
    assert abs(float(meta["spec"]["crop_bottom_ratio"]) - 0.5) < 1e-9
