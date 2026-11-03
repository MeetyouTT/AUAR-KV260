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
import json
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


def render(t, frames, fps, gain, pingpong=False, trim=0, drift=True,
           shot=False, hold=0.0, diffs=None, slowdown=1.0,
           seg=None, loops=1):
    """按播放层口径渲染一帧：取帧（可匀速化/折返/裁尾/稀疏）→ 潜动层（**底边中心**锚定）。

    `diffs`+`slowdown`：**匀速化（最新推荐）** —— 按累积运动量重参数化时间，让循环点速度连续
      （`tools/verify_loop_seam.py` S6 实测：突变比 **0.22 → 1.18**），并可整体放慢；
    `pingpong`：折返（**已否决**：方向反转本身是强视觉事件）；
    `trim`    ：裁掉末尾静止帧数（由 `measure_tail_still()` 实测得出）；
    `shot`+`hold`：稀疏动作（**已否决**：完全静止太假、失去光感自然度）；
    `drift`   ：是否启用既有"去机械化"漂移（做"顿点"对照时关掉，避免混淆变量）。
    """
    n_eff = max(1, len(frames) - trim)
    duration = len(frames) / fps if fps > 0 else 0.0
    if seg is not None:
        tt = at.segment_time(t, seg, fps, loops=loops, slowdown=slowdown)
    elif diffs and slowdown is not None:
        tt = at.warp_time(t, diffs, fps, slowdown=slowdown)
    elif shot and hold > 0.0:
        tt = at.single_shot_time(t, duration, hold)
    elif pingpong:
        tt = at.pingpong_time(t, duration, trim, fps)
    else:
        tt = t
    idx = at.frame_index(at.frame_time(tt, burst=False, phase=0.0, speed=1.0,
                                       drift=drift), n_eff, fps, False)
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


def make_webp(out_path, frames, fps, gain, seconds, out_fps,
              pingpong=False, trim=0, drift=True, shot=False, hold=0.0,
              diffs=None, slowdown=1.0, seg=None, loops=1):
    """动画 WebP（底噪是慢变量，12fps 采样足够；体积与编码时间都可控）。"""
    step = 1.0 / float(out_fps)
    n = max(1, int(round(seconds / step)))
    imgs = [on_bg(render(i * step, frames, fps, gain, pingpong, trim, drift,
                         shot, hold, diffs, slowdown, seg, loops)) for i in range(n)]
    imgs[0].save(str(out_path), save_all=True, append_images=imgs[1:],
                 duration=int(round(1000.0 / out_fps)), loop=0,
                 format="WEBP", quality=88, method=4)
    return n


