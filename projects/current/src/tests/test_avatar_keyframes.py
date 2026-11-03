# -*- coding: utf-8 -*-
"""tools.avatar_keyframes 的单测：关键帧时刻换算 / 差异统计 / 判定阈值 / CLI 端到端。

覆盖「确保生成视频细节顺畅」的两条量化指标：首尾帧自循环、跨素材一致性。
"""
import os
import shutil

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

from scripts import avatar_keyframes as kf


# --------------------------------------------------------------------------- #
# 1) 时刻采样与帧号换算
# --------------------------------------------------------------------------- #
def test_sample_times_includes_ends():
    assert kf.sample_times(10.0, 5) == [0.0, 2.5, 5.0, 7.5, 10.0]


def test_sample_times_count_one_means_first_frame():
    assert kf.sample_times(10.0, 1) == [0.0]
    assert kf.sample_times(10.0, 0) == [0.0]


def test_sample_times_zero_duration():
    assert kf.sample_times(0.0, 3) == [0.0, 0.0, 0.0]


def test_frame_index_at_rounds_to_nearest():
    assert kf.frame_index_at(1.00, 24.0, 100) == 24
    assert kf.frame_index_at(1.02, 24.0, 100) == 24      # 24.48 → 24
    assert kf.frame_index_at(1.03, 24.0, 100) == 25      # 24.72 → 25


def test_frame_index_at_clamps_and_guards():
    assert kf.frame_index_at(100.0, 24.0, 100) == 99     # 末尾夹住（241 帧素材即 240）
    assert kf.frame_index_at(-5.0, 24.0, 100) == 0
    assert kf.frame_index_at(0.0, 0.0, 100) == 0         # fps 非法
    assert kf.frame_index_at(1.0, 24.0, 0) == 0          # 帧数非法


def test_frame_index_at_real_asset_9_98s():
    """实测素材：241 帧 @24.06fps，9.98s 应落在末帧 240。"""
    assert kf.frame_index_at(9.98, 24.06, 241) == 240


# --------------------------------------------------------------------------- #
# 2) 背景掩膜
# --------------------------------------------------------------------------- #
def test_background_mask_marks_green_as_background():
    img = np.zeros((4, 4, 3), dtype=np.uint8)
    img[..., 1] = 255                                   # 纯绿底
    img[1:3, 1:3] = (200, 30, 30)                       # 红块 = 前景
    mask = kf.background_mask(img)
    assert bool(mask[0, 0]) and not bool(mask[1, 1])


def test_background_mask_tolerates_aigc_green_shift():
    """AIGC 绿幕实测 [15,233,21]：与 00FF00 的距离应仍在容差内（判为背景）。"""
    img = np.zeros((2, 2, 3), dtype=np.uint8)
    img[...] = (15, 233, 21)
    assert bool(kf.background_mask(img, tol=60)[0, 0])


def test_background_mask_rejects_non_rgb():
    with pytest.raises(ValueError):
        kf.background_mask(np.zeros((4, 4), dtype=np.uint8))


def test_auto_bg_mask_prefers_alpha_for_rgba():
    img = np.zeros((4, 4, 4), dtype=np.uint8)
    img[1, 1, 3] = 255                                  # 只有 (1,1) 不透明
    mask = kf.auto_bg_mask(img)
    assert not bool(mask[1, 1]) and bool(mask[0, 0])


# --------------------------------------------------------------------------- #
# 3) 差异统计
# --------------------------------------------------------------------------- #
def test_diff_stats_identical_images_are_zero():
    img = np.full((8, 8, 3), 128, dtype=np.uint8)
    stats = kf.diff_stats(img, img)
    assert stats["mean"] == 0.0 and stats["max"] == 0.0 and stats["frac_gt"] == 0.0


def test_diff_stats_detects_local_change():
    a = np.zeros((10, 10, 3), dtype=np.uint8)
    b = a.copy()
    b[0, 0] = 255
    stats = kf.diff_stats(a, b)
    assert stats["max"] == 255.0
    assert stats["frac_gt"] == pytest.approx(0.01)


