#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""眼区逐帧接触表（只读）：把若干资产的眼区按帧拼成一张图，用于一次目测判"何时闭眼"。

用法: python zz_eye_sheet.py --batch-root <...\\batch_001> --items blink_v3_s421001 rest_v3_s421001
                               --out <sheet.png>
输出: 单张 PNG（1:1 像素，不缩放、不写入资产目录）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

X0, Y0, X1, Y1 = 0.40, 0.115, 0.60, 0.185   # 眼区（含 1.4x 余量），由 f16 目测标定
COLS = 13
SCALE = 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="eye band contact sheet (read-only)")
    ap.add_argument("--batch-root", required=True)
    ap.add_argument("--items", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    raw = Path(args.batch_root) / "raw"
    panels = []
    for name in args.items:
        d = raw / name
        pngs = sorted(d.glob("*.png"))
        if not pngs:
            print("FAIL no png: %s" % d)
            return 2
        ref = Image.open(pngs[0])
        w, h = ref.size
        ref.close()
        box = (int(X0 * w), int(Y0 * h), int(X1 * w), int(Y1 * h))
        cw, ch = (box[2] - box[0]) * SCALE, (box[3] - box[1]) * SCALE
        rows = (len(pngs) + COLS - 1) // COLS
        sheet = Image.new("RGB", (cw * COLS, ch * rows + 14), (0, 0, 0))
        dr = ImageDraw.Draw(sheet)
        dr.text((2, 2), "%s  f=0..%d  cols=%d" % (name, len(pngs) - 1, COLS), fill=(255, 255, 0))
        for i, p in enumerate(pngs):
            with Image.open(p) as im:
                cell = im.convert("RGB").crop(box).resize((cw, ch), Image.NEAREST)
            x, y = (i % COLS) * cw, 14 + (i // COLS) * ch
            sheet.paste(cell, (x, y))
            dr.text((x + 3, y + 2), str(i), fill=(255, 0, 0))
        panels.append(sheet)
    W = max(p.size[0] for p in panels)
    H = sum(p.size[1] + 4 for p in panels)
    out = Image.new("RGB", (W, H), (0, 0, 0))
    y = 0
    for p in panels:
        out.paste(p, (0, y))
        y += p.size[1] + 4
    out.save(args.out)
    print("SAVED %s  size=%sx%s" % (args.out, out.size[0], out.size[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