def make_interrupt_webp(out_path, frames, fps, seg, talk_seconds, blend, out_fps):
    """模拟"保持段中途被打断 → 转退出段"：`blend=True` 时用 150ms 交叉淡化。

    场景刻意取**非整数倍**时刻（`talk_seconds` 不是保持段时长的整数倍），
    复现真实交流：用户插话 / 回复结束 / 状态切换都可能落在保持段中间。
    """
    f = fps
    ne, nl, nx = seg.frames()  # noqa: F841 - 仅用于可读性
    t_enter = at.stage_seconds(seg, f, stage="enter")
    blend_s = at.segment_blend_seconds() if blend else 0.0
    total = talk_seconds + blend_s + at.stage_seconds(seg, f, stage="exit")
    step = 1.0 / float(out_fps)
    imgs = []
    for i in range(max(1, int(round(total / step)))):
        t = i * step
        if t < talk_seconds:                       # 进入段 + 保持段
            if t < t_enter:
                tt = at.segment_at(t, seg, f, stage="enter")
            else:
                tt = at.segment_at(t - t_enter, seg, f, stage="loop")
            imgs.append(on_bg(frames[at.frame_index(tt, len(frames), f, False)]))
        elif blend and t < talk_seconds + blend_s:  # 过渡窗口：交叉淡化
            a = at.segment_at(max(0.0, talk_seconds - t_enter), seg, f, stage="loop")
            b = at.segment_at(0.0, seg, f, stage="exit")
            alpha = (t - talk_seconds) / blend_s
            im_a = on_bg(frames[at.frame_index(a, len(frames), f, False)])
            im_b = on_bg(frames[at.frame_index(b, len(frames), f, False)])
            imgs.append(Image.blend(im_a, im_b, max(0.0, min(1.0, alpha))))
        else:                                       # 退出段
            tt = at.segment_at(t - talk_seconds - blend_s, seg, f, stage="exit")
            imgs.append(on_bg(frames[at.frame_index(tt, len(frames), f, False)]))
    imgs[0].save(str(out_path), save_all=True, append_images=imgs[1:],
                 duration=int(round(1000.0 / out_fps)), loop=0,
                 format="WEBP", quality=88, method=4)
    return len(imgs)


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
/* 三档幅度写死为字面量 keyframes（不用 var/calc —— keyframes 内的 var 兼容性差） */
.breath.k1{animation:breath1 3.7s linear infinite}
.breath.k2{animation:breath2 3.7s linear infinite}
.breath.k4{animation:breath4 3.7s linear infinite}
.sway.k1{animation:sway1 5.3s linear infinite}
.sway.k2{animation:sway2 5.3s linear infinite}
.sway.k4{animation:sway4 5.3s linear infinite}
.tilt.k1{animation:tilt1 6.7s linear infinite}
.tilt.k2{animation:tilt2 6.7s linear infinite}
.tilt.k4{animation:tilt4 6.7s linear infinite}
/* 周期档（只改 duration，幅度不变；r1=旧口径，r2/r3/r4 逐级放慢） */
.breath.r1{animation-duration:3.7s}.breath.r2{animation-duration:5.0s}
.breath.r3{animation-duration:6.0s}.breath.r4{animation-duration:7.4s}
.sway.r1{animation-duration:5.3s}.sway.r2{animation-duration:7.2s}
.sway.r3{animation-duration:8.6s}.sway.r4{animation-duration:10.6s}
.tilt.r1{animation-duration:6.7s}.tilt.r2{animation-duration:9.1s}
.tilt.r3{animation-duration:10.9s}.tilt.r4{animation-duration:13.4s}
@keyframes breath1{0%%,100%%{transform:scaleY(1)}50%%{transform:scaleY(1.006)}}
@keyframes breath2{0%%,100%%{transform:scaleY(1)}50%%{transform:scaleY(1.012)}}
@keyframes breath4{0%%,100%%{transform:scaleY(1)}50%%{transform:scaleY(1.024)}}
@keyframes sway1{0%%,100%%{transform:translateX(0)}25%%{transform:translateX(1.2px)}75%%{transform:translateX(-1.2px)}}
@keyframes sway2{0%%,100%%{transform:translateX(0)}25%%{transform:translateX(2.4px)}75%%{transform:translateX(-2.4px)}}
@keyframes sway4{0%%,100%%{transform:translateX(0)}25%%{transform:translateX(4.8px)}75%%{transform:translateX(-4.8px)}}
@keyframes tilt1{0%%,100%%{transform:rotate(0deg)}50%%{transform:rotate(0.35deg)}}
@keyframes tilt2{0%%,100%%{transform:rotate(0deg)}50%%{transform:rotate(0.7deg)}}
@keyframes tilt4{0%%,100%%{transform:rotate(0deg)}50%%{transform:rotate(1.4deg)}}
</style></head><body>
<h1>AURA 玩偶 · 潜动层（L0）样品</h1>
<p class="sub">素材：<b>%(asset)s</b>（%(frames)d 帧 @%(fps).1f fps，%(loopsec).2f 秒一轮）｜
显示口径 <b>%(dw)d×%(dh)d</b>（与板端一致）｜ 采样 %(outfps)d fps / %(seconds)d 秒<br>
<b>before 与 after 只差"是否叠加潜动层"</b> —— 取帧、变速、drift 完全相同，所以四联可直接对比。</p>
<div class="row">%(cards)s</div>
<h2>循环顿点修复（你反馈的"顿一下"）</h2>
%(seam_block)s
<p class="tip">素材是 i2v 循环素材：<b>首末帧姿态近似相同</b>，且动作曲线"起→高潮→收"（末尾 2 帧静止）
⇒ 正放循环时"末帧→首帧"等于回到起点重来，<b>必然顿一下</b>。
修法两层：<b>① 裁掉末尾静止帧</b> + <b>② 折返播放（乒乓）</b> —— 让动作"做完再收回"，末帧只在折返点出现一次。
这两档<b>都关掉了潜动层与 drift</b>，所以差别只来自"循环方式"本身。</p>
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