def test_diff_stats_ignores_transparent_area():
    """RGBA 素材：透明区的 RGB 噪声不该算进差异（否则循环判定会误报）。"""
    a = np.zeros((10, 10, 4), dtype=np.uint8)
    a[0:4, :, 3] = 255                                  # 上半不透明（主体）
    a[0:4, :, 0] = 100
    b = a.copy()
    b[4:, :, 0] = 200                                   # 下半（透明区）大幅不同
    stats = kf.diff_stats(a, b)
    assert stats["fg_ratio"] == pytest.approx(0.4)
    assert stats["fg_mean"] == 0.0
    assert stats["mean"] > 20.0                         # 全图指标仍会变大 → 故以主体为准


def test_diff_stats_uses_bg_mask_when_no_alpha():
    a = np.zeros((4, 4, 3), dtype=np.uint8)
    b = a.copy()
    b[0, 0] = 100                                       # 只改「背景」像素
    mask = np.zeros((4, 4), dtype=bool)
    mask[0, 0] = True
    stats = kf.diff_stats(a, b, bg_mask=mask)
    assert stats["fg_mean"] == 0.0 and stats["mean"] > 0.0


def test_diff_stats_shape_mismatch_raises():
    with pytest.raises(ValueError):
        kf.diff_stats(np.zeros((4, 4, 3), dtype=np.uint8),
                      np.zeros((5, 4, 3), dtype=np.uint8))


# --------------------------------------------------------------------------- #
# 4) 判定阈值
# --------------------------------------------------------------------------- #
def test_loop_verdict_three_levels():
    assert kf.loop_verdict({"fg_mean": 1.0, "fg_frac_gt": 0.01}) == "PASS"
    assert kf.loop_verdict({"fg_mean": 3.0, "fg_frac_gt": 0.03}) == "WARN"
    assert kf.loop_verdict({"fg_mean": 19.9, "fg_frac_gt": 0.47}) == "FAIL"


def test_ref_verdict_is_more_tolerant_than_loop():
    stats = {"fg_mean": 3.0, "fg_frac_gt": 0.03}
    assert kf.loop_verdict(stats) == "WARN"
    assert kf.ref_verdict(stats) == "PASS"


def test_verdict_falls_back_to_global_keys():
    assert kf.loop_verdict({"mean": 0.5, "frac_gt": 0.0}) == "PASS"


# --------------------------------------------------------------------------- #
# 5) 热力图与报告文本
# --------------------------------------------------------------------------- #
def test_heat_image_shape_and_gain():
    a = np.zeros((6, 6, 3), dtype=np.uint8)
    b = a.copy()
    b[2:4, 2:4] = 100
    heat = kf.heat_image(a, b, gain=2)
    assert heat.shape == (6, 6, 3)
    assert int(heat[2, 2, 0]) == 200
    assert int(heat[0, 0, 0]) == 0


def test_report_lines_are_three_lines_with_verdict():
    stats = {"mean": 1.0, "p99": 2.0, "max": 3.0, "frac_gt": 0.01,
             "fg_mean": 0.5, "fg_frac_gt": 0.0, "fg_ratio": 0.5}
    lines = kf.report_lines("t", stats, "PASS")
    assert len(lines) == 3 and lines[0].endswith("PASS")


def test_parse_hex_accepts_hash_and_bare():
    assert kf.parse_hex("#00FF00") == (0, 255, 0)
    assert kf.parse_hex("00B140") == (0, 177, 64)


def test_parse_hex_rejects_bad_input():
    with pytest.raises(SystemExit):
        kf.parse_hex("0F0")


# --------------------------------------------------------------------------- #
# 6) CLI 端到端（用「帧目录」当源，避免依赖真实 mp4）
# --------------------------------------------------------------------------- #
def _write_png(path, array):
    from PIL import Image

    Image.fromarray(array).save(str(path))


