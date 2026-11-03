"""make_demo_viewer.py —— 把演示产物打包成「**双击即看**」的单文件 HTML。

用途
----
`evidence_shots/demo24/` 里已有 313 帧 PNG + GIF + MP4，但：
  ① 帧目录要点开 313 个文件；② GIF 6.4 MB 且被合并成 135 帧 / 256 色；
  ③ **MP4 是 cv2 写的 `mp4v`（MPEG-4 Part 2），浏览器 `<video>` 基本不能播**
    （实测本机 cv2 也无法写 H.264：缺 openh264-2.5.0-win64.dll）。
本工具把它们**打包成一个自包含 HTML**：视频以 base64 内嵌、关键帧缩略内嵌、
剧本时间轴自动推导、校验结论写在页面上 —— 双击就能看，也能单独发给别人。

视频兼容性策略（`--embed`）
--------------------------
`auto`（默认）会把 cv2 的 mp4v 转成 **两种编码同时内嵌**，写进同一个 `<video>` 的多个
`<source>`，浏览器自动挑第一个能播的 —— 这是「一处兜底、哪个浏览器都能看」的关键：
  1. **H.264 / MP4**（`libx264` / yuv420p / `+faststart`）→ `demo_scenario_h264.mp4`：
     Safari / Edge / Chrome / Firefox 通吃，压缩率最好。
  2. **VP9 / WebM**（`libvpx-vp9`，**开放编码**，不依赖任何专有解码器）→ `demo_scenario_vp9.webm`：
     连**未编译 H.264 解码器**的 Chromium 构建（如部分 PySide6 QtWebEngine）也能播。
     ← 实测踩坑：只嵌 H.264 时 QtWebEngine 报
     `DEMUXER_ERROR_NO_SUPPORTED_STREAMS`（该构建无专有解码器）→ 页面黑屏。
  3. 两种都失败 → 退回**内嵌 GIF**（100% 兼容，但体积大、色深差、帧被合并）。
其它取值：`h264` / `webm` 只要一种；`gif` 只嵌 GIF；`both` 视频与 GIF 都嵌。
ffmpeg 优先用 `imageio-ffmpeg` 自带的（免安装），其次 `PATH` 上的；
**原 `demo_scenario.mp4` 永不被改动**。

用法
----
    python scripts\\make_demo_viewer.py
    python scripts\\make_demo_viewer.py --thumbs 9 --thumb-width 320
    python scripts\\make_demo_viewer.py --demo-dir evidence_shots\\demo24 --embed auto

环境标签：**PC / SIMULATED**（产物为 PC 侧演示，非板端实测）。
"""
from __future__ import annotations

import argparse
import base64
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ENV_LABEL = "PC / SIMULATED"
DEFAULT_DEMO_DIR = os.path.join("evidence_shots", "demo24")


# ---------------------------------------------------------------- 基础工具

def _rel_display(path: str) -> str:
    """把绝对路径显示成工程内相对路径（正斜杠），便于写进 HTML。"""
    try:
        rel = os.path.relpath(path, ROOT)
    except ValueError:                                  # 跨盘符
        return path.replace("\\", "/")
    return rel.replace("\\", "/")


def _human(nbytes: int) -> str:
    """人类可读体积（与工程既有打印风格一致：MiB 保留两位）。"""
    return "%.2f MiB" % (nbytes / (1024.0 * 1024.0))


def parse_frame_name(name: str):
    """解析 `demo_<idx>_t<秒>_<状态>.png` → (idx, 秒, 状态)；不匹配返回 (-1, 0.0, '')。"""
    stem = os.path.splitext(os.path.basename(name))[0]
    parts = stem.split("_")
    if len(parts) < 4 or parts[0] != "demo":
        return (-1, 0.0, "")
    try:
        idx = int(parts[1])
        seconds = float(parts[2][1:])
    except ValueError:
        return (-1, 0.0, "")
    state = "_".join(parts[3:])
    return (idx, seconds, state)


def collect_frames(frames_dir: str):
    """按**帧号**（不是文件名）排序返回帧清单。"""
    files = glob.glob(os.path.join(frames_dir, "*.png"))
    parsed = []
    for path in files:
        idx, seconds, state = parse_frame_name(path)
        parsed.append((idx, seconds, state, path))
    parsed.sort(key=lambda t: t[0])
    return parsed


