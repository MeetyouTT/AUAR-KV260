# -*- coding: utf-8 -*-
"""sheet_builder.py —— 拼图器（服务 `vision handoff`：把多帧合成为一张图，控制看图次数）。

用法：
  python.exe -s sheet_builder.py --spec <UTF-8 JSON>

spec 字段（全部为绝对路径）：
{
  "out": "<输出 PNG 路径>",
  "cell_w": 288,                 # 每格宽（px，等比重采样）
  "crop": [x0, y0, x1, y1],      # 可选；对每一帧先裁剪再缩放（用于看脸/局部）
  "rows": [                      # 每行 = 一组帧；行高按该行宽高比自动算
    {"dir": "<帧目录>", "frames": [0, 62, 123]}
  ],
  "order_note": "<可选，写进同名 .txt 的说明>"
}
输出：<out> 以及同名 .txt（记录每行每格对应的“目录 + 帧号”）。
"""
from __future__ import annotations

import argparse
import json
import os

from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--spec', required=True)
    a = ap.parse_args()
    with open(a.spec, 'r', encoding='utf-8') as f:
        s = json.load(f)

    cell_w = int(s.get('cell_w', 288))
    crop = s.get('crop')
    rows = s['rows']
    cells = []          # [(img, x, y)] 计算完成后统一 paste
    row_meta = []
    x0_pad = 0
    y_cursor = 0
    max_w = 0
    for r_i, row in enumerate(rows):
        d = row['dir']
        frames = row['frames']
        imgs = []
        for idx in frames:
            p = os.path.join(d, '%06d.png' % idx)
            im = Image.open(p).convert('RGB')
            if crop:
                im = im.crop(tuple(crop))
            h = max(1, int(round(im.height * cell_w / im.width)))
            imgs.append((im.resize((cell_w, h), Image.LANCZOS), idx, p))
        row_w = cell_w * len(imgs)
        row_h = max(i.height for i, _, _ in imgs)
        for c_i, (im, idx, p) in enumerate(imgs):
            cells.append((im, c_i * cell_w, y_cursor))
        row_meta.append((r_i, d, frames, row_h))
        max_w = max(max_w, row_w)
        y_cursor += row_h
        x0_pad = max(x0_pad, 0)

    canvas = Image.new('RGB', (max_w, y_cursor), (0, 0, 0))
    for im, x, y in cells:
        canvas.paste(im, (x, y))
    canvas.save(s['out'])

    txt = s['out'] + '.txt'
    with open(txt, 'w', encoding='utf-8') as f:
        note = s.get('order_note', '')
        if note:
            f.write(note + '\n')
        f.write('out=%s size=%dx%d cell_w=%d crop=%s\n' % (s['out'], canvas.width, canvas.height, cell_w, crop))
        for r_i, d, frames, row_h in row_meta:
            f.write('row %d | h=%d | %s | frames=%s\n' % (r_i, row_h, d, frames))
    print('SHEET_OK -> %s (%dx%d)' % (s['out'], canvas.width, canvas.height), flush=True)
    print('META -> %s' % txt, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