def _make_frames_dir(root, count=5, fg_step=10, size=(64, 64), same_ends=False):
    """造 count 帧绿幕帧序列：第 i 帧前景块 R 通道 = i*fg_step（same_ends → 首尾相同）。"""
    root.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        value = 0 if (same_ends and i in (0, count - 1)) else min(i * fg_step, 255)
        img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        img[..., 1] = 255
        img[20:40, 20:40] = (value, 10, 10)
        _write_png(root / ("%06d.png" % i), img)
    return root


def test_probe_source_on_frames_dir(tmp_path):
    src = _make_frames_dir(tmp_path / "frames")
    info = kf.probe_source(src, 10.0)
    assert info["kind"] == "frames"
    assert info["frames"] == 5 and info["fps"] == 10.0
    assert info["duration"] == pytest.approx(0.5)
    assert (info["width"], info["height"]) == (64, 64)


def test_cli_extracts_keyframes_and_fails_bad_loop(tmp_path):
    pytest.importorskip("PIL")
    src = _make_frames_dir(tmp_path / "frames", fg_step=30)
    out = tmp_path / "out"
    code = kf.main(["--src", str(src), "--out-dir", str(out), "--count", "5",
                    "--check-loop", "--src-fps", "10"])
    assert code == 1                                        # 首尾差 120 → FAIL
    names = sorted(p.name for p in out.glob("frames_t*.png"))
    assert names[0] == "frames_t00.00_f000000.png"          # 必含首帧
    assert len(names) >= 3                                  # 帧号去重后仍有多个关键帧
    assert (out / "frames_loop_check.png").is_file()


def test_cli_loop_passes_on_seamless_frames(tmp_path, capsys):
    pytest.importorskip("PIL")
    src = _make_frames_dir(tmp_path / "frames", fg_step=30, same_ends=True)
    out = tmp_path / "out"
    code = kf.main(["--src", str(src), "--out-dir", str(out), "--count", "5",
                    "--check-loop", "--src-fps", "10"])
    text = capsys.readouterr().out
    assert code == 0 and "PASS" in text


def test_cli_ref_check_uses_previous_keyframe(tmp_path, capsys):
    pytest.importorskip("PIL")
    src = _make_frames_dir(tmp_path / "frames", fg_step=40)
    out = tmp_path / "out"
    assert kf.main(["--src", str(src), "--out-dir", str(out), "--count", "1",
                    "--src-fps", "10"]) == 0
    ref = out / "frames_t00.00_f000000.png"
    assert ref.is_file()
    code = kf.main(["--src", str(src), "--out-dir", str(out), "--count", "3",
                    "--src-fps", "10", "--ref", str(ref)])
    text = capsys.readouterr().out
    assert code == 0 and "一致性核验" in text and "PASS" in text
    assert (out / "frames_ref_check.png").is_file()


def test_cli_find_loop_reports_latest_best_frame(tmp_path, capsys):
    pytest.importorskip("PIL")
    src = _make_frames_dir(tmp_path / "frames", fg_step=60, same_ends=True)
    out = tmp_path / "out"
    code = kf.main(["--src", str(src), "--out-dir", str(out), "--count", "1",
                    "--find-loop", "--src-fps", "10"])
    text = capsys.readouterr().out
    assert code == 0 and "vs f4" in text                    # 找的是最后一帧 f4（与首帧同）
    assert (out / "frames_loop_best_f000004.png").is_file()


# --------------------------------------------------------------------------- #
# 7) mp4 随机定位回归
#    Bug 记录：read_frame 读 mp4 时只对「末帧」做了 seek，中间帧完全没有 seek，
#    导致 --count>2 抽出的中间关键帧其实全是**首帧**（帧目录源不触发，故此前未暴露）。
# --------------------------------------------------------------------------- #
def _write_test_mp4(path, count=9, size=(48, 64), fps=9.0):
    """造一个「每帧前景颜色都不同」的绿幕 mp4；环境无编码器时返回 False。"""
    cv2 = pytest.importorskip("cv2")
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"),
                             float(fps), size)
    if not writer.isOpened():
        return False
    for i in range(count):
        img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        img[..., 1] = 255                                   # 绿幕
        img[10:30, 10:30] = (min(i * 25, 255), 10, 10)      # 每帧 R 不同
        writer.write(img)
    writer.release()
    return path.is_file() and path.stat().st_size > 0


