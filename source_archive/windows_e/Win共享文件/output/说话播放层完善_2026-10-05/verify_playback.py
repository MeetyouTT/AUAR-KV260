"""Compare exact same source assets/clock/seed before and after playback fixes."""
import importlib.util
import json
import random
import sys
import time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(r'E:\项目\共享文件夹\aura')
OUT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from board.interaction.avatar_player import AvatarPlayer
from board.interaction import avatar_assets
from tools.demo_script import ScriptRunner
spec = importlib.util.spec_from_file_location('board.interaction.before_player', OUT/'before/avatar_player.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)

def array(im):
    im = im.resize((116, 120), Image.Resampling.BILINEAR)
    bg = Image.new('RGBA', im.size, (252, 252, 243, 255))
    bg.alpha_composite(im)
    return np.asarray(bg.convert('RGB'), dtype=np.float32)

def measure(cls, hz):
    p = cls(rng=random.Random(7)); p.idle_gain = 0
    prev = None; diffs = []; jumps = []; boundaries = []; frames = []; rows = []
    for i in range(26 * hz + 1):
        t = i / hz
        state = 'SPEAKING_NEUTRAL' if t < 24 else 'IDLE'
        m = p.display_frame(state, t)
        r = {k:m[k] for k in ['asset', 'index', 'stage', 'display_state']}
        r['t'] = t
        r['source_position'] = m.get('source_position', m['index'])
        arr = array(m['image'])
        if prev:
            a, oldarr, oldimg = prev
            d = float(np.abs(arr - oldarr).mean()); diffs.append(d)
            same = a['asset'] == r['asset'] and a['display_state'] == r['display_state']
            if same and r['display_state'] == 'SPEAKING_NEUTRAL' and abs(r['index'] - a['index']) > 24 / hz + 1:
                jumps.append(dict(previous=a, current=r, mad=d))
            if a['stage'] != r['stage'] or a['asset'] != r['asset'] or (same and abs(r['index']-a['index']) >= 7):
                boundaries.append((d, a, r, oldimg.copy(), m['image'].copy()))
        prev = r, arr, m['image']; rows.append(r)
        if cls is AvatarPlayer and hz == 30 and 7 <= t <= 11 and i % 2 == 0:
            im = m['image'].copy(); im.thumbnail((290, 300))
            bg = Image.new('RGB', (290, 300), (252,252,243)); bg.paste(im,(0,0),im)
            frames.append(bg)
    if frames:
        frames[0].save(OUT/'说话连续播放预览.gif', save_all=True, append_images=frames[1:], duration=67, loop=0)
    boundaries.sort(key=lambda x:x[0], reverse=True)
    return dict(hz=hz, samples=len(rows), speaking_large_index_jumps=len(jumps), jumps=jumps,
                max_pixel_mad=max(diffs), p95_pixel_mad=float(np.percentile(diffs,95)),
                finished_display=rows[-1]['display_state']), boundaries, rows

report = {'note':'Same PNGs, seed 7, offsets disabled, 24s speech then stop. Pixel MAD on 116x120 composited images is a diagnostic proxy, NOT a perceptual score.', 'comparisons':[]}
panels = []
for hz in [12,30]:
    before, b, _ = measure(old.AvatarPlayer,hz)
    after, a, rows = measure(AvatarPlayer,hz)
    report['comparisons'].append({'before':before, 'after':after})
    assert after['speaking_large_index_jumps'] == 0
    assert after['finished_display'] == 'IDLE'
    if hz == 30:
        for name, items in [('BEFORE',b),('AFTER',a)]:
            for d, prev, curr, left, right in items[:3]:
                panels.append((name,d,prev,curr,left,right))
        (OUT/'continuity_frames.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
sheet = Image.new('RGB',(730,280*len(panels)), '#f5f5f5'); draw=ImageDraw.Draw(sheet)
for k,(name,d,prev,curr,left,right) in enumerate(panels):
    draw.text((10,k*280+4),f"{name} {curr['t']:.3f}s MAD {d:.2f} {prev['asset']}:{prev['index']} -> {curr['asset']}:{curr['index']}",fill='black')
    for j,im in enumerate([left,right]):
        im.thumbnail((270,240)); sheet.paste(im,(20+j*350,k*280+30),im)
sheet.save(OUT/'before_after_boundaries.png')
core = AvatarPlayer(rng=random.Random(7))
trace = ScriptRunner(core,dt=1/30).run(quiet=True)
report['script'] = {'errors':trace.errors,'rejected':trace.rejected,'state_spans':trace.state_spans()}
assert not trace.errors and not trace.rejected

# Keep source-level movement separate from player-level corrections.
asset_reports = []
for name in avatar_assets.all_asset_names():
    paths = avatar_assets.list_frames(avatar_assets.asset_dir(name))
    if not paths: continue
    ims = [Image.open(p).convert('RGBA') for p in paths]
    arrays = [array(im) for im in ims]
    raw = [float(np.abs(a-b).mean()) for a,b in zip(arrays,arrays[1:])]
    areas = [int((np.asarray(im.getchannel('A'))>100).sum()) for im in ims]
    asset_reports.append({'asset':name,'frames':len(paths),'max_adjacent_pixel_mad':max(raw),
                          'p95_adjacent_pixel_mad':float(np.percentile(raw,95)),
                          'alpha_area_range_over_mean':(max(areas)-min(areas))/float(np.mean(areas)),
                          'worst_pair':[int(np.argmax(raw)),int(np.argmax(raw))+1]})
report['source_asset_diagnostics'] = asset_reports
im = core.sequence('SPEAKING_NEUTRAL')[0][0]
from board.interaction.avatar_timing import idle_offsets
costs = {}
for cls,label in [(old.AvatarPlayer,'before'),(AvatarPlayer,'after')]:
    times=[]
    for i in range(90):
        start=time.perf_counter(); cls._apply_offsets(im,idle_offsets(i/30)); times.append((time.perf_counter()-start)*1000)
    costs[label]={'median_ms':float(np.median(times)),'p95_ms':float(np.percentile(times,95))}
report['offset_render_benchmark'] = costs
(OUT/'playback_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='source_asset_diagnostics'},ensure_ascii=False,indent=2))
