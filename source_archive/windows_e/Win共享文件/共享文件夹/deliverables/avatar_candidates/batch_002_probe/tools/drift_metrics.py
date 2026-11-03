# -*- coding: utf-8 -*-
"""量化“中段手位/躯干漂移”：对同一提示词、同种子的两条素材逐帧测量轮廓指标并对照。

判据来源：接收端要求比对**首帧 / 最大偏移帧 / 末帧**的全身、脸、肩腰线、双手；
本脚本给出可复算的数值代理（不使用肉眼）：
  * subject_bbox     非绿幕像素的外接框（x0,x1,y0,y1）
  * width@h          按主体高度的相对高度 h 处的水平宽度
  * hand_edge@band   主体高度 0.58~0.78 区间的最左/最右边缘（双手所在带）
  * drift            相对首帧的最大偏差，并除以首帧主体宽度得到“占比”，便于跨长度比较

用法：
  python -B drift_metrics.py --baseline <39帧目录> --probe <124帧目录> --out <报告.txt>
可选：--key 0.0,0.5,1.0（要抽出的相对位置）--copy-dir <抽帧复制目录>
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

import numpy as np
from PIL import Image

REL_HEIGHTS = (0.30, 0.45, 0.60, 0.75)
HAND_BAND = (0.58, 0.78)


def load_frames(d):
    names = sorted(n for n in os.listdir(d) if n.lower().endswith('.png'))
    return [os.path.join(d, n) for n in names]


def metrics(path):
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(np.int16)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    key = (g - np.maximum(r, b)) > 25          # 绿幕判定：绿色显著高于红蓝
    subj = ~key
    ys, xs = np.nonzero(subj)
    if len(xs) == 0:
        return None
    x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
    h = max(1, y1 - y0)
    out = {'bbox': (x0, x1, y0, y1), 'w': x1 - x0, 'h': h}
    for rel in REL_HEIGHTS:
        row = min(a.shape[0] - 1, y0 + int(round(rel * h)))
        band = subj[max(0, row - 2):row + 3, :]
        cols = np.nonzero(band.any(axis=0))[0]
        out['w@%.2f' % rel] = int(cols.max() - cols.min() + 1) if len(cols) else 0
    r0 = y0 + int(round(HAND_BAND[0] * h))
    r1 = y0 + int(round(HAND_BAND[1] * h))
    band = subj[r0:r1 + 1, :]
    cols = np.nonzero(band.any(axis=0))[0]
    out['hand_l'] = int(cols.min()) if len(cols) else -1
    out['hand_r'] = int(cols.max()) if len(cols) else -1
    return out


def scan(paths, label, log):
    rows = []
    for i, p in enumerate(paths):
        m = metrics(p)
        if m is None:
            log('  ! %s 第 %d 帧无主体，跳过' % (label, i))
            continue
        rows.append((i, m))
        if (i + 1) % 20 == 0:
            log('  ...%s %d/%d' % (label, i + 1, len(paths)))
    return rows


def summarize(label, rows, log):
    base = rows[0][1]
    w0 = max(1, base['w'])
    lines = ['[%s] 帧数=%d 首帧宽=%d' % (label, len(rows), base['w'])]
    keys = ['cx', 'w@0.30', 'w@0.45', 'w@0.60', 'w@0.75', 'hand_l', 'hand_r']
    acc = {k: 0.0 for k in keys}
    worst = {k: (0, 0.0) for k in keys}
    for idx, m in rows[1:]:
        cx0 = (base['bbox'][0] + base['bbox'][1]) / 2.0
        cx = (m['bbox'][0] + m['bbox'][1]) / 2.0
        cand = {'cx': abs(cx - cx0)}
        for k in keys[1:]:
            cand[k] = abs(float(m.get(k, 0)) - float(base.get(k, 0)))
        for k, v in cand.items():
            if v > acc[k]:
                acc[k] = v
            if v > worst[k][1]:
                worst[k] = (idx, v)
    for k in keys:
        lines.append('  %-8s max_abs=%7.1f px  = %5.2f%% of 首帧宽  @frame %d'
                     % (k, acc[k], 100.0 * acc[k] / w0, worst[k][0]))
    log('\n'.join(lines))
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', required=True)
    ap.add_argument('--probe', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--copy-dir', default='')
    ap.add_argument('--key', default='0.0,0.5,1.0')
    ap.add_argument('--max-frames', type=int, default=0)
    a = ap.parse_args()

    lines = []
    def log(s):
        print(s, flush=True)
        lines.append(s)

    log('== drift_metrics ==')
    log('baseline=%s' % a.baseline)
    log('probe=%s' % a.probe)
    groups = {}
    for label, d in (('baseline_39', a.baseline), ('probe_124', a.probe)):
        if not os.path.isdir(d):
            log('MISSING dir: %s' % d)
            continue
        paths = load_frames(d)
        if a.max_frames:
            paths = paths[:a.max_frames]
        log('[%s] 帧文件数=%d' % (label, len(paths)))
        groups[label] = (paths, summarize(label, scan(paths, label, log), log))
        if a.copy_dir:
            os.makedirs(a.copy_dir, exist_ok=True)
            rel = [float(x) for x in a.key.split(',')]
            for frac in rel:
                i = min(len(paths) - 1, int(round(frac * (len(paths) - 1))))
                dst = os.path.join(a.copy_dir, '%s_f%04d.png' % (label, i))
                shutil.copy2(paths[i], dst)
                log('  copied %s -> %s' % (os.path.basename(paths[i]), dst))

    if len(groups) == 2:
        def parse(lineset):
            d = {}
            for l in lineset:
                for k in ('cx', 'w@0.30', 'w@0.45', 'w@0.60', 'w@0.75', 'hand_l', 'hand_r'):
                    if l.strip().startswith(k):
                        d[k] = float(l.split('=')[1].split('px')[0])
            return d
        p39 = parse(groups['baseline_39'][1])
        p124 = parse(groups['probe_124'][1])
        log('')
        log('== 对照（最大绝对偏差 px；越小越稳） ==')
        for k in ('cx', 'w@0.45', 'w@0.60', 'w@0.75', 'hand_l', 'hand_r'):
            if k in p39 and k in p124:
                ratio = (p124[k] / p39[k]) if p39[k] else float('inf')
                log('  %-8s 39帧=%7.1f  124帧=%7.1f  124/39=%s' % (k, p39[k], p124[k],
                                                                  ('%.2f' % ratio) if p39[k] else 'n/a'))
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    log('DRIFT_DONE -> %s' % a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
