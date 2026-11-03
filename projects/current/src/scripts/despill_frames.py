# -*- coding: utf-8 -*-
"""despill_frames —— 抠像帧序列的「强化去绿」后处理（A 硬限绿 + D1 蓝发去青）。

## 为什么要这一步（根因；实测数据见 docs/玩偶底图裁切_waistup58定稿口径_技术记录.md §9）

桌宠 `src.matting -m adaptive` 的兜底去绿权重是 `clip(s/0.15, 0, 1) * despill`，
其中 `s = 绿度 / 背景绿度` 是**线性斜坡** —— 绿度低的边缘像素只被削掉 30%~40%，
于是留下 `d = g - max(r,b)` ∈ [3,10] 的淡绿（waistup58 定稿帧实测 11,449 px，占内容 0.44%）；
又因为它把 `g` 压到 `max(r,b)`，对蓝发等价于 `g = b` → 蓝发改呈**青蓝**，
青染比 `q = (g - r) / (b - r)` 实测有 37.8% 的蓝发像素 q >= 0.35（肉眼即"发绿的蓝"）。

## 两步（默认都开；可分别用 --no-limit-green / --no-decyan 关掉）

- **A 硬限绿**：`g = min(g, max(r, b))` —— 只压绿、**不减面积、不改 alpha**；
- **D1 蓝发去青**：对蓝发像素（`q >= q-min`）把绿压到 q 上限：
  `g = min(g, r + q-max * (b - r))`，默认 `q-min=0.35 / q-max=0.50`（最小改动档）。

实测（waistup58 定稿帧 2136x2202）：A 把 `d>=3` 从 11,449 → **0 px**、不透明像素数一字不变；
A+D1 改动 228,166 px（占内容 8.79%）、平均降绿 21.6，蓝发保留率 98.18% 不变、`(b-r)` 均值不变。

## 用法

    python scripts/despill_frames.py --dir <抠像帧目录>             # 就地处理（默认 A+D1）
    python scripts/despill_frames.py --image a.png --out b.png
    python scripts/despill_frames.py --dir <目录> --check           # 只量不改
"""
from __future__ import annotations

import argparse
import sys
import typing
from pathlib import Path

import numpy as np

try:
    import cv2
except ImportError:  # pragma: no cover - 抠像链已强依赖 cv2，这里只做友好提示
    raise SystemExit("despill_frames 需要 opencv-python（与 src.matting 同一依赖）")

__all__ = ["hard_limit_green", "decyan_blue", "trim_alpha_ring", "despill_bgra",
           "analyze", "despill_file", "despill_dir"]


def _channels(bgra: np.ndarray) -> typing.Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """BGRA → (B, G, R) int16。"""
    if bgra.ndim != 3 or bgra.shape[2] < 3:
        raise ValueError("期望 BGRA 图像，收到 shape=%r" % (bgra.shape,))
    return (bgra[..., 0].astype(np.int16), bgra[..., 1].astype(np.int16),
            bgra[..., 2].astype(np.int16))


def hard_limit_green(bgra: np.ndarray) -> np.ndarray:
    """A 档：`g = min(g, max(r, b))`（只降不升；透明像素跳过）。"""
    out = bgra.copy()
    b, g, r = _channels(out)
    cap = np.maximum(b, r)
    newg = np.where((g > cap) & (out[..., 3] > 0), cap, g)
    out[..., 1] = np.clip(newg, 0, 255).astype(np.uint8)
    return out


def decyan_blue(bgra: np.ndarray, q_min: float = 0.35,
                q_max: float = 0.50) -> typing.Tuple[np.ndarray, int]:
    """D1 档：蓝发去青 —— 把青染比 q 压到 q_max（返回 (图, 命中像素数)）。

    蓝发判据 `b - r > 30 且 b > 80`；只作用于 `alpha >= 8` 且 `q >= q_min` 的像素。
    """
    out = bgra.copy()
    b, g, r = _channels(out)
    bl = (b - r).astype(np.float32)
    blue = (bl > 30) & (b > 80)
    q = (g.astype(np.float32) - r) / np.maximum(bl, 1.0)
    hit = blue & (out[..., 3] >= 8) & (q >= float(q_min))
    newg = np.minimum(g.astype(np.float32), r + float(q_max) * np.maximum(bl, 0.0))
    out[..., 1] = np.where(hit, np.clip(newg, 0, 255), g).astype(np.uint8)
    return out, int(hit.sum())


def trim_alpha_ring(bgra: np.ndarray, keep_below: int = 128) -> np.ndarray:
    """可选 C2 档：去掉最外 1px 圈里 `alpha < keep_below` 的淡晕（默认不启用）。"""
    out = bgra.copy()
    content = (out[..., 3] >= 8).astype(np.uint8)
    er = cv2.erode(content, np.ones((3, 3), np.uint8))
    ring = (content > 0) & (er == 0) & (out[..., 3] < int(keep_below))
    out[ring, 3] = 0
    return out


