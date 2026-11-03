# -*- coding: utf-8 -*-
"""avatar_lod（入库 LOD 规格）与 tools.prepare_avatar_frames 的单测。

覆盖：目标尺寸等比缩放 / 抽帧索引 / 播放时长保持 / 体积预算 / meta 与 manifest 往返校验 /
工具端到端（源=帧目录，含 RGB565 导出与 --verify）。
"""
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from board.interaction import avatar_lod as lod
from scripts.prepare_avatar_frames import (parse_bg, parse_formats, rgba_to_rgb565)

SRC_W, SRC_H = 720, 1280      # 真实绿幕素材尺寸（Seedance 竖屏 9:16）
SRC_FPS = 24.06


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtGui import QGuiApplication
    return QGuiApplication.instance() or QGuiApplication([])


# --------------------------------------------------------------------------- #
# 1) 目标尺寸
# --------------------------------------------------------------------------- #
def test_target_size_portrait_9x16():
    assert lod.target_size(SRC_W, SRC_H, 384) == (216, 384)


def test_target_size_width_is_even():
    tw, _ = lod.target_size(721, 1280, 384)
    assert tw % 2 == 0


def test_target_size_never_upscales():
    assert lod.target_size(180, 320, 384) == (180, 320)


def test_target_size_limits_long_side():
    assert lod.target_size(1280, 720, 384) == (384, 216)   # 横屏按长边限制


def test_target_size_zero_means_keep():
    assert lod.target_size(SRC_W, SRC_H, 0) == (SRC_W, SRC_H)


def test_target_size_invalid_raises():
    with pytest.raises(ValueError):
        lod.target_size(0, 1280)


# --------------------------------------------------------------------------- #
# 2) 抽帧索引 + 输出帧率
# --------------------------------------------------------------------------- #
def test_select_indices_exact_half():
    assert lod.select_indices(240, 24.0, 12.0) == list(range(0, 240, 2))


def test_select_indices_keeps_head_and_spacing():
    idx = lod.select_indices(241, SRC_FPS, 12.0)
    assert idx[0] == 0
    assert all(b > a for a, b in zip(idx, idx[1:]))          # 升序去重
    assert {b - a for a, b in zip(idx, idx[1:])} <= {2, 3}   # 均匀（步长 24.06/12≈2.005）
    assert len(idx) >= 119                                   # ≈12fps × 10s


def test_select_indices_no_repeat_when_target_higher():
    assert lod.select_indices(5, 12.0, 24.0) == [0, 1, 2, 3, 4]


def test_select_indices_edges():
    assert lod.select_indices(0, SRC_FPS, 12.0) == []
    assert lod.select_indices(3, 0.0, 12.0) == [0, 1, 2]


def test_effective_fps_keeps_duration():
    kept = len(lod.select_indices(241, SRC_FPS, 12.0))
    fps = lod.effective_fps(SRC_FPS, 241, kept)
    assert 11.9 <= fps <= 12.3
    # 播放时长与原始一致（动作不变慢/变快）
    assert abs(kept / fps - 241 / SRC_FPS) < 0.05


def test_effective_fps_fallback():
    assert lod.effective_fps(0, 10, 10) == lod.DEFAULT_FPS
    assert lod.effective_fps(24, 0, 10) == lod.DEFAULT_FPS


# --------------------------------------------------------------------------- #
# 3) 体积预算
# --------------------------------------------------------------------------- #
def test_estimate_bytes_exact_rgb565():
    per = lod.estimate_bytes(24, (216, 384), ("png", "rgb565"))
    assert per["rgb565"] == 24 * 216 * 384 * 2
    assert per["png"] > 0


def test_budget_report_over_and_under():
    assert lod.budget_report(24, (216, 384), ("png",), 8.0)["over_budget"] is False
    # 未降采样的全量素材必然超预算（这正是本功能存在的理由）
    assert lod.budget_report(241, (SRC_W, SRC_H), ("png",), 8.0)["over_budget"] is True


def test_estimate_bytes_unknown_format():
    with pytest.raises(ValueError):
        lod.estimate_bytes(1, (2, 2), ("gif",))


def test_fit_to_budget_picks_highest_feasible():
    """180×320 全 PNG（≈86KB/帧）+ 8MiB 预算：12fps≈9.89、10fps≈8.24 均超 → 选 8fps。"""
    fit = lod.fit_to_budget(SRC_FPS, 241, (180, 320), ("png",), 8.0)
    assert fit["fits"] is True
    assert fit["fps"] == 8.0
    assert fit["report"]["total_mb"] <= 8.0


