# -*- coding: utf-8 -*-
"""潜动层（L0）样品出片：现状 vs 加"活着"的微动（PIL，无 Qt）。

产物（docs/demo_alive/）：
    index.html        四联并排播放 + 静态差异图 + 底噪轨迹 + 数值表
    before.webp       现状：仅素材自身动作（含既有 drift 去机械化，与生产逐字一致）
    x1.webp           潜动层 ×1（设计值：呼吸 ±0.6% / 重心 ±1.2px / 微摆 0.35°）
    x2.webp / x4.webp 幅度放大档（用于肉眼判断"够不够 / 过不过头"）
    still_compare.png 呼气谷 | 吸气峰 | 差值×8（呼吸纵向差 ≈2.6px）

用法：
    "<AURA>\\.venv\\Scripts\\python.exe" -s tools\\make_alive_sample.py [--asset idle_normal]

口径：取帧与变换**全部调用 board/interaction/avatar_timing**（播放层同一份），
     故样品 = 未来真机效果的逐字预览；before 与 after 只差"是否叠加潜动层"。
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from board.interaction import avatar_assets as aa    # noqa: E402
from board.interaction import avatar_timing as at    # noqa: E402

OUTDIR = ROOT / "docs" / "demo_alive"
DISPLAY_W, DISPLAY_H = 423, 436      # 合同显示尺寸（PC 与板端一致）
PAD = 10                             # 画布留白：给位移/旋转留余量
GAINS = (1.0, 2.0, 4.0)
BG = (250, 248, 244)                 # 底色（米白，与演示台面板同色系）


def load_frames(name):
    """读素材帧（RGBA，缩到显示尺寸）→ (帧表, fps)。"""
    directory = aa.asset_dir(name)
    paths = aa.list_frames(directory)
    if not paths:
        raise SystemExit("素材缺失：%s" % directory)
    frames = [Image.open(p).convert("RGBA").resize((DISPLAY_W, DISPLAY_H),
                                                   Image.LANCZOS) for p in paths]
    return frames, aa.frames_fps(directory)


def render(t, frames, fps, gain):
    """按播放层口径渲染一帧：取帧（含 drift）→ 潜动层（**底边中心**锚定）。"""
    idx = at.frame_index(at.frame_time(t, burst=False, phase=0.0, speed=1.0),
                         len(frames), fps, False)
    off = at.idle_offsets(t, gain=gain)
    new_h = max(2, int(round(DISPLAY_H * off.scale_y)))
    img = frames[idx]
    if new_h != DISPLAY_H:
        img = img.resize((DISPLAY_W, new_h), Image.LANCZOS)
    canvas = Image.new("RGBA", (DISPLAY_W + 2 * PAD, DISPLAY_H + 2 * PAD), (0, 0, 0, 0))
    cx = canvas.width // 2 + int(round(off.dx))
    bottom = canvas.height - PAD - int(round(off.dy))
    canvas.alpha_composite(img, (max(0, cx - DISPLAY_W // 2), max(0, bottom - new_h)))
    if abs(off.tilt_deg) > 1e-6:
        canvas = canvas.rotate(off.tilt_deg, resample=Image.BICUBIC,
                               center=(cx, bottom), fillcolor=(0, 0, 0, 0))
    return canvas


def on_bg(img):
    """透明帧合成到底色（页面观感即真机"玩偶叠在面板上"）。"""
    bg = Image.new("RGB", img.size, BG)
    bg.paste(img, (0, 0), img)
    return bg


def make_webp(out_path, frames, fps, gain, seconds, out_fps):
    """动画 WebP（底噪是慢变量，12fps 采样足够；体积与编码时间都可控）。"""
    step = 1.0 / float(out_fps)
    n = max(1, int(round(seconds / step)))
    imgs = [on_bg(render(i * step, frames, fps, gain)) for i in range(n)]
    imgs[0].save(str(out_path), save_all=True, append_images=imgs[1:],
                 duration=int(round(1000.0 / out_fps)), loop=0,
                 format="WEBP", quality=88, method=4)
    return n


def make_still(out_path, frames, fps):
    """静态三栏：呼气谷 | 吸气峰 | 差值×8 —— 用像素证明"确实在动、动多少"。"""
    lo = on_bg(render(0.0, frames, fps, 1.0))
    hi = on_bg(render(at.IDLE_BREATH_PERIOD / 2.0, frames, fps, 1.0))
    diff = ImageChops.difference(lo, hi).convert("L").point(lambda v: min(255, v * 8))
    gap = 12
    sheet = Image.new("RGB", (lo.width * 3 + gap * 2, lo.height), BG)
    for i, im in enumerate((lo, hi, diff.convert("RGB"))):
        sheet.paste(im, (i * (lo.width + gap), 0))
    sheet.save(str(out_path))
    return out_path


def wave_svg(seconds=60.0, samples=600, w=900, h=240):
    """底噪轨迹（内嵌 SVG）：三条曲线各自归一化 → 直接看出"周期不同、整体不重复"。"""
    step = seconds / float(samples)
    series = ([], [], [])
    for i in range(samples + 1):
        off = at.idle_offsets(i * step)
        series[0].append((off.scale_y - 1.0) * DISPLAY_H)
        series[1].append(off.dx)
        series[2].append(off.tilt_deg * 3.14159265 / 180.0 * DISPLAY_H * 0.5)
    names = ("呼吸·纵向 px", "重心·横向 px", "微摆·端点 px")
    colors = ("#2b6cb0", "#c05621", "#2f855a")
    out = ['<svg viewBox="0 0 %d %d" width="100%%" xmlns="http://www.w3.org/2000/svg">'
           % (w, h), '<rect width="%d" height="%d" fill="#faf8f4"/>' % (w, h)]
    for k in range(3):
        vals = series[k]
        peak = max(abs(v) for v in vals) or 1.0
        pts = ["%.1f,%.1f" % (10 + (w - 20) * i / float(len(vals) - 1),
                              h / 2.0 - (v / peak) * (h / 2.0 - 34))
               for i, v in enumerate(vals)]
        out.append('<polyline fill="none" stroke="%s" stroke-width="1.6" points="%s"/>'
                   % (colors[k], " ".join(pts)))
        out.append('<text x="14" y="%d" font-size="13" fill="%s">%s（峰值 %.2f）</text>'
                   % (20 + k * 18, colors[k], names[k], peak))
    out.append('<text x="14" y="%d" font-size="12" fill="#666">'
               '横轴 0~%.0fs，各曲线按自身峰值归一化</text>' % (h - 8, seconds))
    out.append("</svg>")
    return "".join(out)


def px_dist(a, b):
    """两个姿态的显示距离（像素）：位移直接算，缩放/旋转折算成像素。"""
    return (abs(a.dx - b.dx) + abs(a.dy - b.dy)
            + abs(a.scale_y - b.scale_y) * DISPLAY_H
            + abs(a.tilt_deg - b.tilt_deg) * 3.14159265 / 180.0 * DISPLAY_H * 0.5)


def idle_metrics():
    """样品页要展示的关键读数（与 tools/verify_idle_alive.py 同口径同算式）。"""
    offs = [at.idle_offsets(i / 24.0) for i in range(60 * 24 + 1)]
    worst = max(px_dist(a, b) for a, b in zip(offs, offs[1:]))
    gaps = [px_dist(at.idle_offsets(i * 0.25), at.idle_offsets(i * 0.25 + 200.0))
            for i in range(240)]
    return worst, min(gaps)


TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>AURA 潜动层（L0）样品</title>
<style>
body{font-family:"Microsoft YaHei",sans-serif;background:#faf8f4;color:#222;margin:0;padding:24px}
h1{font-size:22px;margin:0 0 8px}h2{font-size:17px;margin:28px 0 10px}
.sub{color:#666;font-size:13px;margin:0 0 18px;line-height:1.8}
.row{display:flex;gap:14px;flex-wrap:wrap}
.card{background:#fff;border:1px solid #e6e2da;border-radius:8px;padding:10px;width:236px}
.card h3{font-size:14px;margin:0 0 6px}.card img{width:100%%;display:block;border-radius:4px}
.note{font-size:12px;color:#666;margin:6px 0 0;line-height:1.5}
table{border-collapse:collapse;font-size:13px;background:#fff;max-width:820px;width:100%%}
td{border:1px solid #e6e2da;padding:5px 10px}td:first-child{color:#555;width:42%%}
.wrap{background:#fff;border:1px solid #e6e2da;border-radius:8px;padding:10px;max-width:1120px}
.tip{font-size:13px;color:#333;background:#fff7e6;border-left:3px solid #f0b429;
padding:10px 12px;border-radius:4px;max-width:820px;line-height:1.8}
.tip{font-size:13px;color:#333;background:#fff7e6;border-left:3px solid #f0b429;
padding:10px 12px;border-radius:4px;max-width:820px;line-height:1.8}
.stage{position:relative;width:423px;height:436px;background:#f2efe8;border-radius:6px;overflow:hidden;
background-image:linear-gradient(#e4e0d6 1px,transparent 1px),linear-gradient(90deg,#e4e0d6 1px,transparent 1px);
background-size:42px 44px}
.stage img.base{position:absolute;left:0;top:0;width:423px;height:436px}
.layer{position:absolute;left:0;top:0;width:423px;height:436px;transform-origin:50%% 100%%}
.k1{--k:1}.k2{--k:2}.k4{--k:4}
.breath{animation:breath-anim 3.7s linear infinite}
.sway{animation:sway-anim 5.3s linear infinite}
.tilt{animation:tilt-anim 6.7s linear infinite}
@keyframes breath-anim{0%%,100%%{transform:scaleY(1)}50%%{transform:scaleY(calc(1 + 0.006 * var(--k)))}}
@keyframes sway-anim{0%%,100%%{transform:translateX(0)}25%%{transform:translateX(calc(1.2px * var(--k)))}75%%{transform:translateX(calc(-1.2px * var(--k)))}}
@keyframes tilt-anim{0%%,100%%{transform:rotate(0deg)}50%%{transform:rotate(calc(0.35deg * var(--k)))}}
</style></head><body>
<h1>AURA 玩偶 · 潜动层（L0）样品</h1>
<p class="sub">素材：<b>%(asset)s</b>（%(frames)d 帧 @%(fps).1f fps，%(loopsec).2f 秒一轮）｜
显示口径 <b>%(dw)d×%(dh)d</b>（与板端一致）｜ 采样 %(outfps)d fps / %(seconds)d 秒<br>
<b>before 与 after 只差"是否叠加潜动层"</b> —— 取帧、变速、drift 完全相同，所以四联可直接对比。</p>
<div class="row">%(cards)s</div>
<h2>无缝对比（推荐先看这个：无循环接缝，可以一直盯着看）</h2>
%(css_block)s
<p class="tip">这一区块的底图是<b>素材的时间中位帧（完全静止）</b>，所以看到的差别<b>只来自潜动层</b>；
带网格背景是为了让位移更好辨认。<b>动画 WebP 那一组每轮都有接缝</b>（潜动层的复合周期是 133 分钟，
12 秒的动画首尾在数学上接不上），看连续"呼吸感"请以本区块为准。</p>
<h2>静态证据：呼气谷 → 吸气峰（差值放大 8×）</h2>
<div class="wrap"><img src="%(still)s" style="width:100%%"></div>
<h2>底噪轨迹（60 秒；四个通道周期互质 → 复合周期 ≈ %(period).0f 秒 ≈ %(periodmin).0f 分钟）</h2>
<div class="wrap">%(svg)s</div>
<h2>数值（tools/verify_idle_alive.py：RESULT: OK，0 项失败）</h2>
<table>%(table)s</table>
<h2>三个档怎么看</h2>
<p class="tip">
<b>×1</b> = 设计值（目标：能"感觉到在呼吸"，但说不出具体哪里在动）<br>
<b>×2</b> = 明显一档（若觉得 ×1 太弱就选它）<br>
<b>×4</b> = 夸张档（一定过头，用来对照"过了"是什么样）<br>
放大档<b>只为选幅度</b>，生产恒为 ×1；选定后我把 gain 固化进常量即可。<br>
若三档都"看不出差别"，说明瓶颈不在幅度而在<b>素材本身</b>（待机族 5 个素材彼此差 &lt;1.5 灰阶）
—— 那就该进入第 3 波：重制待机族素材（姿态差异化 + 降幅）。
</p>
</body></html>"""