def test_read_frame_seeks_to_middle_and_last(tmp_path):
    """回归：read_frame 必须真的 seek 到目标帧（不得把中间帧都读成首帧）。"""
    mp4 = tmp_path / "seq.mp4"
    if not _write_test_mp4(mp4):
        pytest.skip("当前环境无法写 mp4（缺编码器）")
    info = kf.probe_source(mp4, 9.0)
    assert info["kind"] == "video" and info["frames"] >= 5
    total = info["frames"]
    f0 = kf.read_frame(mp4, 0, info)
    mid = kf.read_frame(mp4, total // 2, info)
    last = kf.read_frame(mp4, total - 1, info)
    assert not np.array_equal(f0, mid)          # 中间帧 ≠ 首帧（本回归的核心）
    assert not np.array_equal(f0, last)         # 末帧 ≠ 首帧
    assert not np.array_equal(mid, last)


def test_cli_count_middle_keyframes_are_not_first_frame(tmp_path):
    """回归：--count=3 抽 mp4 时，三张关键帧必须互不相同（曾经全是首帧）。"""
    pytest.importorskip("PIL")
    mp4 = tmp_path / "seq.mp4"
    if not _write_test_mp4(mp4, count=11, fps=10.0):
        pytest.skip("当前环境无法写 mp4（缺编码器）")
    out = tmp_path / "out"
    assert kf.main(["--src", str(mp4), "--out-dir", str(out), "--count", "3"]) == 0
    pngs = sorted(out.glob("seq_t*.png"))
    assert len(pngs) == 3
    assert len({p.read_bytes() for p in pngs}) == 3         # 互不相同 = 真的抽到了中间帧


# --------------------------------------------------------------------------- #
# 7) Windows 非 ASCII 路径兼容（回归：cv2.imread 读不了中文路径 → --ref 误报）
# --------------------------------------------------------------------------- #
def test_imread_handles_non_ascii_path(tmp_path):
    """读图辅助函数必须能读中文路径（原 cv2.imread 返回 None）。"""
    pytest.importorskip("PIL")
    d = tmp_path / "中文目录"
    d.mkdir()
    p = d / "锚点图_测试.png"
    arr = np.zeros((8, 8, 3), dtype=np.uint8)
    arr[..., 1] = 255
    arr[2:4, 2:4] = (200, 10, 10)
    assert kf.save_rgb(p, arr) is True
    raw = kf._imread(p)
    assert raw is not None and raw.shape[:2] == (8, 8)
    assert int(raw[2, 2, 2]) == 200        # imdecode 走 BGR，第 3 通道即 R=200


def test_probe_source_on_non_ascii_frames_dir(tmp_path):
    """帧目录路径含中文时也要能探测（原实现直接 SystemExit）。"""
    pytest.importorskip("PIL")
    src = _make_frames_dir(tmp_path / "中文帧目录")
    info = kf.probe_source(src, 10.0)
    assert info["kind"] == "frames" and info["frames"] == 5
    assert (info["width"], info["height"]) == (64, 64)


def test_cli_ref_check_accepts_non_ascii_ref_path(tmp_path, capsys):
    """CLI 端到端：--ref 传中文路径参考图必须 PASS（不再误报读取失败）。"""
    pytest.importorskip("PIL")
    src = _make_frames_dir(tmp_path / "frames", fg_step=40)
    out = tmp_path / "out"
    assert kf.main(["--src", str(src), "--out-dir", str(out), "--count", "1",
                    "--src-fps", "10"]) == 0
    ref_dir = tmp_path / "锚点目录"
    ref_dir.mkdir()
    ref = ref_dir / "参考图.png"
    shutil.copyfile(str(out / "frames_t00.00_f000000.png"), str(ref))
    code = kf.main(["--src", str(src), "--out-dir", str(out), "--count", "3",
                    "--src-fps", "10", "--ref", str(ref)])
    text = capsys.readouterr().out
    assert code == 0
    assert "PASS" in text and "无法读取参考图" not in text


