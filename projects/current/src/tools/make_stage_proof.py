# -*- coding: utf-8 -*-
"""阶段机**可视化证据**：把 `enter / loop / blend / exit` 各阶段的代表帧拼成一张图。

为什么需要：阶段机（#5）是**时间行为**，光看代码或数值不直观。这张图让
"说完 / 被打断 → 平滑收起"**一眼可见**（尤其 `blend` 段能看到"保持段姿态**淡入**退出段"的中间态，
这是"无跳变"的直接证据）。

用法：
    "<AURA>\\.venv\\Scripts\\python.exe" -s tools\\make_stage_proof.py
产物：
    docs\\demo_stage\\stage_machine_proof.png（每格标注：阶段 / 时间 / a·b 帧号 / alpha）
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))
sys.path.insert(0, str(AURA / "tools"))                # tools 不是包 → 按目录导入

from board.interaction import avatar_assets as aa       # noqa: E402
from board.interaction import avatar_timing as at       # noqa: E402
from demo_stage import StageCore                        # noqa: E402

ASSET = "talking_neutral"
OUT = AURA / "docs" / "demo_stage" / "stage_machine_proof.png"
STATE = "SPEAKING_NEUTRAL"
#: (标签, 时间点秒, 是否在此刻请求退出)
#  前 4 格展示**多窗口轮换**（每个"来回"换一个窗口 ⇒ 说话不再"同一个动作反复晃"）；
#  后 4 格展示"说完 / 被打断 → blend → exit"（与 `tools/verify_segment_exit.py` 的读数对应）。
SHOTS = (
    ("第1来回（窗口A）", 0.9, False),
    ("第2来回（窗口B）", 2.7, False),
    ("第3来回（窗口C）", 4.5, False),
    ("第4来回（回到 A）", 6.3, False),
    ("【请求退出】此刻", 6.9, True),
    ("blend α≈0.3", 6.95, False),
    ("blend α≈0.7", 7.00, False),
    ("exit 末（停住）", 8.00, False),
)


def main():
    directory = aa.asset_dir(ASSET)
    paths = aa.list_frames(directory)
    if not paths:
        raise SystemExit("素材缺失：%s" % directory)
    frames = [Image.open(p).convert("RGBA") for p in paths]
    fps = aa.frames_fps(directory)
    seg = at.segments_from_dict(aa.read_segments(directory) or {})
    if seg is None:
        raise SystemExit("缺 segments.json：%s（先跑 split_avatar_segments.py --write）" % directory)

    core = StageCore()
    tiles = []
    for label, t, request in SHOTS:
        if request:
            core.request_exit()
        ta, tb, alpha = core.segment_stage_time(STATE, seg, fps, 0.0, t)
        ia = at.frame_index(ta, len(frames), fps, False)
        img = frames[ia].copy()
        note = "f%d" % ia
        if tb is not None and alpha > 0.0:
            ib = at.frame_index(tb, len(frames), fps, False)
            other = frames[ib]
            if other.size == img.size:
                img = Image.blend(img, other, alpha)
            note = "f%d→f%d α=%.2f" % (ia, ib, alpha)
        stage = core.stage_state()[0]
        tiles.append(("t=%.2fs｜%s｜%s｜%s" % (t, stage, label, note), img))

    # 拼图（4 列）
    w, h = tiles[0][1].size
    cap = 18
    cols = 4
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * (h + cap)), (24, 27, 32))
    draw = ImageDraw.Draw(sheet)
    for i, (text, img) in enumerate(tiles):
        cx, cy = (i % cols) * w, (i // cols) * (h + cap)
        bg = Image.new("RGB", img.size, (250, 248, 244))
        bg.paste(img, (0, 0), img)
        sheet.paste(bg, (cx, cy))
        draw.text((cx + 4, cy + h + 2), text, fill=(210, 214, 220))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(OUT))
    print("阶段机证据图：%s（%d 格，%dx%d）" % (OUT, len(tiles), sheet.width, sheet.height))
    return 0


if __name__ == "__main__":
    sys.exit(main())