def measure_tail_still(frames, threshold=1.0):
    """实测末尾静止帧数 N（与 tools/verify_loop_seam.py 同口径）。

    帧间差 = 人物区（alpha > 100）平均绝对灰度差；从末往前数连续 < threshold 的帧数。
    返回 `(N, 逐帧差表)`。
    """
    import numpy as np
    diffs = []
    for a, b in zip(frames, frames[1:]):
        ga = np.asarray(a, dtype=np.float32)
        gb = np.asarray(b, dtype=np.float32)
        mask = ga[..., 3] > 100
        if not mask.any():
            diffs.append(0.0)
            continue
        da = ga[..., :3].mean(axis=2)
        db = gb[..., :3].mean(axis=2)
        diffs.append(float(np.abs(da - db)[mask].mean()))
    n = 0
    for d in reversed(diffs):
        if d < threshold:
            n += 1
        else:
            break
    return n, diffs


def build_seam_block(trim, seg_seconds, fps, frames_n, tail_n, mean_diff, loop_gap):
    """循环顿点区块：现状（正放循环） vs 折返（乒乓 + 裁尾）。"""
    loops = seg_seconds / (frames_n / fps) if fps > 0 else 0.0
    span = 2.0 * (frames_n - trim - 1) / fps if fps > 0 else 0.0
    cycle = (frames_n / fps if fps > 0 else 0.0) + at.LOOP_HOLD_SECONDS
    return ('<div class="row">'
            '<div class="card"><h3>① 现状：正放循环</h3>'
            '<img src="pp_before.webp" alt="pp_before">'
            '<p class="note">末帧近似回到首帧（差 %.2f ／ 平均帧间差 %.2f = 比值 %.2f），'
            '且末尾 <b>%d 帧静止</b> → 每轮结束"顿一下"（%d 秒里约 %.1f 次）</p></div>'
            '<div class="card"><h3>② 折返（乒乓 + 裁尾 %d 帧）· 已被否决</h3>'
            '<img src="pp_after.webp" alt="pp_after">'
            '<p class="note"><b>用户实测否决</b>：折返让速度大小连续（一个来回 %.3f 秒），'
            '但"方向反转"本身就是强视觉事件 → 照样能看出"循环结束"。<br>'
            '顺带确认：<b>顿的物理本质是速度突变</b>（末段 ≈0.75 ／ 首段 ≈3.17 灰阶每帧，差 4 倍）。</p></div>'
            '<div class="card"><h3>③ 稀疏动作（已否决：静止太假）</h3>'
            '<img src="shot_hold.webp" alt="shot_hold">'
            '<p class="note">播一次 + 静止保持 3 秒、周期 %.3f 秒 —— 循环点虽然"逐像素相同"，'
            '但<b>完全静止让画面像卡住、失去光感自然度</b> ⇒ 实测否决。</p></div>'
            '<div class="card"><h3>④ 匀速化 + 放慢 1.5 倍（<b>最新推荐</b>）</h3>'
            '<img src="warp.webp" alt="warp">'
            '<p class="note">按<b>累积运动量</b>匀速推进时间：低速段加速通过、高速段放慢，'
            '循环点<b>速度突变比 0.22 → 1.18</b>（≈1 = 连续）⇒ 看不出"一次循环结束"；'
            '全程<b>持续运动</b>、不静止；同时整体放慢 1.5 倍（配合潜动层周期 8 s）。</p></div>'
            '</div>'
            % (loop_gap, mean_diff, loop_gap / mean_diff if mean_diff else 0.0,
               tail_n, int(seg_seconds), loops, trim, span, cycle))


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
    # 周期档：用户实测"想放慢呼吸" → 放慢只降**变化率**，幅度固定不变
    per = (("r1", 3.7, "旧口径 3.7s（≈16 次/分）"),
           ("r2", 5.0, "5.0s（≈12 次/分）"),
           ("r3", 6.0, "<b>新默认 6.0s（≈10 次/分）</b>"),
           ("r4", 7.4, "7.4s（≈8 次/分）"))
    per_cards = []
    for key, sec, label in per:
        rate = DISPLAY_H * at.IDLE_BREATH_AMP * 2.0 * 3.14159265 / sec / 24.0
        per_cards.append(
            '<div class="card"><h3>呼吸 %s</h3><div class="stage">'
            '<div class="layer sway %s"><div class="layer tilt %s"><div class="layer breath %s">'
            '<img class="base" src="still_base.png" alt="%s"></div></div></div></div>'
            '<p class="note">%s<br>幅度固定 ±%.2f px，每帧变化 <b>%.3f px</b></p></div>'
            % (key, key, key, key, key, label,
               DISPLAY_H * at.IDLE_BREATH_AMP, rate))
    # 10 秒说话：现状（整段往复） vs 三段式（抬手 → 空中保持 ×N → 放下）
    talk_cards = []
    for key, label, note in (
            ("talk_before", "现状：整段往复循环",
             "说话 10 秒 = 抬手放下重复约 6 次 → 极不自然"),
            ("talk_after", "三段式：抬手 → 空中保持 ×N → 放下",
             "手一直停在空中、只做小幅自然动；说完才放下 → 自然")):
        talk_cards.append(
            '<div class="card"><h3>%s</h3><img src="%s.webp" alt="%s">'
            '<p class="note">%s</p></div>' % (label, key, key, note))
    # 打断衔接：话说到 3.7 秒被打断（非整数倍时刻）→ 硬切 vs 150ms 交叉淡化
    cut_cards = []
    for key, label, note in (
            ("cut_hard", "硬切（未做衔接）",
             "保持段被打断 → 直接跳退出段首帧：会看到一次明显跳变"),
            ("cut_blend", "150ms 交叉淡化（推荐）",
             "同样被打断，但在 150ms 内淡到退出段 → 过渡连续、看不出切换")):
        cut_cards.append(
            '<div class="card"><h3>%s</h3><img src="%s.webp" alt="%s">'
            '<p class="note">%s</p></div>' % (label, key, key, note))
    return ('<div class="row">%s</div>'
            '<h3 style="margin:24px 0 8px;font-size:15px">'
            '呼吸快慢对比（<b>幅度相同</b>，只改周期；"每帧变化"越小越舒缓）</h3>'
            '<div class="row">%s</div>'
            '<h3 style="margin:24px 0 8px;font-size:15px">'
            '说话 10 秒（talking_normal）：<b>现状</b> vs <b>三段式</b></h3>'
            '<div class="row">%s</div>'
            '<h3 style="margin:24px 0 8px;font-size:15px">'
            '打断衔接（话说到 <b>3.7 秒</b>被打断 —— 刻意取非整数倍时刻）</h3>'
            '<div class="row">%s</div>'
            % ("".join(cards), "".join(per_cards), "".join(talk_cards),
               "".join(cut_cards)))


