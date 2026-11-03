"""Read-only raw-frame audit and fixed-coordinate contact sheets; no acceptance by metric."""
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent
BATCH = OUT.parent
PREV = BATCH.parent / 'batch_001'
RAW = BATCH / 'raw/e1_rest_s421001_L124'
BASE = PREV / 'raw/talking_calm_rest_v3_s421001'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def diff(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        result = []
        for k in sorted(a.keys() | b.keys()):
            if k not in a or k not in b:
                result.append({'path': path+'/'+k, 'before': a.get(k), 'after': b.get(k)})
            else:
                result.extend(diff(a[k], b[k], path+'/'+k))
        return result
    return [] if a == b else [{'path': path, 'before': a, 'after': b}]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sheet(folder, indices, dest, panels, width=216, columns=None):
    columns = columns or len(indices)
    panel_heights = [round(width*(box[3]-box[1])/(box[2]-box[0])) for box in panels]
    cell_h = 24 + sum(panel_heights) + 6*(len(panels)-1)
    canvas = Image.new('RGB', (columns*width, ((len(indices)+columns-1)//columns)*cell_h), '#eeeeee')
    draw = ImageDraw.Draw(canvas)
    for j, idx in enumerate(indices):
        x, y = (j % columns)*width, (j//columns)*cell_h
        draw.text((x+6, y+5), f'frame {idx:03d}', fill='black')
        y += 24
        with Image.open(folder / f'{idx:06d}.png') as im:
            for box, height in zip(panels, panel_heights):
                canvas.paste(im.crop(box).resize((width, height), Image.Resampling.LANCZOS), (x, y))
                y += height+6
    canvas.save(OUT / dest)


def main():
    meta = json.loads((RAW/'meta.json').read_text(encoding='utf-8-sig'))
    graph = BATCH/'workflows/e1_rest_s421001_L124_api.json'
    base_graph = PREV/'workflows/talking_calm_rest_v3_s421001_api.json'
    files = sorted(RAW.glob('*.png'))
    assert [p.name for p in files] == [f'{i:06d}.png' for i in range(124)]
    records = []
    for p in files:
        with Image.open(p) as im:
            im.load()
            assert im.size == (864, 1536)
            records.append({'file': p.name, 'size': list(im.size), 'mode': im.mode, 'sha256': sha(p)})
    assert records[0]['sha256'] == meta['sha256_first']
    assert records[-1]['sha256'] == meta['sha256_last']
    assert sha(graph) == meta['api_graph_sha256']
    changes = diff(json.loads(base_graph.read_text(encoding='utf-8-sig')), json.loads(graph.read_text(encoding='utf-8-sig')))
    assert changes == [{'path': '/7/inputs/length', 'before': 39, 'after': 124}]
    integrity = {'frame_count': len(files), 'consecutive_and_readable': True, 'first_last_and_graph_hash_match_meta': True,
                 'graph_sha256': sha(graph), 'baseline_graph_sha256': sha(base_graph), 'graph_differences': changes,
                 'frames': records}
    (OUT/'integrity.json').write_text(json.dumps(integrity, indent=2), encoding='utf-8')
    motion = load_module('hand_motion', PREV/'tools/measure_review_motion.py')
    drift = load_module('raw_drift', BATCH/'tools/drift_metrics.py')
    diagnostic = {'caution': 'Skin-color centroid is an appearance proxy, not wrist tracking; not an acceptance gate.', 'cases': []}
    for label, folder in [('baseline_39', BASE), ('probe_124', RAW)]:
        paths = sorted(folder.glob('*.png'))
        pts = np.asarray([motion.center(p) for p in paths])
        distances = np.linalg.norm(pts-pts[0], axis=1)
        worst = int(distances.argmax())
        bbox = drift.metrics(paths[0])['bbox']
        y0, y1 = bbox[2:]
        h = y1-y0
        diagnostic['cases'].append({'label': label, 'frame_count': len(paths),
            'skin_roi_xyxy': [300,540,555,770], 'max_skin_centroid_source_px': float(distances[worst]),
            'max_skin_centroid_frame': worst, 'skin_centers': pts.tolist(),
            'old_script_first_bbox': bbox,
            'old_script_hand_band_y': [y0+round(.58*h), y0+round(.78*h)],
            'old_script_width_sample_y': {str(v): y0+round(v*h) for v in drift.REL_HEIGHTS}})
        sheet(folder, [0, worst, len(paths)-1], label+'_hands.png', [(270,470,585,780)], width=315)
    (OUT/'region_diagnostics.json').write_text(json.dumps(diagnostic, indent=2), encoding='utf-8')
    for start in (0, 64):
        sheet(RAW, list(range(start, min(start+64,124))), f'faces_{start:03d}.png', [(310,170,540,340)], width=184, columns=8)
    selected = [0, 13, 27, 35, 62, 100, 115, 123]
    sheet(RAW, selected, 'probe_keyframes.png', [(0,0,864,1536),(285,95,570,345),(260,345,590,790)], width=190)
    sheet(RAW, [42,44,45,46,47,49,51,81,82,83,84,85,87,90], 'blink_evidence.png', [(310,170,540,340)], width=184, columns=7)
    with Image.open(RAW/'000000.png') as source:
        region_map = source.convert('RGB')
    draw = ImageDraw.Draw(region_map)
    draw.rectangle((0,892,863,1188), outline='red', width=5)
    draw.text((30,905), 'OLD "HAND" BAND: y892..1188 (hair / legs)', fill='red', stroke_width=1)
    draw.rectangle((300,540,555,770), outline='yellow', width=5)
    draw.text((300,520), 'HAND + FOREARM ROI', fill='black')
    region_map.save(OUT/'metric_regions.png')
    # Fixed coordinates preserve drift. No recentering, warping, or background removal.
    print(json.dumps({'integrity': {k:v for k,v in integrity.items() if k!='frames'},
                      'regions': [{k:v for k,v in row.items() if k!='skin_centers'} for row in diagnostic['cases']]}, indent=2))


if __name__ == '__main__':
    main()
