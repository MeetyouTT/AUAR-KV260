# -*- coding: utf-8 -*-
"""眼区“蓝瞳占比”探针（变长帧数版，只读）。

派生自 `batch_001/tools/blink_probe_v2_iris.py`：算法、坐标框（x∈[0.41,0.59]，y∈[0.125,0.175]）、
判据（`dip=(med-min)/med`：≥15% 强 / 8–15% 弱 / <8% 无；闭眼帧 = `blue_frac < 0.72*med`）**完全一致**，
唯一差别是**去掉“必须正好 39 帧”的硬约束**（batch_002/batch_003 的探针是 124 帧），
因此两者的 `dip_ratio` / `closed_frames` 可直接对表。

用法（本机无 python 别名，用 ComfyUI 便携解释器）：
  python.exe -s blink_probe_iris_mlen.py --dirs <帧目录1> [<帧目录2> ...] --out <报告.txt> [--json <附档.json>]
输出：逐目录的 median/min/dip/闭眼帧列表 + 完整曲线；附档 JSON 便于程序化对表。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

X0, Y0, X1, Y1 = 0.41, 0.125, 0.59, 0.175
MIN_FRAMES = 2


def blue_frac(path: Path) -> float:
    with Image.open(path) as im:
        a = np.asarray(im.convert("RGB"), dtype=np.float32)
    h, w = a.shape[:2]
    box = a[int(Y0 * h):int(Y1 * h), int(X0 * w):int(X1 * w)]
    r, g, b = box[..., 0], box[..., 1], box[..., 2]
    return float(((b > r + 20) & (b > g + 10)).mean())


def probe(d: Path) -> dict:
    pngs = sorted(d.glob("*.png"))
    rec = {"id": d.name, "png": len(pngs), "dir": str(d)}
    if len(pngs) < MIN_FRAMES:
        rec["error"] = "need >=%d frames" % MIN_FRAMES
        return rec
    f = np.asarray([blue_frac(p) for p in pngs])
    med = float(np.median(f))
    sd = 1.4826 * float(np.median(np.abs(f - med)))      # MAD 稳健噪声底
    i_min = int(np.argmin(f))
    fmin = float(f[i_min])
    dip = (med - fmin) / med if med > 0 else 0.0
    closed = [int(i) for i in np.where(f < 0.72 * med)[0]]
    if dip >= 0.15 and (med - fmin) >= 3.0 * max(sd, 1e-6):
        verdict = "BLINK"
    elif dip >= 0.08:
        verdict = "WEAK"
    else:
        verdict = "NONE"
    rec.update({
        "blue_frac_median": round(med, 4),
        "blue_frac_min": round(fmin, 4),
        "min_frame": i_min,
        "dip_ratio": round(dip, 3),
        "noise_sd": round(sd, 4),
        "closed_frames": closed,
        "verdict": verdict,
        "curve": [round(float(v), 4) for v in f],
    })
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="iris-band blink probe (variable length, read-only)")
    ap.add_argument('--spec', default='', help='UTF-8 JSON: {"dirs":[...],"out":"...","json":"..."}')
    ap.add_argument('--dirs', nargs='*', default=[])
    ap.add_argument('--out', default='')
    ap.add_argument('--json', default='')
    a = ap.parse_args(argv)
    if a.spec:
        with open(a.spec, 'r', encoding='utf-8') as f:
            s = json.load(f)
        a.dirs = a.dirs or list(s.get('dirs', []))
        a.out = a.out or s.get('out', '')
        a.json = a.json or s.get('json', '')
    if not a.dirs or not a.out:
        print('need --dirs <d1> [<d2> ...] --out <txt> (or --spec with those fields)', flush=True)
        return 2

    lines = []
    recs = []
    lines.append('== 眼区蓝瞳占比探针（变长版；判据与 batch_001 blink_probe_v2_iris.py 一致） ==')
    lines.append('眼区 x∈[%.2f,%.2f] y∈[%.2f,%.2f]（整幅比例）; 闭眼帧阈值 blue_frac < 0.72*median'
                 % (X0, X1, Y0, Y1))
    for d in a.dirs:
        rec = probe(Path(d))
        recs.append(rec)
        if 'error' in rec:
            lines.append('[%s] ERROR %s' % (rec['id'], rec['error']))
            continue
        lines.append('[%s] 帧数=%d  median=%.4f  min=%.4f @f%d  dip=%.1f%%  噪声sd=%.4f  判定=%s'
                     % (rec['id'], rec['png'], rec['blue_frac_median'], rec['blue_frac_min'],
                        rec['min_frame'], 100.0 * rec['dip_ratio'], rec['noise_sd'], rec['verdict']))
        lines.append('   闭眼帧(<0.72*median)=%s' % (rec['closed_frames'] or '无'))
        lines.append('   曲线=%s' % ','.join('%.3f' % v for v in rec['curve']))
    if len(recs) == 2 and all('error' not in r for r in recs):
        lines.append('')
        lines.append('== 对照 A=%s（基） vs B=%s（探针） ==' % (recs[0]['id'], recs[1]['id']))
        lines.append('  median %.4f -> %.4f ; dip %.1f%% -> %.1f%% ; min_frame %d -> %d'
                     % (recs[0]['blue_frac_median'], recs[1]['blue_frac_median'],
                        100.0 * recs[0]['dip_ratio'], 100.0 * recs[1]['dip_ratio'],
                        recs[0]['min_frame'], recs[1]['min_frame']))
        lines.append('  闭眼帧 A=%s  B=%s' % (recs[0]['closed_frames'], recs[1]['closed_frames']))
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    if a.json:
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump(recs, f, ensure_ascii=False, indent=2)
    print('\n'.join(lines), flush=True)
    print('BLINK_MLEN_DONE -> %s' % a.out, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