def test_fit_to_budget_never_upsamples():
    fit = lod.fit_to_budget(10.0, 100, (180, 320), ("png",), 8.0)
    assert fit["fps"] <= 10.0


def test_fit_to_budget_reports_when_impossible():
    """原分辨率全量素材：任何帧率都装不下 → fits=False 且取阶梯最低帧率。"""
    fit = lod.fit_to_budget(SRC_FPS, 241, (SRC_W, SRC_H), ("png",), 1.0)
    assert fit["fits"] is False
    assert fit["fps"] == lod.FPS_LADDER[-1]


# --------------------------------------------------------------------------- #
# 4) meta.json / manifest.json
# --------------------------------------------------------------------------- #
def test_build_meta_readable_by_avatar_assets(tmp_path):
    from board.interaction import avatar_assets as av

    d = tmp_path / "idle_normal"
    d.mkdir()
    meta = lod.build_meta("idle_normal", 12.08, (216, 384), 120,
                          spec={"max_side": 384}, source={"sha256": "abc"})
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False),
                                encoding="utf-8")
    assert av.frames_fps(d) == 12.08          # 渲染层按该帧率播放
    assert lod.read_manifest(d) is None


def test_manifest_roundtrip_then_tamper(tmp_path):
    frames = []
    for i in range(3):
        p = tmp_path / ("%06d.png" % i)
        p.write_bytes(b"\x89PNG" + bytes([i]))
        frames.append(p)
    entries = lod.manifest_entries(frames)
    (tmp_path / lod.MANIFEST_NAME).write_text(
        json.dumps(lod.build_manifest("idle_normal", entries)), encoding="utf-8")

    assert lod.verify_manifest(tmp_path, frames)["ok"] is True

    frames[1].write_bytes(b"tampered")        # 篡改一帧 → 必须报错
    result = lod.verify_manifest(tmp_path, frames)
    assert result["ok"] is False
    assert any("sha256" in s or "字节数" in s for s in result["issues"])


def test_verify_manifest_missing(tmp_path):
    result = lod.verify_manifest(tmp_path, [])
    assert result["ok"] is False and result["checked"] == 0


def test_verify_manifest_detects_extra_frame(tmp_path):
    p = tmp_path / "000000.png"
    p.write_bytes(b"a")
    (tmp_path / lod.MANIFEST_NAME).write_text(
        json.dumps(lod.build_manifest("x", lod.manifest_entries([p]))),
        encoding="utf-8")
    q = tmp_path / "000001.png"
    q.write_bytes(b"b")
    result = lod.verify_manifest(tmp_path, [p, q])
    assert result["ok"] is False
    assert any("帧数" in s or "缺少条目" in s for s in result["issues"])


# --------------------------------------------------------------------------- #
# 5) 工具层：参数解析 / RGB565 / 端到端
# --------------------------------------------------------------------------- #
def test_parse_formats_always_keeps_png():
    assert parse_formats("rgb565") == ("rgb565", "png")
    assert parse_formats("png,rgb565") == ("png", "rgb565")
    assert parse_formats("PNG") == ("png",)
    with pytest.raises(SystemExit):
        parse_formats("gif")


def test_parse_bg():
    assert parse_bg("#00FF00") == (0, 255, 0)
    assert parse_bg(None) is None
    with pytest.raises(SystemExit):
        parse_bg("fff")


def test_rgba_to_rgb565_big_endian_and_alpha():
    # 像素1 = 纯红不透明；像素2 = 全透明
    rgba = bytes([255, 0, 0, 255, 0, 0, 0, 0])
    out = rgba_to_rgb565(rgba, 2, 1, 8)
    assert len(out) == 4
    assert out[0:2] == bytes([0xF8, 0x00])        # 红 → 0xF800（大端）
    assert out[2:4] == bytes([0x00, 0x00])        # alpha<128 → 置黑
    out_bg = rgba_to_rgb565(rgba, 2, 1, 8, background=(0, 255, 0))
    assert out_bg[2:4] == bytes([0x07, 0xE0])     # 透明 + 绿底合成 → 0x07E0


def _write_src_frames(directory, count=6, size=(16, 32)):
    """造一批「已抠好的全分辨率帧」作为 --src（免依赖 cv2）。"""
    from PySide6.QtGui import QColor, QImage

    directory.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        img = QImage(size[0], size[1], QImage.Format_ARGB32)
        img.fill(QColor(10 * i, 255, 0, 255))
        assert img.save(str(directory / ("%06d.png" % i)), "PNG")
    return directory


