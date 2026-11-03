"""Compare real idle/speech rendering and exercise the cached audio/FSM path."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

AURA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AURA))
from tools.demo_script import create_demo_core
from tools.realtime_facials import RealtimeFacials
from tools.selected_voice_demo import SelectedVoiceRunner, VoicePlan, activity_envelope, warm_script_assets
from tools.facial_layers import aperture_levels, interpolate

OUT = AURA.parent / 'deliverables/2026-10-09_speech_idle_alignment'
ROWS = [('neutral', 'SPEAKING_NEUTRAL', 'greeting', '平静'),
        ('happy', 'SPEAKING', 'excited', '开心'),
        ('low', 'SPEAKING_LOW', 'gentle', '安慰')]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    idle, speech = create_demo_core('reuse'), create_demo_core('reuse')
    idle_faces, speech_faces = RealtimeFacials(idle), RealtimeFacials(speech)
    plan = VoicePlan()
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 18)
    timing, previews, contact, closeups, positions = [], [], [], [], []
    max_body_difference = 0
    for slug, state, scene, label in ROWS:
        idle.reset_playback(); speech.reset_playback()
        envelope = activity_envelope(plan.clips[scene])
        levels = aperture_levels(plan.clips[scene])
        frames = []
        for i in range(121):
            t = i / 20
            gain = interpolate(envelope['gains'], t, envelope['hop_seconds'])
            level = interpolate(levels, t)
            left = idle_faces.apply(idle.frame_at('IDLE', t), t, 0, 0)
            started = time.perf_counter()
            right = speech_faces.apply(speech.frame_at(state, t), t, gain, level)
            timing.append((time.perf_counter()-started)*1000)
            a, b = np.asarray(left['image']), np.asarray(right['image'])
            max_body_difference = max(max_body_difference, int(np.count_nonzero(a[170:] != b[170:])))
            assert max_body_difference == 0, 'Speech changed the idle body below the mouth'
            assert np.array_equal(a[:, :, 3], b[:, :, 3]), 'Speech changed the silhouette'
            assert left['body_source_position'] == right['body_source_position']
            frame = Image.new('RGB', (940, 522), '#FCFCF3')
            draw = ImageDraw.Draw(frame)
            draw.text((16, 8), label+' / 原待机', font=font, fill='#283540')
            draw.text((486, 8), label+' / 待机身体＋独立嘴型', font=font, fill='#283540')
            portraits = []
            for x, meta in ((3, left), (473, right)):
                portrait = Image.new('RGBA', (464, 480), '#FCFCF3')
                portrait.alpha_composite(meta['image'])
                frame.paste(portrait.convert('RGB'), (x, 39))
                portraits.append(portrait)
            frames.append(frame.resize((705, 392), Image.Resampling.LANCZOS))
            if i in (20, 60, 100):
                contact.append(frames[-1])
                detail = Image.new('RGB', (672, 278), '#FCFCF3')
                dd = ImageDraw.Draw(detail)
                dd.text((8, 6), f'{label} {t:.1f}s / 待机                 说话', font=font, fill='#283540')
                for n, portrait in enumerate(portraits):
                    crop = portrait.crop((169, 91, 281, 171)).resize((336, 240), Image.Resampling.NEAREST)
                    detail.paste(crop.convert('RGB'), (n*336, 38))
                closeups.append(detail)
                positions.append({'emotion': slug, 'time': t, 'body_source_position': right['body_source_position'],
                                  'mouth_matrix': right['mouth_matrix']})
        path = OUT/(slug+'_idle_speech.webp')
        frames[0].save(path, save_all=True, append_images=frames[1:],
                       duration=50, loop=0, quality=78, method=1)
        previews.append(path.name)
        print('PREVIEW_OK', slug, flush=True)

    for name, items, width, height in [('contact.png', contact, 705, 392),
                                     ('face_alignment.png', closeups, 672, 278)]:
        sheet = Image.new('RGB', (width*3, height*3), '#FCFCF3')
        for i, frame in enumerate(items):
            sheet.paste(frame, ((i % 3)*width, (i // 3)*height))
        sheet.save(OUT/name)

    # Use the real selected-voice/FSM/display path, including actions and cut.
    warm_script_assets(speech)
    runner = SelectedVoiceRunner(speech, plan, effects=True); runner.reset()
    samples, render_times = [], []
    for i in range(int(plan.end*30)+2):
        t = min(plan.end, i/30)
        started = time.perf_counter(); meta = runner.advance(t)
        render_times.append((time.perf_counter()-started)*1000)
        if meta and meta['asset'] in speech._reuse_anchors:
            assert meta['body_asset'] == 'idle_normal'
            samples.append((meta['asset'], meta['body_source_position']))
    assert not runner.trace.errors and not runner.trace.rejected
    assert runner.trace.samples[-1]['display_state'] == 'IDLE'
    assert {asset for asset, _ in samples} == set(speech._reuse_anchors)
    assert all(np.ptp([p for a, p in samples if a == asset]) > .1 for asset in speech._reuse_anchors)
    tracked = ['tools/idle_body_compositor.py', 'tools/facial_layers.py',
               'board/interaction/avatar_player.py', 'tests/test_speech_idle_body.py',
               'tools/realtime_facials.py', 'tools/demo_script.py',
               'tools/selected_voice_demo.py', 'tools/realtime_stage.py',
               'tools/verify_speech_idle_body.py',
               '../deliverables/2026-10-06_avatar_reuse/preview_script.py']
    report = {
        'status': 'PASS', 'scope': 'PC offline real cached voice/FSM rendering; no device benchmark',
        'body_method': 'Existing idle_normal sequence and production cursor; tracked local mouth and eye patches',
        'new_body_motion_effects': False,
        'preview_checks': {'samples': 363, 'body_changed_pixels_below_y170': max_body_difference,
                           'alpha_identical': True, 'idle_speech_cursor_identical': True},
        'regression': {'selected_script_samples': len(runner.trace.samples),
                       'duration_seconds': plan.end, 'errors': runner.trace.errors, 'rejected': runner.trace.rejected,
                       'final_state': runner.trace.samples[-1]['display_state'],
                       'mouth_sets_used': sorted({asset for asset, _ in samples})},
        'speech_render_ms': {'p95': float(np.percentile(timing, 95)), 'max': max(timing)},
        'full_script_render_ms': {'p95': float(np.percentile(render_times, 95)), 'max': max(render_times)},
        'previews': previews, 'example_positions': positions,
        'source_sha256': {path: hashlib.sha256((AURA/path).read_bytes()).hexdigest() for path in tracked}}
    (OUT/'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    cards = ''.join('<section><h2>'+label+'</h2><img src="'+slug+'_idle_speech.webp"></section>'
                    for slug, _, _, label in ROWS)
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<title>汐蓝说话与待机动画对齐</title><style>
body{background:#111e30;color:#e5edf8;font:17px system-ui;margin:32px auto;max-width:1000px}
h1{font-size:27px}img{width:100%;border-radius:12px}section{margin:32px 0}p{line-height:1.7}</style>
<h1>说话沿用现有待机动画</h1><p>左侧为现有待机，右侧叠加独立嘴型。两侧身体帧、播放游标和眨眼时间线一致。
这里没有新增身体动态效果；嘴型依据已有录音的发声与音强开合。动画对照无声。</p>'''+cards+'''
<section><h2>嘴型与脸部对齐抽帧</h2><img src="face_alignment.png"></section></html>'''
    (OUT/'index.html').write_text(page, encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ('source_sha256', 'example_positions')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