def parse_args():
    ap = argparse.ArgumentParser(description="把演示产物打包成单文件 HTML（双击即看）")
    ap.add_argument("--demo-dir", default=DEFAULT_DEMO_DIR,
                    help="演示产物目录（默认 %(default)s）")
    ap.add_argument("--out", default="",
                    help="输出 HTML（默认 <演示目录>_viewer.html，如 evidence_shots/demo24_viewer.html）")
    ap.add_argument("--embed", default="auto", choices=("auto", "h264", "webm", "gif", "both"),
                    help="内嵌源：auto=同时转 H.264+WebM（双源自动兜底），全失败才退回 GIF"
                         "（默认 %(default)s）")
    ap.add_argument("--thumbs", type=int, default=9,
                    help="关键帧缩略图数量（默认 %(default)s；0 = 不生成）")
    ap.add_argument("--thumb-width", type=int, default=320,
                    help="缩略图宽度 px（默认 %(default)s）")
    ap.add_argument("--thumb-quality", type=int, default=80,
                    help="缩略图 JPEG 质量（默认 %(default)s）")
    ap.add_argument("--fps", type=float, default=24.0, help="演示采样帧率（默认 %(default)s）")
    ap.add_argument("--crf", type=int, default=20, help="H.264 恒定质量（默认 %(default)s，越小越清晰）")
    ap.add_argument("--webm-crf", type=int, default=34,
                    help="WebM/VP9 恒定质量（默认 %(default)s，越小越清晰）")
    ap.add_argument("--ffmpeg", default="", help="指定 ffmpeg 可执行文件（默认自动查找）")
    ap.add_argument("--title", default="剧本化交互演示 · 24 fps 流畅版", help="页面标题")
    return ap.parse_args()


# ------------------------------------------------------------ ffmpeg 查找

def find_ffmpeg(explicit: str = "") -> str:
    """按「显式指定 → imageio-ffmpeg 自带 → PATH」顺序找 ffmpeg，找不到返回空串。"""
    if explicit:
        return explicit if os.path.isfile(explicit) else ""
    try:                                                # imageio-ffmpeg 免安装自带
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            return exe
    except Exception:                                   # pragma: no cover
        pass
    return shutil.which("ffmpeg") or ""


# -------------------------------------------------------------- 视频转码

# 逐个尝试的 H.264 编码器（libx264 最通用；imageio-ffmpeg 自带构建未含时退回 openh264/硬编）
H264_CODECS = (
    ("libx264", ["-preset", "slow", "-profile:v", "high", "-level", "3.0"]),
    ("libopenh264", ["-b:v", "1200k"]),
    ("h264_nvenc", ["-preset", "p5"]),
    ("h264_qsv", []),
    ("h264_amf", []),
)

# `<source type=...>` 里的 **codecs 限定**：带上它，浏览器才能在做「资源选择」时
# 用 canPlayType() 判断自己解不解得了 —— 解不了就会自动跳到下一个 `<source>`。
# （实测：不写 codecs 时，未编译 H.264 解码器的 Chromium 会「选中 mp4 → 解码失败 → 不再回退」。）
MP4_MIME = {"libx264": 'video/mp4; codecs="avc1.64001e"'}       # High@3.0（转码时显式 -level 3.0）
WEBM_MIME = {"libvpx-vp9": 'video/webm; codecs="vp9"',
             "libvpx": 'video/webm; codecs="vp8"',
             "libaom-av1": 'video/webm; codecs="av01.0.04M.08"'}

# 逐个尝试的 **开放编码** 视频编码器（VP9/VP8 → WebM）：不依赖任何专有解码器，
# 因此连「未编译 H.264 解码器」的 Chromium 构建（如部分 PySide6 QtWebEngine）也能播。
WEBM_CODECS = (
    ("libvpx-vp9", ["-row-mt", "1", "-cpu-used", "3"]),
    ("libvpx", []),
    ("libaom-av1", ["-row-mt", "1", "-cpu-used", "6"]),
)