def test_main_end_to_end_from_frame_dir(qapp, tmp_path, capsys):
    """全链路（源=帧目录）：抽帧 + 缩放 + meta/manifest + RGB565 + --verify。"""
    import scripts.prepare_avatar_frames as paf

    src = _write_src_frames(tmp_path / "raw")
    src_sha_before = lod.sha256_file(src / "000003.png")
    out_root = tmp_path / "assets"

    code = paf.main(["--src", str(src), "--name", "idle_normal",
                     "--out-root", str(out_root),
                     "--src-fps", "24", "--fps", "12",
                     "--max-side", "16", "--formats", "png,rgb565"])
    assert code == 0

    out_dir = out_root / "idle_normal"
    assert _frame_names(out_dir) == [
        "000000.png", "000001.png", "000002.png"]     # 6 帧 @24fps → 3 帧 @12fps

    meta = json.loads((out_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["fps"] == 12.0
    assert meta["size"] == [8, 16]                    # 长边 ≤16 → 8×16（宽取偶）
    assert meta["frames"] == 3
    assert meta["source"]["height"] == 32
    assert meta["spec"]["max_side"] == 16

    # 板端 RGB565 帧流：3 帧 × 8×16 × 2B
    assert (out_dir / "frames.rgb565").stat().st_size == 3 * 8 * 16 * 2

    # 校验清单 → 通过；篡改一帧 → 失败
    assert paf.main(["--verify", "--out-root", str(out_root)]) == 0
    (out_dir / "000001.png").write_bytes(b"tampered")
    assert paf.main(["--verify", "--out-root", str(out_root)]) == 1

    # 原始（源）素材只读：内容未被改动
    assert lod.sha256_file(src / "000003.png") == src_sha_before

    # 已入库素材默认跳过（不覆盖）
    assert paf.main(["--src", str(src), "--name", "idle_normal",
                     "--out-root", str(out_root)]) == 0
    assert "跳过" in capsys.readouterr().out


def _frame_names(directory):
    """目录内帧名（按名排序）；无则空表。"""
    return sorted(p.name for p in directory.glob("*.png"))


def _has_cv2():
    try:
        import cv2  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.skipif(not _has_cv2(), reason="需要 cv2 生成合成绿幕视频")
def test_dry_run_does_not_generate(qapp, tmp_path, capsys):
    import cv2
    import numpy as np

    import scripts.prepare_avatar_frames as paf

    src = tmp_path / "idle_normal.mp4"
    writer = cv2.VideoWriter(str(src), cv2.VideoWriter_fourcc(*"mp4v"),
                             24.0, (64, 96))
    try:
        for _ in range(12):
            writer.write(np.zeros((96, 64, 3), dtype=np.uint8))
    finally:
        writer.release()

    info = paf.probe_video(src)
    if not info or info["frames"] <= 0 or info["fps"] <= 0:
        pytest.skip("本机 cv2 无法写出可解码的合成视频")

    out_root = tmp_path / "assets"
    code = paf.main(["--src", str(src), "--state", "IDLE",
                     "--out-root", str(out_root), "--dry-run"])
    assert code == 0
    assert not (out_root / "idle_normal").exists()   # dry-run 不落盘
    out = capsys.readouterr().out
    assert "dry-run" in out and "idle_normal" in out


# --------------------------------------------------------------------------- #
# 6) 效果图生成器（Pillow 可选：缺失则跳过）
# --------------------------------------------------------------------------- #
def test_gallery_smoke_sheet(qapp, tmp_path):
    """帧带冒烟：能从入库素材生成 avatar_sheet_<素材名>.png。"""
    pytest.importorskip("PIL")
    import scripts.make_asset_gallery as gallery

    _write_src_frames(tmp_path / "assets" / "idle_normal", count=4, size=(16, 32))
    out_dir = tmp_path / "evidence"

    code = gallery.main(["--name", "idle_normal",
                         "--frames-root", str(tmp_path / "assets"),
                         "--out-dir", str(out_dir), "--no-gif",
                         "--no-quality", "--no-rgb565",
                         "--sheet-cols", "4"])
    assert code == 0
    sheet = out_dir / "avatar_sheet_idle_normal.png"
    assert sheet.is_file() and sheet.stat().st_size > 0


def test_rgb565_decode_roundtrip():
    """板端帧流自检用到的解码器：0xF800 → 纯红、0x07E0 → 纯绿。"""
    pytest.importorskip("PIL")
    import struct

    from scripts.make_asset_gallery import rgb565_decode

    blob = struct.pack(">HH", 0xF800, 0x07E0)
    image = rgb565_decode(blob, 2, 1)
    assert image.getpixel((0, 0)) == (255, 0, 0)
    assert image.getpixel((1, 0)) == (0, 255, 0)
