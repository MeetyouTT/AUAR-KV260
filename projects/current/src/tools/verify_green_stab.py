# -*- coding: utf-8 -*-
"""生成帧的**绿幕稳定性**检查：逐帧取四角/四边背景块，看绿幕是否漂移。

色度键的前提是背景均匀且逐帧一致；i2v 模型可能在中间帧把绿幕画成渐变/加阴影。
用法: python aura_bg_stab.py <绿幕帧目录>
"""
import os
import sys

import cv2
import numpy as np

EXTS = ('.png', '.jpg', '.jpeg', '.bmp')


def rd(p):
    return cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_UNCHANGED)


d = sys.argv[1]
fs = [os.path.join(d, f) for f in sorted(os.listdir(d))
      if os.path.splitext(f)[1].lower() in EXTS]
rows = []
for p in fs:
    im = rd(p)
    if im.ndim == 2:
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
    im = im[..., :3].astype(np.float32)
    h, w = im.shape[:2]
    s = 40
    blks = [im[0:s, 0:s], im[0:s, w - s:w], im[h - s:h, 0:s], im[h - s:h, w - s:w],
            im[h // 2 - s // 2:h // 2 + s // 2, 0:s],
            im[h // 2 - s // 2:h // 2 + s // 2, w - s:w]]
    m = np.concatenate([b.reshape(-1, 3) for b in blks]).mean(0)    # BGR 均值
    rows.append(m)
A = np.array(rows)
line = []
line.append('帧数 %d  尺寸 %dx%d' % (len(fs), w, h))
line.append('背景块 BGR 均值：全片均值 %s' % A.mean(0).round(2))
line.append('  逐帧 std：B %.2f  G %.2f  R %.2f  （越小=越稳定）'
            % tuple(A.std(0).round(3)))
line.append('  逐帧 G 的 min %.1f / max %.1f  → 峰峰 %.1f'
            % (A[:, 1].min(), A[:, 1].max(), float(np.ptp(A[:, 1]))))
line.append('  B 通道 min %.1f / max %.1f ; R 通道 min %.1f / max %.1f'
            % (A[:, 0].min(), A[:, 0].max(), A[:, 2].min(), A[:, 2].max()))
# 绿幕基色（RGB）与偏离
rgb = A[:, ::-1]
line.append('绿幕基色 RGB 均值 %s（源首帧实测 (13,247,34)）' % rgb.mean(0).round(1))
dev = np.sqrt(((rgb - rgb.mean(0)) ** 2).sum(1))
line.append('逐帧与全片均值的欧氏偏差：max %.2f（阈值 3 内视为稳定）' % dev.max())
out = os.path.join(d, 'bg_stab.txt')
with open(out, 'w', encoding='utf-8') as f:
    f.write('\n'.join(line) + '\n')
print('OK ' + out)
