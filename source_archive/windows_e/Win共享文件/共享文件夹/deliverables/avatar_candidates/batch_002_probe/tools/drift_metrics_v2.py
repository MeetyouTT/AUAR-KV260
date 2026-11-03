# -*- coding: utf-8 -*-
"""区域/命名更正版漂移度量（v2）。回应 `review_20261006/接收端验收结论.md` §3 的三条纠正。

v1（`drift_metrics.py`）的三个问题与 v2 的处理：

| v1 名字 | v1 错在哪 | v2 名字 / 做法 |
|---|---|---|
| `hand_l` / `hand_r`（“左右手”） | 取相对高度 0.58–0.78，实测落在 **y=892–1188**，是**长发与腿**所在带，**根本没覆盖手**（手在 y≈650–740） | 更名 **`low_edge_l/r@y892_1188`**，只解释为“下部外缘” |
| `w@0.45`（“腹部宽度”） | 该横带（y≈700）同时穿过**手、围裙与两侧长发**，宽度是**前景跨度**不是腹部宽度 | 更名 **`span@y700`**，显式声明“含手/围裙/长发” |
| `cx`（“质心”） | 实际是**外接框横向中点**，受长发外轮廓影响 | 更名 **`bbox_cx`** |

另新增接收端实际使用的**手/前臂 ROI 外观代理**：固定 ROI `x=300..555, y=540..770` 上
肤色掩码 `(r>100)&(r-g>10)&(g-b>0)&(r-b>18)` 的中心位移（掩码定义与
`batch_001/tools/measure_review_motion.py` 完全一致，便于与接收端 `region_diagnostics.json` 对表）。
**这不是腕关节追踪，不能单独作为通过/失败判据。**

所有坐标均为 **864x1536 原图像素**（不是最终播放画布），取样行均为**固定绝对行**，不重定中心、不缩放。

用法（本机无 python 别名，用 ComfyUI 便携解释器 python_standalone\\python.exe -s 调用）：
  python.exe -s drift_metrics_v2.py --baseline <39帧目录> --probe <124帧目录> --out <报告.txt>
  或（路径含中文、需脱离终端启动时）：python.exe -s drift_metrics_v2.py --spec <UTF-8 JSON>
    JSON 字段：baseline / probe / out / copy_dir / label_base / label_probe
    说明：spec 方式下命令行本身可全为 ASCII，避免 PowerShell 5.1 误读 UTF-8 参数。
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

import numpy as np
from PIL import Image

ROWS = (
    ('span@y478', 478, '胸（rel≈0.30）'),
    ('span@y700', 700, '含手/围裙/长发的横带（v1 误称“腹部”）'),
    ('span@y921', 921, '腰下'),
    ('span@y1143', 1143, '腿'),
)
LOW_BAND = (892, 1188)          # v1 的“hand band 0.58–0.78”，实为长发/腿
HAND_ROI = (300, 555, 540, 770)  # x0,x1,y0,y1 —— 手+前臂（接收端所用固定 ROI）
KEYS = ('bbox_cx', 'span@y478', 'span@y700', 'span@y921', 'span@y1143',
        'low_edge_l@y892_1188', 'low_edge_r@y892_1188', 'hand_skin_x', 'hand_skin_y')


def load_frames(d):
    names = sorted(n for n in os.listdir(d) if n.lower().endswith('.png'))
    return [os.path.join(d, n) for n in names]


def metrics(path):
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.int16)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    subj = (g - np.maximum(r, b)) <= 25      # 非绿幕
    ys, xs = np.nonzero(subj)
    if len(xs) == 0:
        return None
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    out = {'bbox': (x0, x1, y0, y1), 'w': x1 - x0 + 1, 'h': y1 - y0 + 1,
           'bbox_cx': (x0 + x1) / 2.0}
    for name, row, _ in ROWS:
        band = subj[max(0, row - 2):row + 3, :]
        cols = np.nonzero(band.any(axis=0))[0]
        out[name] = int(cols.max() - cols.min() + 1) if len(cols) else 0
    band = subj[LOW_BAND[0]:LOW_BAND[1] + 1, :]
    cols = np.nonzero(band.any(axis=0))[0]
    out['low_edge_l@y892_1188'] = int(cols.min()) if len(cols) else -1
    out['low_edge_r@y892_1188'] = int(cols.max()) if len(cols) else -1
    sx0, sx1, sy0, sy1 = HAND_ROI
    roi = a[sy0:sy1, sx0:sx1]
    rr, gg, bb = roi[:, :, 0], roi[:, :, 1], roi[:, :, 2]
    skin = (rr > 100) & ((rr - gg) > 10) & ((gg - bb) > 0) & ((rr - bb) > 18)
    yy, xx = np.nonzero(skin)
    out['hand_skin_x'] = float(xx.mean() + sx0) if len(xx) else float('nan')
    out['hand_skin_y'] = float(yy.mean() + sy0) if len(yy) else float('nan')
    out['hand_skin_px'] = int(len(xx))
    return out


def scan(paths, label, log):
    rows = []
    for i, p in enumerate(paths):
        m = metrics(p)
        if m is None:
            log('  ! %s 第 %d 帧无主体，跳过' % (label, i))
            continue
        rows.append((i, m))
        if (i + 1) % 40 == 0:
            log('  ...%s %d/%d' % (label, i + 1, len(paths)))
    return rows


def summarize(label, rows, log):
    base = rows[0][1]
    w0 = max(1, base['w'])
    lines = ['[%s] 帧数=%d 首帧主体 x=%d..%d y=%d..%d 宽=%d（原图像素）'
             % (label, len(rows), base['bbox'][0], base['bbox'][1],
                base['bbox'][2], base['bbox'][3], base['w'])]
    acc, worst = {k: 0.0 for k in KEYS}, {k: (0, 0.0) for k in KEYS}
    skin = []
    for idx, m in rows:
        cand = {'bbox_cx': abs(m['bbox_cx'] - base['bbox_cx'])}
        for k in KEYS[1:]:
            cand[k] = abs(float(m[k]) - float(base[k]))
        for k, v in cand.items():
            if v != v:          # NaN（肤色掩码为空）
                continue
            if v > acc[k]:
                acc[k] = v
            if v > worst[k][1]:
                worst[k] = (idx, v)
        d = np.hypot(m['hand_skin_x'] - base['hand_skin_x'],
                     m['hand_skin_y'] - base['hand_skin_y'])
        if d == d:
            skin.append((idx, float(d)))
    hints = dict((n, h) for n, _, h in ROWS)
    for k in KEYS:
        lines.append('  %-22s max_abs=%7.2f px = %5.2f%% of 首帧宽 @frame %-4d %s'
                     % (k, acc[k], 100.0 * acc[k] / w0, worst[k][0], hints.get(k, '')))
    if skin:
        idx, d = max(skin, key=lambda t: t[1])
        lines.append('  %-22s max_abs=%7.2f px = %5.2f%% of 首帧宽 @frame %-4d %s'
                     % ('hand_skin_shift', d, 100.0 * d / w0, idx,
                        '手/前臂 ROI 外观代理（非腕部追踪，不作判据）'))
    log('\n'.join(lines))
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--spec', default='')
    ap.add_argument('--baseline', default='')
    ap.add_argument('--probe', default='')
    ap.add_argument('--out', default='')
    ap.add_argument('--copy-dir', default='')
    ap.add_argument('--label-base', default='')
    ap.add_argument('--label-probe', default='')
    a = ap.parse_args()
    if a.spec:
        import json
        with open(a.spec, 'r', encoding='utf-8') as f:
            s = json.load(f)
        a.baseline = a.baseline or s.get('baseline', '')
        a.probe = a.probe or s.get('probe', '')
        a.out = a.out or s.get('out', '')
        a.copy_dir = a.copy_dir or s.get('copy_dir', '')
        a.label_base = a.label_base or s.get('label_base', 'baseline_39')
        a.label_probe = a.label_probe or s.get('label_probe', 'probe_124')
    a.label_base = a.label_base or 'baseline_39'
    a.label_probe = a.label_probe or 'probe_124'
    if not (a.baseline and a.probe and a.out):
        print('need --baseline --probe --out (or --spec with those fields)', flush=True)
        return 2

    lines = []

    def log(s):
        print(s, flush=True)
        lines.append(s)

    log('== drift_metrics_v2（区域/命名更正版，回应接收端 §3） ==')
    log('固定绝对取样行：' + '; '.join('%s=y%d(%s)' % (n, y, h) for n, y, h in ROWS))
    log('下部外缘带：y%d..%d（v1 误称 hand band）; 手/前臂 ROI：x%d..%d y%d..%d'
        % (LOW_BAND[0], LOW_BAND[1], HAND_ROI[0], HAND_ROI[1], HAND_ROI[2], HAND_ROI[3]))
    log('注意：以上坐标均为 864x1536 原图像素，不是最终播放画布。')
    groups = {}
    for label, d in ((a.label_base, a.baseline), (a.label_probe, a.probe)):
        if not os.path.isdir(d):
            log('MISSING dir: %s' % d)
            continue
        paths = load_frames(d)
        log('[%s] 帧文件数=%d' % (label, len(paths)))
        groups[label] = (paths, summarize(label, scan(paths, label, log), log))
        if a.copy_dir:
            os.makedirs(a.copy_dir, exist_ok=True)
            for frac in (0.0, 0.5, 1.0):
                i = min(len(paths) - 1, int(round(frac * (len(paths) - 1))))
                dst = os.path.join(a.copy_dir, 'v2_%s_f%04d.png' % (label, i))
                shutil.copy2(paths[i], dst)
                log('  copied %s -> %s' % (os.path.basename(paths[i]), dst))

    if len(groups) == 2:
        def parse(lineset):
            d = {}
            for l in lineset:
                for k in KEYS + ('hand_skin_shift',):
                    if l.strip().startswith(k):
                        d[k] = float(l.split('=')[1].split('px')[0])
            return d
        p39, p124 = parse(groups[a.label_base][1]), parse(groups[a.label_probe][1])
        log('')
        log('== 对照（最大绝对偏差 px，原图像素；越小越稳） ==')
        lb, lp = a.label_base, a.label_probe
        for k in KEYS + ('hand_skin_shift',):
            if k in p39 and k in p124 and p39[k]:
                log('  %-22s %s=%7.2f  %s=%7.2f  probe/base=%.2f'
                    % (k, lb, p39[k], lp, p124[k], p124[k] / p39[k]))
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    log('DRIFT_V2_DONE -> %s' % a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())