def video_info(path: str) -> dict:
    """读视频元数据（cv2 可用时）；失败返回空 dict。"""
    if not os.path.isfile(path):
        return {}
    try:
        import cv2
    except ImportError:                                 # pragma: no cover
        return {}
    cap = cv2.VideoCapture(path)
    info = {
        "fps": float(cap.get(cv2.CAP_PROP_FPS)),
        "frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "w": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "h": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }
    cap.release()
    info["size"] = os.path.getsize(path)
    info["duration"] = info["frames"] / info["fps"] if info["fps"] else 0.0
    return info


def container_tags(path: str) -> dict:
    """扫描文件头尾的容器编码 tag（判是否 H.264：`avc1` / `avc3`）。"""
    tags = {}
    if not os.path.isfile(path):
        return tags
    with open(path, "rb") as fh:
        head = fh.read(4096)
        fh.seek(max(0, os.path.getsize(path) - 65536))
        tail = fh.read()
    blob = head + tail
    for name in ("avc1", "avc3", "mp4v", "hvc1", "hev1", "vp09", "av01"):
        tags[name] = blob.find(name.encode("ascii")) >= 0
    return tags


def _run_transcode(ffmpeg: str, src: str, dst: str, codecs, tail: list) -> tuple:
    """按 codecs 顺序逐个尝试转码。返回 (ok, log, cmd)。"""
    log = []
    if not ffmpeg:
        return False, ["未找到 ffmpeg"], []
    if not os.path.isfile(src):
        return False, ["源视频不存在：%s" % src], []
    for codec, extra in codecs:
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", src, "-an",
               "-c:v", codec] + extra + list(tail) + [dst]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=900)
        except Exception as exc:                        # pragma: no cover
            log.append("%s: 调用失败 %s" % (codec, exc))
            continue
        # ffmpeg 的 stderr 可能是 UTF-8/本地码混排 → 只取最后一行做提示
        err = (proc.stderr or b"").decode("utf-8", "replace").strip().splitlines()
        if proc.returncode == 0 and os.path.isfile(dst) and os.path.getsize(dst) > 0:
            log.append("%s: OK → %s (%s)" % (codec, _rel_display(dst), _human(os.path.getsize(dst))))
            return True, log, cmd
        log.append("%s: 失败(rc=%d) %s" % (codec, proc.returncode, err[-1] if err else ""))
    return False, log, []


def transcode_h264(ffmpeg: str, src: str, dst: str, crf: int = 20) -> tuple:
    """转 H.264 MP4（+faststart）：Safari / Edge / Chrome / Firefox 通吃。返回 (ok, log, cmd)。"""
    return _run_transcode(ffmpeg, src, dst, H264_CODECS,
                          ["-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart"])


def transcode_webm(ffmpeg: str, src: str, dst: str, crf: int = 34) -> tuple:
    """转 VP9/VP8 WebM：**开放编码**，连未编译 H.264 解码器的 Chromium 也能播。"""
    return _run_transcode(ffmpeg, src, dst, WEBM_CODECS,
                          ["-crf", str(crf), "-b:v", "0", "-pix_fmt", "yuv420p"])


def _b64(path: str) -> str:
    """文件 → base64 字符串（用于 data URI 内嵌）。"""
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode("ascii")


# ---------------------------------------------------------- 关键帧缩略图

def make_thumbs(frames, count: int, width: int, quality: int) -> list:
    """等间隔抽 `count` 张关键帧（**必含首帧与末帧**）→ 缩略图 data-URI 列表。"""
    if count <= 0 or not frames:
        return []
    n = len(frames)
    if count == 1:
        picks = [frames[0]]
    else:
        step = (n - 1) / float(count - 1)
        picks = [frames[int(round(i * step))] for i in range(count)]

    seen, uniq = set(), []
    for item in picks:                                  # 按帧号去重（保序）
        if item[0] in seen:
            continue
        seen.add(item[0])
        uniq.append(item)

    from PIL import Image
    out = []
    for idx, seconds, state, path in uniq:
        im = Image.open(path).convert("RGB")
        ratio = float(width) / float(im.width)
        im = im.resize((int(width), max(1, int(round(im.height * ratio)))), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=int(quality), optimize=True)
        out.append({
            "idx": idx,
            "t": seconds,
            "state": state,
            "name": os.path.basename(path),
            "bytes": buf.tell(),
            "uri": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii"),
        })
    return out


# -------------------------------------------------------------- 剧本时间轴

def build_timeline(frames, fps: float) -> list:
    """按**状态变化**自动把帧序列切成若干段（无需手写剧本表）。

    返回 [{state, idx0, idx1, t0, t1, t_end, n}]，t_end = 下一段起点（末段 = 末帧时刻 + 1/fps）。
    """
    segs = []
    for idx, seconds, state, _path in frames:
        if segs and segs[-1]["state"] == state:
            seg = segs[-1]
            seg["idx1"] = idx
            seg["t1"] = seconds
            seg["n"] += 1
        else:
            segs.append({"state": state, "idx0": idx, "idx1": idx,
                         "t0": seconds, "t1": seconds, "n": 1})
    period = (1.0 / fps) if fps > 0 else 0.0
    for i, seg in enumerate(segs):
        if i + 1 < len(segs):
            seg["t_end"] = segs[i + 1]["t0"]
        else:
            seg["t_end"] = seg["t1"] + period
    return segs


