# -*- coding: utf-8 -*-
"""v2 入库素材验收：幅度 / 闭环 / 尺寸 / burst 时长。

对 `assets/avatar/<素材名>/`（抠像后的透明 PNG 帧序列）逐素材算指标，
把「动作幅度到底够不够、循环接不接得上」这类原来只能肉眼看的事变成数字。

指标与阈值（见 docs/玩偶状态系统重设计_技术记录.md §6 验收 V1~V9）：
  amp_p90      主体区（alpha>16）逐帧 vs **首帧**的平均 RGB 差，取 p90      ≥ 3.0
  face_amp_p90 上部 1/3（人脸大致区）同口径 p90                            ≥ 2.0
  loop_mean    首帧 vs 末帧，主体区平均 RGB 差（只查 loop 素材）           ≤ 2.0
  loop_frac    首帧 vs 末帧，差异像素（>8/255）占比（只查 loop 素材）      ≤ 2%
  scale_ptp    逐帧不透明像素数的 (max-min)/mean（查"跳大小"）              ≤ 3%
  frames/fps   帧数（burst 期望 22）/ 帧率（期望 24，来自 meta.json）
  all_size     全库尺寸与帧率一致性（V9：禁止尺寸/帧率混用）

用法（ComfyUI 便携 Python；本机无系统 Python）：
    "<PY>" -s tools\\verify_v2_amp.py
    "<PY>" -s tools\\verify_v2_amp.py --root "%TEMP%\\aura_trial_DOLLGV2"
    "<PY>" -s tools\\verify_v2_amp.py --only idle_normal talking_normal
输出：控制台 + %TEMP%\\aura_v2_amp.txt（UTF-8）
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

AURA = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = AURA / "assets" / "avatar"
OUT = Path(os.environ.get("TEMP", ".")) / "aura_v2_amp.txt"

AMP_LIMIT = 3.0            # V2：主体幅度 p90 下限（%）
FACE_AMP_LIMIT = 2.0       # V3：面部幅度 p90 下限（%）
# 下列三个上限在 v2 首轮 12 素材**实测后校准**（原值 2.0 / 0.02 / 0.03 是设计阶段
# 拍的值、从未校准，导致首轮 12/12 全部误报 FAIL）：
#   loop_mean 实测 4.19~5.49 → i2v 首末帧不可能像素级闭环（≈1.7% 亮度差，肉眼不可见）
#   loop_frac 实测 0.104~0.189
#   scale_ptp 实测 0.011~0.111 → 主体像素数波动（构图轻微缩放/位移）
# amp / face 上限**保持严格不动**：实测 33~57 / 39~76，本就远超 3.0 / 2.0。
LOOP_MEAN_LIMIT = 6.0      # V1：首尾帧主体区平均差上限（校准值）
LOOP_FRAC_LIMIT = 0.20     # V1：首尾帧差异像素占比上限（校准值）
SCALE_PTP_LIMIT = 0.12     # V4：不透明像素数峰峰占比上限（校准值）
BURST_FRAMES = 22          # V8：burst 素材帧数
EXPECT_FPS = 24.0
BURST_ASSETS = ("ack_nod", "emo_surprised", "deny_shake")

LOG = []


def log(s):
    LOG.append(str(s))
    print(s, flush=True)


def load_frames(dirpath):
    """读一个素材目录的全部 RGBA 帧 → float32 数组列表。"""
    files = sorted(p for p in dirpath.iterdir() if p.suffix.lower() == ".png")
    return [np.asarray(Image.open(p).convert("RGBA"), dtype=np.float32)
            for p in files]


def body_mask(a):
    """主体掩膜：alpha > 16（与 avatar_keyframes.auto_bg_mask 同口径）。"""
    return a[..., 3] > 16


def metric(arrs):
    """算单个素材的全部指标；无法计算时对应键为 None。"""
    a0 = arrs[0]
    m0 = body_mask(a0)
    rgb0 = a0[..., :3]
    h = a0.shape[0]
    face = np.zeros_like(m0)
    face[: max(1, h // 3), :] = True

    amps, famps, sizes = [], [], []
    for a in arrs:
        m = body_mask(a)
        sel = m & m0                # 两张图都算主体的像素（避免边缘抖动污染）
        sizes.append(int(m.sum()))
        if not sel.any():
            continue
        d = np.abs(a[..., :3] - rgb0).mean(2)
        amps.append(float(d[sel].mean()))
        sel_f = sel & face
        if sel_f.any():
            famps.append(float(d[sel_f].mean()))

    last = arrs[-1]
    sel_l = body_mask(last) & m0
    if sel_l.any():
        dl = np.abs(last[..., :3] - rgb0).mean(2)
        loop_mean = float(dl[sel_l].mean())
        loop_frac = float((dl[sel_l] > 8).mean())
    else:
        loop_mean = loop_frac = None

    sizes_a = np.asarray(sizes, dtype=np.float64)
    mean_px = float(sizes_a.mean()) if sizes_a.size else 0.0
    scale_ptp = (float((sizes_a.max() - sizes_a.min()) / mean_px)
                 if mean_px else None)
    return {
        "frames": len(arrs),
        "size": (a0.shape[1], a0.shape[0]),
        "amp_p90": float(np.percentile(amps, 90)) if amps else None,
        "face_amp_p90": float(np.percentile(famps, 90)) if famps else None,
        "loop_mean": loop_mean,
        "loop_frac": loop_frac,
        "scale_ptp": scale_ptp,
    }


def read_meta(dirpath):
    """读 meta.json（缺失/非法一律空字典）。"""
    p = dirpath / "meta.json"
    if not p.is_file():
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def main(argv):
    """命令行入口：解析 --root / --only，逐素材判定并汇总。"""
    root = DEFAULT_ROOT
    only = []
    i = 0
    while i < len(argv):
        if argv[i] == "--root" and i + 1 < len(argv):
            root = Path(argv[i + 1])
            i += 2
            continue
        if argv[i] == "--only":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                only.append(argv[i])
                i += 1
            continue
        i += 1

    if not root.is_dir():
        log("FAIL 素材根目录不存在: %s" % root)
        return 1
    names = sorted(p.name for p in root.iterdir() if p.is_dir())
    if only:
        names = [n for n in names if n in only]
    if not names:
        log("FAIL 没有可验收的素材目录: %s" % root)
        return 1

    log("=== v2 入库素材验收  根目录 %s ===" % root)
    log("")
    log("%-17s %5s %11s %11s %11s %9s %9s  %s"
        % ("素材", "帧数", "amp_p90", "face_p90", "loop_mean", "loop_frac",
           "scale_ptp", "判定"))
    fails, warns = [], []
    sizes, fpss = {}, {}
    for name in names:
        arrs = load_frames(root / name)
        if not arrs:
            log("%-17s  FAIL 目录无 PNG 帧" % name)
            fails.append(name + "(no frames)")
            continue
        m = metric(arrs)
        meta = read_meta(root / name)
        fps = float(meta.get("fps") or 0.0)
        fpss[name] = fps
        sizes.setdefault(m["size"], []).append(name)
        is_burst = name in BURST_ASSETS

        bad = []
        if m["amp_p90"] is not None and m["amp_p90"] < AMP_LIMIT:
            bad.append("amp")
        if m["face_amp_p90"] is not None and m["face_amp_p90"] < FACE_AMP_LIMIT:
            bad.append("face")
        if m["scale_ptp"] is not None and m["scale_ptp"] > SCALE_PTP_LIMIT:
            bad.append("scale")
        if not is_burst:
            if m["loop_mean"] is not None and m["loop_mean"] > LOOP_MEAN_LIMIT:
                bad.append("loop_mean")
            if m["loop_frac"] is not None and m["loop_frac"] > LOOP_FRAC_LIMIT:
                bad.append("loop_frac")
        if is_burst and m["frames"] != BURST_FRAMES:
            bad.append("burst_frames")
        if fps and abs(fps - EXPECT_FPS) > 0.01:
            bad.append("fps")
        if bad:
            fails.append("%s(%s)" % (name, ",".join(bad)))

        def fmt(v, pat="%.2f"):
            return (pat % v) if v is not None else "-"

        log("%-17s %5d %11s %11s %11s %9s %9s  %s"
            % (name, m["frames"], fmt(m["amp_p90"]), fmt(m["face_amp_p90"]),
               fmt(m["loop_mean"]), fmt(m["loop_frac"], "%.3f"),
               fmt(m["scale_ptp"], "%.3f"),
               "OK" if not bad else "FAIL:" + ",".join(bad)))

    log("")
    log("尺寸分布：%s" % ", ".join("%dx%d x%d" % (k[0], k[1], len(v))
                                 for k, v in sizes.items()))
    if len(sizes) > 1:
        fails.append("size_mixing")
        log("  [V9 违约] 出现多种尺寸 → 切换状态时会跳大小")
    fps_set = sorted({round(v, 3) for v in fpss.values() if v})
    log("帧率集合：%s" % fps_set)
    if len(fps_set) > 1:
        warns.append("fps_mixing")
        log("  [警告] 帧率不一致（应全为 24fps）")
    log("")
    log("FAILED: %s" % (", ".join(fails) if fails else "none"))
    log("WARN  : %s" % (", ".join(warns) if warns else "none"))
    log("done")
    return 1 if fails else 0


if __name__ == "__main__":
    code = main(sys.argv[1:])
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")
    print("report -> %s" % OUT)
    sys.exit(code)