def despill_bgra(bgra: np.ndarray, limit_green: bool = True, decyan: bool = True,
                 q_min: float = 0.35, q_max: float = 0.50,
                 trim_edge: str = "off") -> np.ndarray:
    """单帧入口：抠像 BGRA → 强化去绿后的 BGRA（供 prepare_avatar_frames 复用）。"""
    out = bgra
    if limit_green:
        out = hard_limit_green(out)
    if decyan:
        out, _ = decyan_blue(out, q_min=q_min, q_max=q_max)
    if trim_edge == "soft":
        out = trim_alpha_ring(out)
    return out


def analyze(bgra: np.ndarray) -> typing.Dict[str, int]:
    """量化指标：绿残留 d>=3/>=6、青染蓝发 q>=0.35/>=0.6、内容与不透明像素数。"""
    b, g, r = _channels(bgra)
    a = bgra[..., 3]
    d = g - np.maximum(b, r)
    bl = (b - r).astype(np.float32)
    blue = (bl > 30) & (b > 80)
    q = (g.astype(np.float32) - r) / np.maximum(bl, 1.0)
    tgt = blue & (a >= 8)
    return {"content_px": int((a >= 8).sum()), "opaque_px": int((a > 200).sum()),
            "d_ge3": int(((a >= 8) & (d >= 3)).sum()), "d_ge6": int(((a >= 8) & (d >= 6)).sum()),
            "blue_px": int(tgt.sum()), "blue_q35": int((tgt & (q >= 0.35)).sum()),
            "blue_q60": int((tgt & (q >= 0.6)).sum())}


def _read(path: Path) -> np.ndarray:
    """读 PNG（**非 ASCII 路径安全**：走 imdecode + fromfile）。"""
    img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise SystemExit("无法读取: %s" % path)
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
    if img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    return img


def _write(path: Path, img: np.ndarray) -> None:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise SystemExit("PNG 写出失败: %s" % path)
    buf.tofile(str(path))


def despill_file(path: Path, out: typing.Optional[Path] = None, **kw) -> typing.Dict[str, int]:
    """处理单帧；`out` 为空则就地覆盖。返回处理后指标。"""
    src = _read(path)
    dst = despill_bgra(src, **kw)
    _write(Path(out) if out else path, dst)
    return analyze(dst)


def despill_dir(root: Path, pattern: str = "*.png", limit_green: bool = True, decyan: bool = True,
                q_min: float = 0.35, q_max: float = 0.50, trim_edge: str = "off",
                progress: typing.Optional[typing.Callable[[str], None]] = None) -> int:
    """就地处理目录内帧（默认 A+D1）。返回处理帧数。"""
    files = sorted(Path(root).glob(pattern))
    for i, p in enumerate(files, 1):
        despill_file(p, limit_green=limit_green, decyan=decyan,
                     q_min=q_min, q_max=q_max, trim_edge=trim_edge)
        if progress and (i % 10 == 0 or i == len(files)):
            progress("  去绿 %d/%d %s" % (i, len(files), p.name))
    return len(files)


def main(argv: typing.Optional[typing.List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="抠像帧强化去绿（A 硬限绿 + D1 蓝发去青）")
    ap.add_argument("--dir", help="帧目录（就地处理）")
    ap.add_argument("--image", help="单帧输入")
    ap.add_argument("--out", help="单帧输出（默认就地）")
    ap.add_argument("--pattern", default="*.png", help="目录内匹配（默认 *.png）")
    ap.add_argument("--check", action="store_true", help="只量不改")
    ap.add_argument("--no-limit-green", action="store_true", help="关掉 A 硬限绿")
    ap.add_argument("--no-decyan", action="store_true", help="关掉 D1 蓝发去青")
    ap.add_argument("--q-min", type=float, default=0.35, help="D1 触发阈值（默认 0.35）")
    ap.add_argument("--q-max", type=float, default=0.50, help="D1 青染比上限（默认 0.50）")
    ap.add_argument("--trim-edge", choices=("off", "soft"), default="off",
                    help="soft=再去掉最外 1px 圈的淡晕（默认 off）")
    args = ap.parse_args(argv)
    kw = dict(limit_green=not args.no_limit_green, decyan=not args.no_decyan,
              q_min=args.q_min, q_max=args.q_max, trim_edge=args.trim_edge)
    keys = ("d_ge3", "d_ge6", "blue_q35", "blue_q60", "content_px", "opaque_px")

    if args.image:
        img = _read(Path(args.image))
        before = analyze(img)
        dst = despill_bgra(img, **kw)
        if not args.check:
            _write(Path(args.out) if args.out else Path(args.image), dst)
        after = analyze(dst)
        print("  [%s] %s" % ("check" if args.check else "write", args.image))
        for k in keys:
            print("    %-11s %8d -> %8d" % (k, before[k], after[k]))
        return 0

    if args.dir:
        files = sorted(Path(args.dir).glob(args.pattern))
        if not files:
            raise SystemExit("目录内没有匹配帧: %s %s" % (args.dir, args.pattern))
        if args.check:
            agg = {k: 0 for k in keys[:4]}
            for p in files:
                m = analyze(_read(p))
                for k in agg:
                    agg[k] += m[k]
            print("  [check] %d 帧合计: %s" % (len(files), agg))
            return 0
        n = despill_dir(args.dir, pattern=args.pattern, progress=print, **kw)
        print("  [去绿] 就地处理 %d 帧 → %s" % (n, args.dir))
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
