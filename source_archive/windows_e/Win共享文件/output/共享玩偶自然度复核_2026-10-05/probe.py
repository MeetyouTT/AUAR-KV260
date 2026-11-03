import sys, random, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

AURA = Path(r'E:\项目\共享文件夹\aura')
sys.path.insert(0, str(AURA))
from board.interaction.avatar_player import AvatarPlayer
from tools.demo_script import ScriptRunner

OUT = Path(__file__).parent
core = AvatarPlayer(rng=random.Random(7))
core.idle_gain = 0
rows, prev, best = [], None, []
for n in range(601):
    t = n / 30
    m = core.frame_at('SPEAKING_NEUTRAL', t)
    im = m['image'].resize((116, 120))
    bg = Image.new('RGBA', im.size, (252, 252, 243, 255))
    bg.alpha_composite(im)
    arr = np.asarray(bg.convert('RGB'), dtype=np.float32)
    row = dict(t=round(t, 4), asset=m['asset'], index=m['index'], stage=m['stage'], loop_round=core._loop_round)
    if prev is not None:
        old, oldarr, oldimg = prev
        d = float(np.abs(arr-oldarr).mean())
        boundary = old['asset'] != row['asset'] or old['stage'] != row['stage'] or old['loop_round'] != row['loop_round']
        row.update(mad=round(d, 3), boundary=boundary, previous=old)
        if boundary:
            best.append((d, dict(row), oldimg.copy(), m['image'].copy()))
    rows.append(row)
    prev = row.copy(), arr, m['image']
    prev[0].pop('previous', None)

best.sort(key=lambda x:x[0], reverse=True)
sheet = Image.new('RGB', (740, 5*280), '#f5f5f5')
draw = ImageDraw.Draw(sheet)
for k,(d,row,left,right) in enumerate(best[:5]):
    for j,im in enumerate((left,right)):
        im = im.copy(); im.thumbnail((260, 240))
        sheet.paste(im, (j*350+30, k*280+35), im)
    old = row['previous']
    draw.text((15,k*280+6), f"{row['t']:.3f}s | MAD {d:.2f} | {old['asset']}:{old['index']} -> {row['asset']}:{row['index']}", fill='black')
    draw.text((15,k*280+260), f"{old['stage']} round {old['loop_round']} -> {row['stage']} round {row['loop_round']}", fill='black')
sheet.save(OUT/'boundary_pairs.png')
script = AvatarPlayer(rng=random.Random(7)); script.idle_gain = 0
trace = ScriptRunner(script, dt=1/30).run(quiet=True)
result = dict(note='MAD is a diagnostic pixel difference, not a perceptual acceptance score. 30 Hz virtual sampling; idle offsets disabled.', top_boundaries=[x[1] for x in best[:12]], sample_count=len(rows), script_states=trace.state_spans(), script_rejected=trace.rejected, script_errors=trace.errors)
(OUT/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