def _fmt_time(seconds: float) -> str:
    return "%.1fs" % seconds


def _seg_rows(segs) -> str:
    """时间轴 → <tr> 行（帧号沿用脚本里的补零宽度约定，取 3 位）。"""
    state_cls = {"IDLE": "t-IDLE", "PRESENT": "t-PRESENT", "LISTENING": "t-LISTENING",
                 "THINKING": "t-THINKING", "SPEAKING": "t-SPEAKING"}
    rows = []
    for seg in segs:
        cls = state_cls.get(seg["state"], "t-IDLE")
        span = "%s ~ %s" % (_fmt_time(seg["t0"]), _fmt_time(seg["t_end"]))
        rng = ("%03d" % seg["idx0"]) if seg["idx0"] == seg["idx1"] else \
              ("%03d ~ %03d" % (seg["idx0"], seg["idx1"]))
        rows.append("<tr><td>%s</td><td><span class=\"tag %s\">%s</span></td>"
                    "<td>%s</td><td>%d</td></tr>"
                    % (span, cls, seg["state"], rng, seg["n"]))
    return "\n".join(rows)


def _thumb_cards(thumbs) -> str:
    state_cls = {"IDLE": "t-IDLE", "PRESENT": "t-PRESENT", "LISTENING": "t-LISTENING",
                 "THINKING": "t-THINKING", "SPEAKING": "t-SPEAKING"}
    cards = []
    for th in thumbs:
        cls = state_cls.get(th["state"], "t-IDLE")
        cards.append(
            "<figure><img src=\"%s\" alt=\"%s\">"
            "<figcaption><span class=\"tag %s\">%s</span>t=%.2fs ｜ 帧 %03d</figcaption></figure>"
            % (th["uri"], th["name"], cls, th["state"], th["t"], th["idx"]))
    return "\n".join(cards)