def make_still_base(out_path, frames):
    """静止底图：素材的**时间中位帧**（把"素材自身的动作"完全冻结）。

    用途：CSS 无缝页里只保留潜动层 → 用户看到的差别**只来自呼吸/重心/微摆**，
    彻底排除"素材自身动作"与"动画循环接缝"两个干扰源。
    """
    on_bg(frames[len(frames) // 2]).save(str(out_path))
    return out_path


def build_css_block():
    """无缝对比区块：静止底图 + 三层 CSS 动画（呼吸 / 重心 / 微摆）。

    为什么用 CSS 而不是动画图（本轮踩坑后的结论）：
      · 潜动层本质就是 transform → CSS keyframes 可以**逐字实现**，且**永不间断、无循环接缝**；
      · 叠三层 div（各挂一个 animation）是必需的 —— 同一元素上的多条 animation 会**互相覆盖**
        `transform`，必须分层；
      · WebP/GIF 动画每播完一轮都有接缝，而潜动层复合周期 133 分钟 ⇒ **首尾在数学上不可能接上**
        （t=0 为中性位、t=12s 已偏 1.19px）→ 用动画图看会误判成"停顿"。
    """
    cards = ['<div class="card"><h3>现状（完全静止）</h3>'
             '<div class="stage"><img class="base" src="still_base.png" alt="base"></div>'
             '<p class="note">没有任何微动 —— 这才是"贴图"的样子</p></div>']
    for gain in GAINS:
        key = "x%g" % gain
        cards.append(
            '<div class="card"><h3>潜动层 %s</h3><div class="stage">'
            '<div class="layer sway %s"><div class="layer tilt %s"><div class="layer breath %s">'
            '<img class="base" src="still_base.png" alt="%s"></div></div></div></div>'
            '<p class="note">呼吸 ±%.2fpx ／ 重心 ±%.1fpx ／ 微摆 %.2f°（无缝循环）</p></div>'
            % (key, key, key, key, key, DISPLAY_H * at.IDLE_BREATH_AMP * gain,
               at.IDLE_SWAY_AMP_X * gain, at.IDLE_TILT_AMP_DEG * gain))
    return '<div class="row">%s</div>' % "".join(cards)


def build_html(asset, fps, frames_n, counts, still_name, rows, svg, out_fps, seconds,
               css_block=""):
    cards = ['<div class="card"><h3>现状（无潜动层）</h3>'
             '<img src="before.webp" alt="before">'
             '<p class="note">只有素材自身动作；几何上仍会回到同一姿态（%d 帧）</p></div>'
             % counts["before"]]
    for gain in GAINS:
        key = "x%g" % gain
        cards.append(
            '<div class="card"><h3>潜动层 %s</h3><img src="%s.webp" alt="%s">'
            '<p class="note">呼吸 ±%.2fpx ／ 重心 ±%.1fpx ／ 微摆 %.2f°（%d 帧）</p></div>'
            % (key, key, key, DISPLAY_H * at.IDLE_BREATH_AMP * gain,
               at.IDLE_SWAY_AMP_X * gain, at.IDLE_TILT_AMP_DEG * gain, counts[key]))
    return TEMPLATE % {
        "asset": asset, "frames": frames_n, "fps": fps,
        "loopsec": frames_n / fps if fps > 0 else 0.0,
        "dw": DISPLAY_W, "dh": DISPLAY_H, "outfps": int(out_fps),
        "seconds": int(seconds), "cards": "".join(cards),
        "still": still_name, "svg": svg,
        "period": at.idle_composite_period(),
        "periodmin": at.idle_composite_period() / 60.0,
        "table": "".join("<tr><td>%s</td><td>%s</td></tr>" % kv for kv in rows),
        "css_block": css_block,
    }


def main():
    ap = argparse.ArgumentParser(description="潜动层（L0）样品出片")
    ap.add_argument("--asset", default="idle_normal", help="素材名（默认待机）")
    ap.add_argument("--seconds", type=float, default=12.0, help="动画时长（秒）")
    ap.add_argument("--fps", type=float, default=12.0, help="出片采样帧率")
    ap.add_argument("--force", action="store_true", help="强制重建动画 WebP（默认跳过已存在的）")
    args = ap.parse_args()

    frames, fps = load_frames(args.asset)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    print("素材 %s：%d 帧 @%.1f fps → 显示 %d×%d"
          % (args.asset, len(frames), fps, DISPLAY_W, DISPLAY_H))

    counts = {}
    for key, gain in [("before", 0.0)] + [("x%g" % g, g) for g in GAINS]:
        out = OUTDIR / (key + ".webp")
        if out.exists() and not args.force:
            counts[key] = int(round(args.seconds * args.fps))
            print("  [webp] %-8s %-14s 已存在，跳过（--force 重建）" % (key, out.name))
            continue
        counts[key] = make_webp(out, frames, fps, gain, args.seconds, args.fps)
        print("  [webp] %-8s %-14s %3d 帧  %.2f MB"
              % (key, out.name, counts[key], out.stat().st_size / 1048576.0))

    still = make_still(OUTDIR / "still_compare.png", frames, fps)
    print("  [png ] %-14s %.2f MB" % (still.name, still.stat().st_size / 1048576.0))

    worst_frame, min_gap = idle_metrics()
    period = at.idle_composite_period()
    tip_px = at.IDLE_TILT_AMP_DEG * 3.14159265 / 180.0 * DISPLAY_H * 0.5
    rows = [
        ("呼吸·纵向起伏（显示像素）", "%.2f px　（设计 2~4px：看得见、但不像抖）"
         % (DISPLAY_H * at.IDLE_BREATH_AMP)),
        ("重心·水平摆动（显示像素）", "±%.1f px" % at.IDLE_SWAY_AMP_X),
        ("重心·下沉（显示像素）", "%.2f px" % at.IDLE_SWAY_AMP_Y),
        ("微摆·端点位移", "%.2f px（%.2f°）" % (tip_px, at.IDLE_TILT_AMP_DEG)),
        ("24fps 最大帧间变化", "%.4f px（亚像素 → 平滑、不抖）" % worst_frame),
        ("复合周期（四通道互质）", "%.0f s ≈ %.1f 分钟" % (period, period / 60.0)),
        ("t 与 t+200s 最小姿态距离", "%.3f px（>0 → 200 秒内不重复）" % min_gap),
        ("进场中性位", "t≤0 / gain=0 → 位移 0、缩放 1.0（不跳变、可一键关闭）"),
        ("素材总体位移（前提复核）", "帧间 shift = 0,0（体检 v3 实测）→ 叠加不打架"),
    ]
    base = make_still_base(OUTDIR / "still_base.png", frames)
    print("  [png ] %-14s %.2f MB" % (base.name, base.stat().st_size / 1048576.0))

    page = OUTDIR / "index.html"
    page.write_text(build_html(args.asset, fps, len(frames), counts, still.name,
                               rows, wave_svg(), args.fps, args.seconds,
                               build_css_block()),
                    encoding="utf-8")
    print("页面：%s" % page)
    return 0


if __name__ == "__main__":
    sys.exit(main())

