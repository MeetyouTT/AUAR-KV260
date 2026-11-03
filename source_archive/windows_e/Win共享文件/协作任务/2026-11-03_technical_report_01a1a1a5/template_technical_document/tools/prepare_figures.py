from pathlib import Path
import json, hashlib, shutil, sys
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')
R = Path(__file__).resolve().parents[1]
B = R.parent / 'v5_contribution_bjt_simsun'
F = R / 'figures'
FONT = ImageFont.truetype(r'C:\Windows\Fonts\simsun.ttc', 38)
manifest = []

for name in ['system_architecture.png', 'old_hardware_connections.png', 'old_vision_pipeline.png',
             'scheduler_flow.png', 'command_sequence.png', 'dialogue_lifecycle.png',
             'board_x11_live.png', 'history_model_latency.png', 'live_resources.png',
             'native_02b_xsim_wave_detail.png']:
    src = B / 'figures' / name
    dst = F / name
    shutil.copy2(src, dst)
    manifest.append({'file': name, 'source': str(src), 'sha256': hashlib.sha256(dst.read_bytes()).hexdigest(),
                     'kind': 'existing face-mosaic board capture' if name == 'board_x11_live.png' else 'existing verified project figure'})

# Crop only the surrounding unused native viewport area; model geometry is unchanged.
crops = {
 'assembly_isometric': (520, 300, 1650, 1220),
 'assembly_front': (650, 140, 2040, 1100),
 'assembly_side': (640, 130, 2070, 1150),
 'assembly_back': (740, 140, 2090, 1100),
 'part_front': (730, 220, 2120, 1100),
 'part_back': (880, 190, 1970, 1140),
 'part_base': (670, 210, 2110, 1100),
 'part_base_1': (1000, 100, 1690, 1200),
 'part_screen': (700, 210, 2130, 1090),
}
for stem, box in crops.items():
    src = F / (stem + '.png')
    out = F / (stem + '_focus.png')
    Image.open(src).crop(box).save(out)
    manifest.append({'file': out.name, 'source': str(src), 'source_sha256': hashlib.sha256(src.read_bytes()).hexdigest(),
                     'crop_px': box, 'kind': 'native SolidWorks export with viewport margins cropped; no model editing'})

def panel(out, entries, width=2000, height=1550):
    page = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(page)
    w, h = width // 2, height // 2
    for i, (stem, text) in enumerate(entries):
        im = Image.open(F / (stem + '_focus.png')).convert('RGB')
        im.thumbnail((w - 40, h - 115), Image.Resampling.LANCZOS)
        x, y = (i % 2) * w, (i // 2) * h
        page.paste(im, (x + (w - im.width) // 2, y + 15 + (h - 110 - im.height) // 2))
        draw.text((x + w // 2, y + h - 55), text, anchor='mm', font=FONT, fill='black')
    page.save(F / out)
    manifest.append({'file': out, 'kind': 'layout of unchanged native CAD views with SimSun panel labels',
                     'panels': entries})

panel('cad_orthographic_panel.png', [('assembly_front','正面'),('assembly_isometric','等轴视图'),
                                    ('assembly_back','背面'),('assembly_side','侧面')])
panel('cad_parts_panel.png', [('part_front','Front 前框'),('part_back','Back 壳体'),
                             ('part_base','base 支座'),('part_base_1','Base_1 基底板')])

(R / 'sources' / 'figure_sources.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print('Prepared figures:', len(manifest))