# ---------------------------------------------------------------- HTML 模板

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@TITLE@@（@@ENV@@）</title>
<style>
  :root { --bg:#F2F2E9; --panel:#FCFCF3; --fg:#1F242B; --dim:#5A6572; --acc:#0B7FC4; --warn:#E08600; }
  * { box-sizing:border-box; }
  body { margin:0; padding:24px 28px 60px; background:var(--bg); color:var(--fg);
         font-family:"Microsoft YaHei","Segoe UI",sans-serif; }
  h1 { font-size:20px; margin:0 0 4px; }
  h2 { font-size:15px; margin:28px 0 10px; color:var(--acc);
       border-left:3px solid var(--acc); padding-left:8px; }
  .sub { color:var(--dim); font-size:12px; margin-bottom:6px; line-height:1.75; }
  .box { background:var(--panel); border-radius:10px; padding:16px 18px; margin-bottom:18px; }
  .center { text-align:center; }
  video.vid, img.vid { width:768px; max-width:100%; border-radius:6px; background:#0d141b;
                       display:block; margin:0 auto; box-shadow:0 6px 24px rgba(0,0,0,.55); }
  table { border-collapse:collapse; font-size:13px; width:100%; }
  th,td { border:1px solid #2a3b4a; padding:5px 10px; text-align:left; }
  th { background:#1f2f3d; color:var(--dim); font-weight:600; }
  code { background:#0d141b; padding:1px 5px; border-radius:4px; color:var(--warn); font-size:12px; }
  ul { margin:6px 0 0 18px; padding:0; font-size:13px; line-height:1.9; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(228px,1fr)); gap:12px; }
  figure { margin:0; background:#0d141b; border-radius:8px; overflow:hidden; border:1px solid #223444; }
  figure img { width:100%; display:block; }
  figcaption { font-size:12px; color:var(--dim); padding:5px 8px; }
  .tag { display:inline-block; padding:1px 7px; border-radius:10px; font-size:11px; margin-right:6px; }
  .t-IDLE{background:#2d3f52;color:#cfe3f7} .t-PRESENT{background:#1f4d3a;color:#b6f0d3}
  .t-LISTENING{background:#4d3a1f;color:#f7e2b6} .t-THINKING{background:#3b2f52;color:#dfd0f7}
  .t-SPEAKING{background:#52232d;color:#f7c3cf}
  .note { font-size:12px; color:var(--warn); line-height:1.85; margin-top:10px; }
  .foot { color:var(--dim); font-size:11px; line-height:1.9; border-top:1px solid #223444;
          padding-top:12px; margin-top:26px; }
</style>
</head>
<body>
<h1>@@TITLE@@</h1>
<div class="sub">@@SUBTITLE@@</div>

@@PLAYER_BLOCK@@

<h2>剧本时间轴（按状态切换自动推导，共 @@NSEG@@ 段）</h2>
<div class="box">
<table>
<tr><th>时刻</th><th>状态</th><th>帧号</th><th>帧数</th></tr>
@@SEG_ROWS@@
</table>
</div>

@@THUMBS_BLOCK@@

<h2>校验结论</h2>
<div class="box">
<table>
<tr><th>项目</th><th>实测</th><th>结论</th></tr>
@@CHECK_ROWS@@
</table>
</div>

<h2>说明与已知边界</h2>
<div class="box">
<ul>
  <li><code>--fps 24</code> 是<b>采样 / 播放</b>帧率；玩偶素材本体只有 <b>9.983 fps</b>，
      24 fps 下每个素材帧显示约 2.4 次 —— 观感连续，但「有效变化帧率」的上限仍是素材的 9.983 fps。
      要真正 24 fps 的运动，需按 24 fps 重新生成素材。</li>
  <li>GIF 帧延时只能存 10 ms 的整数倍（物理上存不下 41.67 ms）→ 逐帧延时用 40/50 ms 交替做误差扩散；
      且 PIL 会把「与前一帧完全相同」的帧合并（313 帧 → @@GIF_FRAMES@@ 帧），<b>总时长不变、视觉无损</b>。</li>
  <li>原 <code>demo_scenario.mp4</code> 由 cv2 写成 <code>mp4v</code>（MPEG-4 Part 2），多数浏览器
      <b>不支持在 <code>&lt;video&gt;</code> 里播放</b>；本页内嵌的 @@EMBED_LABEL@@
      是 <code>@@TRANSCODE_CMD@@</code> 转出的浏览器可播版本（<b>原文件未改动</b>）。</li>
  <li>本页是<b>自包含单文件</b>（视频与缩略图均为 base64 内嵌）：<b>双击即看，也可单独转发</b>，
      不依赖同目录任何文件。</li>
  <li>素材源：<code>idle_normal / idle_present / idle_listening / idle_thinking / talking_normal /
      talking_low</code>，均为 <b>466×480 / waist-up</b>；画布 1024×600，玩偶框
      <code>423×516 @ (593,32)</code>，contain 缩放 <b>0.9077</b> → 423×436 贴底。</li>
  <li>环境标签：<b>@@ENV@@（PC 侧离屏渲染 / 非板端实测）</b>。</li>
</ul>
</div>

<div class="foot">
  生成命令：<code>python scripts\\make_demo_viewer.py @@CLI_ARGS@@</code><br>
  生成时间：@@BUILD_TIME@@ ｜ 产物：<code>@@OUT_REL@@</code>（@@HTML_SIZE@@）<br>
  内嵌源：@@EMBED_SUMMARY@@<br>
  本页由 <code>scripts/make_demo_viewer.py</code> 生成，仅供项目内部评审使用。
</div>

<script>
(function () {
  var v = document.getElementById("pv");
  if (!v) { return; }
  var fb = document.getElementById("vfallback");
  v.addEventListener("error", function () {
    if (fb) { fb.style.display = "block"; }
  });
  var p = v.play();
  if (p && p.catch) { p.catch(function () { /* 自动播放被拦：控件已可见，点一下即可 */ }); }
})();
</script>
</body>
</html>
"""


def _player_block(ctx: dict) -> str:
    """播放区：`<video>` 内放**多个 `<source>`**（H.264 → WebM），浏览器自动挑能播的；
    全都不支持时才由 JS 显示兜底提示（并可用 GIF 兼容块）。"""
    blocks = []
    sources = ctx.get("sources") or []
    if sources:
        tags = "\n    ".join("<source src=\"%s\" type='%s'>" % (uri, mime)
                             for uri, mime, _lab in sources)
        poster = (' poster="%s"' % ctx["poster"]) if ctx.get("poster") else ""
        labels = " 、 ".join(lab for _uri, _mime, lab in sources)
        blocks.append(
            '<div class="box center">'
            '<video id="pv" class="vid" controls autoplay loop muted playsinline preload="auto"%s>\n'
            '    %s\n</video>'
            '<div class="sub" style="margin:10px 0 0">%s</div>'
            '<div class="sub" style="margin:4px 0 0">内嵌播放源（浏览器自动选择可播的第一个）：<b>%s</b></div>'
            '<div id="vfallback" class="note" style="display:none">'
            '若上方黑屏不动：这个浏览器两个编码都解不了，请直接打开同目录的 '
            '<code>%s</code>（万能兜底），或用系统播放器打开 <code>%s</code>。</div>'
            '</div>' % (poster, tags, ctx["video_line"], labels, ctx["gif_rel"], ctx["files_rel"]))
    if (not sources or ctx["mode"] == "both") and ctx["gif_uri"]:
        title = "GIF 兼容版（内嵌）" if sources else "GIF 版（内嵌）"
        blocks.append(
            '<div class="box center">'
            '<img class="vid" src="%s" alt="demo gif">'
            '<div class="sub" style="margin:10px 0 0"><b>%s</b> ｜ %s</div>'
            '</div>' % (ctx["gif_uri"], title, ctx["gif_line"]))
    return "\n".join(blocks)


def _check_rows(items) -> str:
    """校验项 → <tr> 行。items = [(项目, 实测, "OK"/"FAIL"/"INFO")]。"""
    rows = []
    for name, value, status in items:
        color = {"OK": "#7ddc9b", "FAIL": "#ff8a8a"}.get(status, "#8aa0b4")
        rows.append("<tr><td>%s</td><td>%s</td><td style=\"color:%s\">%s</td></tr>"
                    % (name, value, color, status))
    return "\n".join(rows)


def _render(ctx: dict) -> str:
    """把 ctx 里的 @@KEY@@ 全部替换进模板。"""
    html = HTML_TEMPLATE
    for key, value in ctx.items():
        html = html.replace("@@%s@@" % key, str(value))
    return html


# --------------------------------------------------------------------- main

def main() -> int:
    args = parse_args()

    demo_dir = args.demo_dir if os.path.isabs(args.demo_dir) \
        else os.path.join(ROOT, args.demo_dir)
    demo_dir = os.path.normpath(demo_dir)
    if args.out:
        out_path = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    else:
        out_path = os.path.join(os.path.dirname(demo_dir),
                                os.path.basename(demo_dir) + "_viewer.html")

    frames_dir = os.path.join(demo_dir, "demo_frames")
    gif_path = os.path.join(demo_dir, "demo_scenario.gif")
    mp4_path = os.path.join(demo_dir, "demo_scenario.mp4")
    h264_path = os.path.join(demo_dir, "demo_scenario_h264.mp4")
    webm_path = os.path.join(demo_dir, "demo_scenario_vp9.webm")

    print("=== make_demo_viewer（%s）===" % ENV_LABEL)
    print("演示目录：%s" % _rel_display(demo_dir))

    frames = collect_frames(frames_dir)
    if not frames:
        print("!! 未找到帧序列：%s" % _rel_display(frames_dir))
        return 2
    names = [os.path.basename(f[3]) for f in frames]
    order_ok = (names == sorted(names))
    print("[1] 帧序列：%d 张（%s ~ %s）；文件名序 == 帧号序：%s"
          % (len(frames), names[0], names[-1], "是" if order_ok else "否"))

    # ---------- ② 转码成浏览器可播格式（原 mp4 不动） ----------
    ffmpeg = find_ffmpeg(args.ffmpeg)
    h264_ok = webm_ok = False
    tc_cmds = []
    want_h264 = args.embed in ("auto", "h264", "both")
    want_webm = args.embed in ("auto", "webm", "both")
    h264_codec = webm_codec = ""
    if want_h264 or want_webm:
        print("[2] ffmpeg：%s" % (ffmpeg or "未找到"))
    if want_h264:
        ok, log, cmd = transcode_h264(ffmpeg, mp4_path, h264_path, args.crf)
        for line in log:
            print("     H.264 " + line)
        h264_ok = ok
        if ok:
            h264_codec = cmd[cmd.index("-c:v") + 1]
            tc_cmds.append(" ".join([os.path.basename(cmd[0])] + cmd[1:]))
    if want_webm:
        ok, log, cmd = transcode_webm(ffmpeg, mp4_path, webm_path, args.webm_crf)
        for line in log:
            print("     WebM  " + line)
        webm_ok = ok
        if ok:
            webm_codec = cmd[cmd.index("-c:v") + 1]
            tc_cmds.append(" ".join([os.path.basename(cmd[0])] + cmd[1:]))
    if args.embed == "h264" and not h264_ok:
        print("!! --embed h264 但转码失败：请改用 --embed auto/gif，或用 --ffmpeg 指定 ffmpeg")
        return 3
    if args.embed == "webm" and not webm_ok:
        print("!! --embed webm 但转码失败：请改用 --embed h264/auto/gif")
        return 3
    if not (h264_ok or webm_ok) and args.embed != "gif":
        print("     两种编码都不可用 → 退回内嵌 GIF（100% 浏览器兼容）")
    if args.embed == "gif":
        print("[2] --embed gif：跳过转码，直接内嵌 GIF")

    meta_path = h264_path if h264_ok else (webm_path if webm_ok else mp4_path)
    vinfo = video_info(meta_path)
    tags = container_tags(meta_path)
    if vinfo:
        print("[3] 内嵌视频：%s ｜ %d×%d / fps=%.4f / %d 帧 / %.3f s / %s"
              % (_rel_display(meta_path), vinfo["w"], vinfo["h"], vinfo["fps"],
                 vinfo["frames"], vinfo["duration"], _human(vinfo["size"])))

    gif_info = {}
    if os.path.isfile(gif_path):
        from PIL import Image
        im = Image.open(gif_path)
        n, total = 0, 0
        try:
            while True:
                total += im.info.get("duration", 0)
                n += 1
                im.seek(n)
        except EOFError:
            pass
        gif_info = {"frames": n, "total": int(total), "size": os.path.getsize(gif_path)}
        print("[4] GIF：%d 帧 / 总时长 %d ms / %s"
              % (gif_info["frames"], gif_info["total"], _human(gif_info["size"])))

    # ---------- ③ 缩略图 / 时间轴 ----------
    thumbs = make_thumbs(frames, args.thumbs, args.thumb_width, args.thumb_quality)
    segs = build_timeline(frames, args.fps)
    thumb_bytes = sum(t["bytes"] for t in thumbs)
    print("[5] 关键帧缩略图：%d 张（JPEG 合计 %s）" % (len(thumbs), _human(thumb_bytes)))
    print("[6] 剧本时间轴：自动推导 %d 段（%s）"
          % (len(segs), "、".join(s["state"] for s in segs)))

    # ---------- ④ 内嵌数据（base64 data URI，多 `<source>` 兜底） ----------
    sources = []
    if h264_ok:
        sources.append(("data:video/mp4;base64," + _b64(h264_path),
                        MP4_MIME.get(h264_codec, "video/mp4"),
                        "H.264/MP4 %s" % _human(os.path.getsize(h264_path))))
    if webm_ok:
        sources.append(("data:video/webm;base64," + _b64(webm_path),
                        WEBM_MIME.get(webm_codec, "video/webm"),
                        "VP9/WebM %s" % _human(os.path.getsize(webm_path))))
    gif_uri = ""
    if (not sources) or (args.embed == "both"):
        if os.path.isfile(gif_path):
            gif_uri = "data:image/gif;base64," + _b64(gif_path)

    video_line = ("%d×%d ｜ 真 %.4f fps ｜ %d 帧 ｜ %.3f s ｜ "
                  "内容源 <code>%s</code>（cv2 写的 mp4v / MPEG-4 Part 2，浏览器多不能播）"
                  "→ 内嵌时可播编码；<b>原文件未改动</b>"
                  % (vinfo["w"], vinfo["h"], vinfo["fps"], vinfo["frames"], vinfo["duration"],
                     os.path.basename(mp4_path))) if vinfo else "（无视频元数据）"
    files_rel = " 、 ".join(_rel_display(p) for p, ok in
                           ((h264_path, h264_ok), (webm_path, webm_ok)) if ok) or "—"
    gif_line = ("%d×%d ｜ 写出 %d 帧 ｜ 总时长 %d ms ｜ loop=0 ｜ %s"
                % (vinfo["w"] if vinfo else 0, vinfo["h"] if vinfo else 0,
                   gif_info.get("frames", 0), gif_info.get("total", 0),
                   _human(gif_info.get("size", 0))))

    # ---------- ⑤ 校验项 ----------
    expect_ms = (len(frames) / args.fps * 1000.0) if args.fps > 0 else 0.0
    checks = [("帧序列", "%d 张，%s ~ %s" % (len(frames), names[0], names[-1]),
               "OK" if order_ok else "FAIL")]
    enc_bits = []
    if h264_ok:
        enc_bits.append("avc1（H.264）%s" % _human(os.path.getsize(h264_path)))
    if webm_ok:
        enc_bits.append("VP9（WebM）%s" % _human(os.path.getsize(webm_path)))
    if vinfo:
        fps_ok = (abs(vinfo["fps"] - args.fps) < 0.01) and (vinfo["frames"] == len(frames))
        checks.append(("内嵌视频元数据（%s）" % os.path.basename(meta_path),
                       "%d×%d / fps=%.4f / %d 帧 / %.3f s / %s"
                       % (vinfo["w"], vinfo["h"], vinfo["fps"], vinfo["frames"],
                          vinfo["duration"], _human(vinfo["size"])),
                       "OK" if fps_ok else "FAIL"))
    checks.append(("内嵌视频编码",
                   " ＋ ".join(enc_bits) if enc_bits else
                   "无（退回 GIF：%s）" % _human(gif_info.get("size", 0)),
                   "OK" if enc_bits else "FAIL"))
    if gif_info:
        diff = int(gif_info["total"] - expect_ms)
        checks.append(("GIF 兜底文件",
                       "%d 帧 / 总时长 %d ms / %s ｜ 与 %.0f fps 时间轴差 %+d ms"
                       % (gif_info["frames"], gif_info["total"], _human(gif_info["size"]),
                          args.fps, diff),
                       "OK" if abs(diff) <= 25 else "FAIL"))
    checks.append(("内嵌体积",
                   "视频 %s + GIF %s + 缩略图 %s"
                   % ("+".join(enc_bits) if enc_bits else "—",
                      _human(gif_info.get("size", 0)) if gif_uri else "—",
                      _human(thumb_bytes)), "INFO"))

    # ---------- ⑥ 渲染（HTML 体积自指 → 迭代到收敛） ----------
    ctx = {
        "TITLE": args.title,
        "ENV": ENV_LABEL,
        "SUBTITLE": ("脚本 <code>examples/run_demo_scenario.py --fps %.0f --mp4</code> ｜ "
                     "链路：EventBus → FSM → UiState → PySide6 板端三区 1024×600 ｜ "
                     "<b>环境标签：%s（非板端实测）</b>" % (args.fps, ENV_LABEL)),
        "PLAYER_BLOCK": "",
        "NSEG": len(segs),
        "SEG_ROWS": _seg_rows(segs),
        "THUMBS_BLOCK": "",
        "CHECK_ROWS": _check_rows(checks),
        "GIF_FRAMES": str(gif_info.get("frames", "?")),
        "EMBED_LABEL": " ＋ ".join(enc_bits) if enc_bits else "GIF（100% 兼容）",
        "TRANSCODE_CMD": "<br>".join("ffmpeg " + c for c in tc_cmds) if tc_cmds else "（本页未使用转码）",
        "OUT_REL": _rel_display(out_path),
        "BUILD_TIME": time.strftime("%Y-%m-%d %H:%M:%S"),
        "CLI_ARGS": " ".join(sys.argv[1:]) or "（默认参数）",
        "EMBED_SUMMARY": "",
        "HTML_SIZE": "0.00 MiB",
    }
    if thumbs:
        ctx["THUMBS_BLOCK"] = (
            "<h2>关键帧（等间隔抽取 %d 张，含首末帧）</h2>\n"
            "<div class=\"box\"><div class=\"grid\">\n%s\n</div></div>"
            % (len(thumbs), _thumb_cards(thumbs)))
    ctx["PLAYER_BLOCK"] = _player_block({
        "mode": args.embed,
        "sources": sources,
        "poster": thumbs[0]["uri"] if thumbs else "",
        "gif_uri": gif_uri,
        "video_line": video_line,
        "gif_line": gif_line,
        "gif_rel": _rel_display(gif_path),
        "files_rel": files_rel,
    })

    parts = []
    for _uri, _mime, label in sources:
        parts.append(label)
    if gif_uri:
        parts.append("GIF %s" % _human(gif_info.get("size", 0)))
    if thumbs:
        parts.append("缩略图 %d 张 %s" % (len(thumbs), _human(thumb_bytes)))
    ctx["EMBED_SUMMARY"] = " + ".join(parts) or "无"

    size_text, html = "0.00 MiB", ""
    for _ in range(4):                                  # 页面里要写自身体积 → 迭代到收敛
        ctx["HTML_SIZE"] = size_text
        html = _render(ctx)
        new_text = _human(len(html.encode("utf-8")))
        if new_text == size_text:
            break
        size_text = new_text

    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    html_bytes = len(html.encode("utf-8"))
    print("[7] 产物：%s（%s）" % (_rel_display(out_path), _human(html_bytes)))
    print("     内嵌：%s" % ctx["EMBED_SUMMARY"])
    print("     双击用浏览器打开即可播放（自包含单文件，无外部依赖）")
    ok_all = bool(order_ok and (sources or gif_uri))
    print("结论: %s" % ("PASS" if ok_all else "FAIL"))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
