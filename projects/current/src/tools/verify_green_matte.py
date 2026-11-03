# -*- coding: utf-8 -*-
"""逐帧**真口径**核对：用该帧自身四角估计背景色（生成帧的绿幕会漂移，
硬编码 GREEN=(13,247,34) 会把漂移后的背景误判成前景 —— 必须先自适应估计）。

指标（每帧）：
  bg_kept  = 源帧是背景、却被保留 alpha>128  → **背景误留**（应≈0）
  fg_drop  = 源帧是人物、却被抠掉 alpha<=128 → **人物误抠**（应小）
  d>=3 / blue q>=0.6（保留像素上的绿残留与青染，口径同 despill.analyze）
用法: python aura_verify2.py <绿幕帧目录> <抠后帧目录> [输出目录]
"""
import io
import os
import sys

import cv2
import numpy as np

EXTS = ('.png', '.jpg', '.jpeg', '.bmp')


def rd(p):
    return cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_UNCHANGED)


def frames(d):
    return [os.path.join(d, f) for f in sorted(os.listdir(d))
            if os.path.splitext(f)[1].lower() in EXTS]


sd, md = sys.argv[1], sys.argv[2]
od = sys.argv[3] if len(sys.argv) > 3 else md
srcs, mts = frames(sd), frames(md)
n = min(len(srcs), len(mts))
L = ['绿幕帧目录 %s' % sd, '抠后帧目录 %s' % md, '共 %d 帧' % n, '']
L.append('%-5s %-9s %-9s %-9s %-8s %-7s %-9s %-9s'
         % ('帧', '背景误留', '人物误抠', '不透明', '内容', 'd>=3', '蓝发被抠', 'q60'))
rows = []
for i in range(n):
    im = rd(srcs[i])
    mt = rd(mts[i])
    if im.ndim == 2:
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    im = im[..., :3].astype(np.float32)
    if mt.ndim == 2:
        mt = cv2.cvtColor(mt, cv2.COLOR_GRAY2BGRA)
    elif mt.shape[2] == 3:
        mt = cv2.cvtColor(mt, cv2.COLOR_BGR2BGRA)
    a = mt[..., 3]
    h, w = a.shape
    k = 40
    bg = np.concatenate([im[0:k, 0:k].reshape(-1, 3), im[0:k, w - k:w].reshape(-1, 3),
                         im[h - k:h, 0:k].reshape(-1, 3),
                         im[h - k:h, w - k:w].reshape(-1, 3)]).mean(0)
    dist = np.sqrt(((im - bg) ** 2).sum(2))
    src_bg = dist < 45
    kept = a > 128
    a8 = a >= 8
    bg_kept = int((src_bg & kept).sum())
    fg_drop = int((~src_bg & ~kept).sum())
    rgb = mt[..., 2::-1].astype(np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    d = g - np.maximum(r, b)
    bl = (b - r)
    blue = (bl > 30) & (b > 80)
    q = np.where(bl > 0, (g - r).astype(np.float32) / np.maximum(bl, 1), 0.0)
    rows.append((i + 1, bg_kept, fg_drop, int(kept.sum()), int(a8.sum()),
                 int(((d >= 3) & a8).sum()), int((blue & ~(a > 200)).sum()),
                 int(((q >= 0.6) & blue & a8).sum()), bg.round(1)))
    L.append('%-5d %-9d %-9d %-9d %-8d %-7d %-9d %-9d'
             % (i + 1, rows[-1][1], rows[-1][2], rows[-1][3], rows[-1][4],
                rows[-1][5], rows[-1][6], rows[-1][7]))
L.append('')
A = np.array([[r[1], r[2], r[3], r[5], r[6], r[7]] for r in rows])
L.append('汇总（56 帧）：背景误留 max %d / 均值 %.0f ；人物误抠 max %d / 均值 %.0f'
         % (A[:, 0].max(), A[:, 0].mean(), A[:, 1].max(), A[:, 1].mean()))
L.append('  不透明 px：min %d / max %d（峰峰 %d）'
         % (A[:, 2].min(), A[:, 2].max(), A[:, 2].max() - A[:, 2].min()))
L.append('  d>=3 合计 %d ；蓝发被抠 合计 %d ；q60 合计 %d'
         % (A[:, 3].sum(), A[:, 4].sum(), A[:, 5].sum()))
bgs = np.array([r[8] for r in rows])
L.append('  每帧背景估计 RGB：均值 %s ；逐帧 std %s ；峰峰 G %.1f'
         % (bgs.mean(0).round(1), bgs.std(0).round(2),
            bgs[:, 1].max() - bgs[:, 1].min()))
out = os.path.join(od, 'verify2.txt')
with io.open(out, 'w', encoding='utf-8') as f:
    f.write('\n'.join(L) + '\n')
print('OK ' + out)