def build_html(asset, fps, frames_n, counts, still_name, rows, svg, out_fps, seconds,
               css_block="", seam_block=""):
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
        "seam_block": seam_block,
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

    # 循环顿点对照：两档都关掉潜动层与 drift，只对比"循环方式"本身
    tail_n, diffs = measure_tail_still(frames)
    mean_diff = sum(diffs) / len(diffs) if diffs else 0.0
    ends = measure_tail_still([frames[-1], frames[0]])[1]
    loop_gap = ends[0] if ends else 0.0
    pp_seconds = 9.0
    print("实测：末尾静止 %d 帧 ／ 平均帧间差 %.2f ／ 首末帧差 %.2f（比值 %.2f）"
          % (tail_n, mean_diff, loop_gap, loop_gap / mean_diff if mean_diff else 0.0))
    for key, pingpong in (("pp_before", False), ("pp_after", True)):
        out = OUTDIR / (key + ".webp")
        if out.exists() and not args.force:
            counts[key] = int(round(pp_seconds * fps))
            print("  [webp] %-8s %-14s 已存在，跳过（--force 重建）" % (key, out.name))
            continue
        # 顿点对照片用**素材原生帧率**：折返点附近是低速段（约 0.75 灰阶/帧），
        # 若按 12fps 采样会把低速段整段丢掉、**人为放大"顿"** → 必须逐帧出片才真实。
        counts[key] = make_webp(out, frames, fps, 0.0, pp_seconds, fps,
                                pingpong=pingpong,
                                trim=(tail_n if pingpong else 0), drift=False)
        print("  [webp] %-8s %-14s %3d 帧  %.2f MB"
              % (key, out.name, counts[key], out.stat().st_size / 1048576.0))

    # 稀疏动作档（推荐方案）：素材播一次 + 保持 3 秒；循环点落在静止段内 ⇒ 差 = 0.0
    cycle = len(frames) / fps + at.LOOP_HOLD_SECONDS
    shot_seconds = round(cycle * 2.0, 3)      # 恰好 2 个周期（循环点落在周期边界上）
    out_shot = OUTDIR / "shot_hold.webp"
    if out_shot.exists() and not args.force:
        counts["shot_hold"] = int(round(shot_seconds * fps))
        print("  [webp] %-8s %-14s 已存在，跳过（--force 重建）"
              % ("shot_hold", out_shot.name))
    else:
        counts["shot_hold"] = make_webp(out_shot, frames, fps, 0.0, shot_seconds, fps,
                                        shot=True, hold=at.LOOP_HOLD_SECONDS,
                                        drift=False)
        print("  [webp] %-8s %-14s %3d 帧  %.2f MB"
              % ("shot_hold", out_shot.name, counts["shot_hold"],
                 out_shot.stat().st_size / 1048576.0))

    # 匀速化档（**最新推荐**）：按运动量匀速推进 + 整体放慢 1.5 倍；循环点速度连续、全程不静止
    slow = 1.5
    warp_seconds = round((len(frames) / fps) * slow * 4.0, 3)   # 4 个周期（循环点落在周期边界）
    out_warp = OUTDIR / "warp.webp"
    if out_warp.exists() and not args.force:
        counts["warp"] = int(round(warp_seconds * fps))
        print("  [webp] %-8s %-14s 已存在，跳过（--force 重建）" % ("warp", out_warp.name))
    else:
        counts["warp"] = make_webp(out_warp, frames, fps, 0.0, warp_seconds, fps,
                                   diffs=diffs, slowdown=slow, drift=False)
        print("  [webp] %-8s %-14s %3d 帧  %.2f MB"
              % ("warp", out_warp.name, counts["warp"],
                 out_warp.stat().st_size / 1048576.0))

    # 三段式演示（模拟 10 秒说话）：① 现状（全段往复循环）② enter 一次 → loop×N → exit 一次
    talk_name = "talking_normal"
    talk_seg = None
    talk_frames = None
    talk_fps = fps
    if aa.list_frames(aa.asset_dir(talk_name)):
        seg_path = aa.asset_dir(talk_name) / "segments.json"
        if seg_path.is_file():
            try:
                talk_seg = at.segments_from_dict(
                    json.loads(seg_path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                talk_seg = None
        if talk_seg is not None:
            talk_frames, talk_fps = load_frames(talk_name)
    if talk_frames is not None:
        talk_seconds = 10.0
        n_loops = at.loops_for_duration(talk_seconds, talk_seg, talk_fps)
        print("三段式（%s）：enter %s ／ loop %s ／ exit %s → 10 秒说话循环 %d 次"
              % (talk_name, talk_seg.enter, talk_seg.loop, talk_seg.exit, n_loops))
        for key, use_seg in (("talk_before", False), ("talk_after", True)):
            out_talk = OUTDIR / (key + ".webp")
            if out_talk.exists() and not args.force:
                counts[key] = int(round(talk_seconds * talk_fps))
                print("  [webp] %-11s %-14s 已存在，跳过（--force 重建）"
                      % (key, out_talk.name))
                continue
            counts[key] = make_webp(
                out_talk, talk_frames, talk_fps, 0.0, talk_seconds, talk_fps,
                seg=(talk_seg if use_seg else None),
                loops=(n_loops if use_seg else 1),
                slowdown=(at.LOOP_SLOWDOWN if use_seg else 1.0), drift=False)
            print("  [webp] %-11s %-14s %3d 帧  %.2f MB"
                  % (key, out_talk.name, counts[key],
                     out_talk.stat().st_size / 1048576.0))

    if talk_frames is not None:
        # 打断演示：话说到 3.7 秒被打断（**非整数倍**）→ 硬切 vs 150ms 交叉淡化
        interrupt_seconds = 3.7
        for key, do_blend in (("cut_hard", False), ("cut_blend", True)):
            out_cut = OUTDIR / (key + ".webp")
            if out_cut.exists() and not args.force:
                counts[key] = 0
                print("  [webp] %-11s %-14s 已存在，跳过（--force 重建）"
                      % (key, out_cut.name))
                continue
            counts[key] = make_interrupt_webp(out_cut, talk_frames, talk_fps,
                                              talk_seg, interrupt_seconds, do_blend,
                                              talk_fps)
            print("  [webp] %-11s %-14s %3d 帧  %.2f MB"
                  % (key, out_cut.name, counts[key],
                     out_cut.stat().st_size / 1048576.0))

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
                               build_css_block(),
                               build_seam_block(tail_n, pp_seconds, fps,
                                                len(frames), tail_n,
                                                mean_diff, loop_gap)),
                    encoding="utf-8")
    print("页面：%s" % page)
    return 0


if __name__ == "__main__":
    sys.exit(main())

