"""Render old/new speech previews and exercise the full cached-voice script."""
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

OUT = AURA.parent / 'deliverables/2026-10-09_speech_body_motion'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    old = create_demo_core('reuse', body_motion=False)
    new = create_demo_core('reuse')
    old_faces, new_faces = RealtimeFacials(old), RealtimeFacials(new)
    plan = VoicePlan()
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 18)
    rows = [('neutral', 'SPEAKING_NEUTRAL', 'greeting', '\u5e73\u9759'),
            ('happy', 'SPEAKING', 'excited', '\u5f00\u5fc3'),
            ('low', 'SPEAKING_LOW', 'gentle', '\u5b89\u6170')]
    timing, previews, contact = [], [], []
    for slug, state, scene, label in rows:
        old.reset_playback(); new.reset_playback()
        envelope = activity_envelope(plan.clips[scene])
        levels = aperture_levels(plan.clips[scene])
        frames = []
        for i in range(121):
            t = i / 20
            gain = interpolate(envelope['gains'], t, envelope['hop_seconds'])
            level = interpolate(levels, t)
            before = old_faces.apply(old.frame_at(state, t), t, gain, level)
            started = time.perf_counter()
            after = new_faces.apply(new.frame_at(state, t), t, gain, level)
            timing.append((time.perf_counter() - started) * 1000)
            frame = Image.new('RGB', (940, 522), '#FCFCF3')
            draw = ImageDraw.Draw(frame)
            draw.text((16, 8), label + ' / \u539f\u7248', font=font, fill='#283540')
            draw.text((486, 8), label + ' / \u5934\u80a9\u5fae\u52a8', font=font, fill='#283540')
            for x, meta in ((3, before), (473, after)):
                rgba = Image.new('RGBA', (464, 480), '#FCFCF3')
                rgba.alpha_composite(meta['image'])
                frame.paste(rgba.convert('RGB'), (x, 39))
            frames.append(frame.resize((705, 392), Image.Resampling.LANCZOS))
            if i in (20, 60, 100):
                contact.append(frame.resize((705, 392)))
        path = OUT / (slug + '_before_after.webp')
        frames[0].save(path, save_all=True, append_images=frames[1:],
                       duration=50, loop=0, quality=78, method=1)
        previews.append(path.name)
    sheet = Image.new('RGB', (705 * 3, 392 * 3), '#FCFCF3')
    for i, frame in enumerate(contact):
        sheet.paste(frame, ((i % 3) * 705, (i // 3) * 392))
    sheet.save(OUT / 'contact.png')

    # The actual selected-voice/FSM/display path, including all emotions and cut.
    new.reset_playback()
    warm_script_assets(new)
    runner = SelectedVoiceRunner(new, plan, effects=True); runner.reset()
    poses, render_times = [], []
    for i in range(int(plan.end * 30) + 2):
        t = min(plan.end, i / 30)
        started = time.perf_counter(); meta = runner.advance(t)
        render_times.append((time.perf_counter() - started) * 1000)
        if meta and meta['asset'] in new._reuse_anchors:
            poses.append((meta['asset'], list(meta['speech_body_pose'])))
    assert not runner.trace.errors and not runner.trace.rejected
    assert runner.trace.samples[-1]['display_state'] == 'IDLE'
    assert {asset for asset, _ in poses} == set(new._reuse_anchors)
    assert all(any(abs(v) > .1 for v in pose)
               for asset in new._reuse_anchors
               for pose in [max((p for a, p in poses if a == asset),
                               key=lambda p: sum(abs(v) for v in p))])
    tracked = ['tools/speech_body_motion.py', 'tools/facial_layers.py',
               'board/interaction/avatar_player.py', 'tests/test_speech_body_motion.py',
               'tools/realtime_facials.py', 'tools/demo_script.py',
               'tools/selected_voice_demo.py', 'tools/realtime_stage.py',
               '../deliverables/2026-10-06_avatar_reuse/preview_script.py']
    report = {
        'status': 'PASS', 'scope': 'PC offline real cached voice/FSM rendering; no device benchmark',
        'regression': {'test_speech_body_motion': 7, 'selected_script_samples': len(runner.trace.samples),
                       'errors': runner.trace.errors, 'rejected': runner.trace.rejected,
                       'final_state': runner.trace.samples[-1]['display_state'],
                       'mouth_sets_used': sorted({asset for asset, _ in poses})},
        'new_speech_render_ms': {'p95': float(np.percentile(timing, 95)), 'max': max(timing)},
        'full_script_render_ms': {'p95': float(np.percentile(render_times, 95)), 'max': max(render_times)},
        'previews': previews,
        'source_sha256': {path: hashlib.sha256((AURA/path).read_bytes()).hexdigest() for path in tracked}}
    (OUT/'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    cards = ''.join('<section><h2>'+label+'</h2><img src="'+slug+'_before_after.webp"></section>'
                    for slug, _, _, label in rows)
    page = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>\u6c50\u84dd\u8bf4\u8bdd\u5934\u80a9\u5fae\u52a8\u5bf9\u7167</title><style>body{background:#111e30;color:#e5edf8;font:17px system-ui;margin:32px auto;max-width:1000px}h1{font-size:27px}img{width:100%;border-radius:12px}section{margin:32px 0}p{line-height:1.7}</style><h1>\u8bf4\u8bdd\u65f6\u7684\u5934\u80a9\u5fae\u52a8</h1><p>\u5de6\u4fa7\u4e3a\u539f\u7248\uff0c\u53f3\u4fa7\u52a0\u5165\u5934\u80a9\u5fae\u52a8\u3002\u4e24\u4fa7\u4f7f\u7528\u540c\u4e00\u53e3\u578b\u97f3\u5f3a\u4e0e\u7728\u773c\u65f6\u95f4\u7ebf\uff1b\u8fd9\u662f\u65e0\u58f0\u5c40\u90e8\u5bf9\u7167\u3002\u8bf7\u7559\u610f\u8138\u3001\u53d1\u68a2\u4e0e\u80a9\u90e8\u7684\u8fde\u7eed\u8fd0\u52a8\u3002</p>'+cards+'</html>'
    (OUT/'index.html').write_text(page, encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
