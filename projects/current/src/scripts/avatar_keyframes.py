# -*- coding: utf-8 -*-
"""avatar_keyframes —— 抽关键帧 + 核验「首尾帧循环 / 跨素材一致性」（Seedance 素材质检第一关）。

## 为什么要量化这两件事
玩偶素材是**循环素材**：
- 切状态时，只要每个素材的**第 1 帧**长得一样，画面就不会「跳大小、跳姿态」；
- 单素材循环播放时，只要**首帧 == 末帧**，无限循环就不会抖一下。

于是素材质检只需盯两个可量化指标，本工具都能量出数字（而不是靠肉眼）：

1. **自循环**：首帧 vs 末帧 差异 —— `--check-loop`；
2. **跨素材**：首帧 vs 参考图（`@character.png`，即 `idle_normal` 的首帧）差异 —— `--ref`。

## 产出（落 `--out-dir`）
    <素材名>_t00.00_f000000.png   关键帧原图（**绿幕原样**，可直接当 Seedance 首帧/尾帧/参考图）
    <素材名>_loop_check.png       首帧 | 末帧 | 差异热力 三栏并排（绿幕底，肉眼可复核）
    <素材名>_ref_check.png        首帧 | 参考图 | 差异热力 三栏并排

## 用法
    # 1) 生成前：抽绿幕参考帧（喂给 Seedance，作"首帧 = 尾帧"的锚点）
    python scripts/avatar_keyframes.py --src "...\\idle_normal.mp4" --out-dir "...\\refs" --count 1

    # 2) 生成后：核验首尾帧循环（FAIL 时退出码 1，可进 CI / 批处理）
    python scripts/avatar_keyframes.py --src "...\\idle_listening.mp4" --out-dir "...\\checks" --check-loop

    # 3) 核验跨素材一致性（新素材首帧 vs idle_normal 首帧）
    python scripts/avatar_keyframes.py --src "...\\idle_listening.mp4" --out-dir checks \\
        --check-loop --ref "...\\refs\\idle_normal_t00.00_f000000.png"

依赖：numpy + OpenCV（读 mp4，与桌宠抠像同源依赖）；合成对比图额外需要 Pillow（缺失时只出报告）。
环境标签：PC/SIMULATED（生成阶段质检）；只**读**原始素材，从不修改、不移动。
"""
from __future__ import annotations

import argparse
import sys
import typing
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

FRAME_EXTS: typing.Tuple[str, ...] = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
VIDEO_EXTS: typing.Tuple[str, ...] = (".mp4", ".mov", ".mkv", ".avi", ".webm")
DEFAULT_BG: typing.Tuple[int, int, int] = (0, 255, 0)   # 绿幕基准色（RGB）
BANNER_BG: typing.Tuple[int, int, int] = (16, 20, 28)   # 比对图底色（与 UI 一致）

# 判定阈值：thr=8 认为「肉眼可见差异」；主体区指标优先于全图指标。
LOOP_MEAN_LIMIT: float = 2.0     # 自循环：主体区平均差 ≤ 2/255
LOOP_FRAC_LIMIT: float = 0.02    # 自循环：差异像素 ≤ 2%
REF_MEAN_LIMIT: float = 4.0      # 跨素材：主体区平均差 ≤ 4/255
REF_FRAC_LIMIT: float = 0.05     # 跨素材：差异像素 ≤ 5%


# --------------------------------------------------------------------------- #
# 纯逻辑（无 cv2 / Pillow 依赖，可单测）
# --------------------------------------------------------------------------- #
def sample_times(duration: float, count: int = 7) -> typing.List[float]:
    """在 [0, duration] 上等距取 count 个时刻（含首尾）；count<=1 只取 0。"""
    if count <= 1:
        return [0.0]
    total = max(float(duration), 0.0)
    return [total * i / (count - 1) for i in range(count)]


def frame_index_at(seconds: float, fps: float, total: int) -> int:
    """时刻 → 帧号（四舍五入后夹到 [0, total-1]；fps/total 非法时回 0）。"""
    if fps <= 0 or total <= 0:
        return 0
    index = int(round(max(float(seconds), 0.0) * float(fps)))
    return max(0, min(index, total - 1))


def background_mask(image, bg: typing.Sequence[int] = DEFAULT_BG, tol: int = 60):
    """绿幕背景掩膜（True = 背景）：各通道与 bg 的最大差 ≤ tol。"""
    import numpy as np

    img = np.asarray(image)
    if img.ndim != 3 or img.shape[2] < 3:
        raise ValueError("图像应为 HxWx3(RGB) 或 HxWx4(RGBA)")
    diff = np.abs(img[..., :3].astype(np.int16) - np.asarray(bg, dtype=np.int16))
    return diff.max(axis=2) <= int(tol)


def auto_bg_mask(image, bg: typing.Sequence[int] = DEFAULT_BG, tol: int = 60):
    """自动取背景掩膜：**RGBA 按 alpha**（抠像后素材），**RGB 按绿幕色距离**（原始素材）。"""
    import numpy as np

    img = np.asarray(image)
    if img.ndim == 3 and img.shape[2] == 4:
        return img[..., 3] <= 16
    return background_mask(img, bg=bg, tol=tol)


def diff_stats(a, b, thr: int = 8, bg_mask=None) -> typing.Dict[str, float]:
    """两张同尺寸图的逐像素差异统计（通道平均差）。

    keys: mean/p99/max/frac_gt（全图）+ fg_mean/fg_frac_gt/fg_ratio（主体区）。
    背景判定优先级：任一张图带 alpha → 用 alpha；否则用传入的 bg_mask。
    主体区 = 两张图都算前景的像素；无前景时退回全图。
    """
    import numpy as np

    x = np.asarray(a)
    y = np.asarray(b)
    if x.shape != y.shape:
        raise ValueError("两图尺寸不一致: %s vs %s" % (x.shape, y.shape))
    if x.ndim not in (2, 3):
        raise ValueError("图像应为 HxW 或 HxWxC: %s" % (x.shape,))

    mask = None
    if x.ndim == 3 and (x.shape[2] == 4 or y.shape[2] == 4):
        ax = x[..., 3] if x.shape[2] == 4 else np.full(x.shape[:2], 255)
        ay = y[..., 3] if y.shape[2] == 4 else np.full(y.shape[:2], 255)
        mask = (ax <= 16) | (ay <= 16)
    elif bg_mask is not None:
        cand = np.asarray(bg_mask)
        if cand.shape == x.shape[:2]:
            mask = cand
    if mask is not None and bool(mask.all()):
        mask = None

    d = np.abs(x[..., :3].astype(np.float32) - y[..., :3].astype(np.float32))
    d = d.mean(axis=2) if d.ndim == 3 else d
    flat = d.reshape(-1)
    fg = flat[~np.asarray(mask).reshape(-1)] if mask is not None else flat
    return {
        "mean": float(flat.mean()),
        "p99": float(np.percentile(flat, 99)),
        "max": float(flat.max()),
        "frac_gt": float((flat > thr).mean()),
        "fg_mean": float(fg.mean()),
        "fg_frac_gt": float((fg > thr).mean()),
        "fg_ratio": float(fg.size) / float(max(flat.size, 1)),
    }


def verdict(stats: typing.Dict[str, float], mean_limit: float, frac_limit: float) -> str:
    """差异统计 → PASS / WARN / FAIL（以主体区指标为准；2 倍阈值内算 WARN）。"""
    mean = float(stats.get("fg_mean", stats.get("mean", 0.0)))
    frac = float(stats.get("fg_frac_gt", stats.get("frac_gt", 0.0)))
    if mean <= mean_limit and frac <= frac_limit:
        return "PASS"
    if mean <= mean_limit * 2 and frac <= frac_limit * 2:
        return "WARN"
    return "FAIL"


def loop_verdict(stats: typing.Dict[str, float]) -> str:
    """自循环判定（首帧 vs 末帧）。"""
    return verdict(stats, LOOP_MEAN_LIMIT, LOOP_FRAC_LIMIT)


def ref_verdict(stats: typing.Dict[str, float]) -> str:
    """跨素材一致性判定（首帧 vs 参考图）。"""
    return verdict(stats, REF_MEAN_LIMIT, REF_FRAC_LIMIT)


def heat_image(a, b, gain: int = 4):
    """差异热力图（HxWx3 uint8）：黑底，差异越大越亮（红→黄）。"""
    import numpy as np

    x = np.asarray(a).astype(np.int16)
    y = np.asarray(b).astype(np.int16)
    d = np.abs(x[..., :3] - y[..., :3]).max(axis=2)
    heat = np.clip(d * int(gain), 0, 255).astype(np.uint8)
    out = np.zeros((heat.shape[0], heat.shape[1], 3), dtype=np.uint8)
    out[..., 0] = heat
    out[..., 1] = (heat // 3).astype(np.uint8)
    return out


def report_lines(title: str, stats: typing.Dict[str, float], judge: str) -> typing.List[str]:
    """把差异统计整理成可读的多行报告（纯字符串，便于单测/落日志）。"""
    return [
        "%s  ->  %s" % (title, judge),
        "    全图  mean=%.2f  p99=%.1f  max=%.1f  差异像素(>8)=%.2f%%"
        % (stats["mean"], stats["p99"], stats["max"], stats["frac_gt"] * 100.0),
        "    主体  mean=%.2f  差异像素(>8)=%.2f%%  （主体占全图 %.1f%%）"
        % (stats["fg_mean"], stats["fg_frac_gt"] * 100.0, stats["fg_ratio"] * 100.0),
    ]


# --------------------------------------------------------------------------- #
# I/O：读源（mp4 / 帧目录）→ 落关键帧 → 合成对比图
# --------------------------------------------------------------------------- #
FONT_CANDIDATES = (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf")


def _cv2():
    """按需导入 OpenCV（读 mp4 必需），缺失时给安装提示。"""
    try:
        import cv2
    except ImportError:
        raise SystemExit("需要 OpenCV 才能读 mp4：pip install opencv-python-headless")
    return cv2


def _to_rgb(raw):
    """OpenCV BGR/BGRA → RGB/RGBA（转连续数组，便于 Pillow 保存）。"""
    import numpy as np

    arr = np.asarray(raw)
    if arr.ndim == 3 and arr.shape[2] == 4:
        return np.ascontiguousarray(arr[..., [2, 1, 0, 3]])
    if arr.ndim == 3 and arr.shape[2] == 3:
        return np.ascontiguousarray(arr[..., ::-1])
    return arr


def _imread(path: typing.Union[str, Path]):
    """读图（IMREAD_UNCHANGED，返回 BGR/BGRA 或 None）。**兼容非 ASCII 路径**。

    Windows 上 `cv2.imread` 走 ANSI 文件 API：路径含中文时直接返回 None
    （症状：`can't open/read file: check file path/integrity` + 路径乱码），
    会让 `--ref` 误报"无法读取参考图"。这里改为
    `np.fromfile`（Python 层，Unicode 安全）+ `cv2.imdecode`（内存解码），
    语义与 `cv2.imread(..., IMREAD_UNCHANGED)` 一致。
    """
    import numpy as np

    cv2 = _cv2()
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
    except OSError:
        return None
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_UNCHANGED)


def _imwrite(path: typing.Union[str, Path], arr) -> bool:
    """写图（入参 BGR/BGRA）。与 `_imread` 同理：兼容非 ASCII 路径。"""
    import numpy as np

    cv2 = _cv2()
    path = Path(path)
    ok, buf = cv2.imencode(path.suffix or ".png", np.ascontiguousarray(arr))
    if not ok:
        return False
    buf.tofile(str(path))
    return True


def probe_source(src: typing.Union[str, Path], src_fps: float = 24.0) -> typing.Dict:
    """探测源：视频给 宽/高/帧率/帧数/时长；帧目录给 宽/高/帧数（帧率取 src_fps）。"""
    cv2 = _cv2()
    src = Path(src)
    if src.is_dir():
        files = sorted(p for p in src.iterdir()
                       if p.is_file() and p.suffix.lower() in FRAME_EXTS)
        if not files:
            raise SystemExit("目录内没有帧文件: %s" % src)
        first = _imread(files[0])
        if first is None:
            raise SystemExit("无法读取帧: %s" % files[0])
        height, width = first.shape[:2]
        fps = float(src_fps) if src_fps > 0 else 24.0
        return {"kind": "frames", "files": files, "width": width, "height": height,
                "fps": fps, "frames": len(files), "duration": len(files) / fps}

    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        cap.release()
        raise SystemExit("无法打开视频: %s" % src)
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        return {"kind": "video",
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "fps": fps, "frames": frames,
                "duration": (frames / fps) if fps > 0 else 0.0}
    finally:
        cap.release()


def read_frame(src: typing.Union[str, Path], index: int, info: typing.Dict):
    """按帧号取帧（返回 RGB/RGBA uint8）：视频随机定位，末帧从 total-2 连读两帧。"""
    cv2 = _cv2()
    src = Path(src)
    if info.get("kind") == "frames":
        files = info["files"]
        idx = max(0, min(int(index), len(files) - 1))
        raw = _imread(files[idx])
        if raw is None:
            raise SystemExit("无法读取帧: %s" % files[idx])
        return _to_rgb(raw)

    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        cap.release()
        raise SystemExit("无法打开视频: %s" % src)
    try:
        total = int(info.get("frames") or 0)
        target = max(0, min(int(index), total - 1)) if total else max(0, int(index))
        # 定位到目标帧：**必须先 seek**（否则读到的永远是首帧）。
        # 末帧退回一格再连读两帧，规避部分编码器「seek 到末帧」越界返回空帧。
        start = max(target - 1, 0) if (total and target >= total - 1) else target
        cap.set(cv2.CAP_PROP_POS_FRAMES, start)
        ok, frame = cap.read()
        if ok and start != target:             # 末帧：再补读一帧到目标帧
            ok2, frame2 = cap.read()
            if ok2:
                ok, frame = True, frame2
        if not ok or frame is None:
            raise SystemExit("读取帧失败: %s (frame %d)" % (src, index))
        return _to_rgb(frame)
    finally:
        cap.release()


def save_rgb(path: typing.Union[str, Path], rgb) -> bool:
    """保存 RGB/RGBA 图（优先 Pillow，缺则 cv2 回退）；返回是否成功。"""
    import numpy as np

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image

        Image.fromarray(np.asarray(rgb)).save(str(path))
        return True
    except ImportError:
        pass
    arr = np.asarray(rgb)
    arr = arr[..., ::-1] if arr.ndim == 3 else arr
    return _imwrite(path, arr)


def _font(size: int = 15):
    """中文标签字体（找不到就用 Pillow 默认字体）。"""
    import os

    from PIL import ImageFont

    for path in FONT_CANDIDATES:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def compose_compare(panels, labels, out_path: typing.Union[str, Path],
                    gap: int = 10, label_h: int = 26) -> bool:
    """多栏并排对比图（上带中文标签；RGBA 先合成到深色底）；缺 Pillow 返回 False。"""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return False

    images = []
    for panel in panels:
        img = panel if hasattr(panel, "convert") else Image.fromarray(panel)
        if img.mode == "RGBA":
            canvas = Image.new("RGB", img.size, BANNER_BG)
            canvas.paste(img, (0, 0), img)
            img = canvas
        images.append(img.convert("RGB"))

    width = sum(i.width for i in images) + gap * (len(images) - 1)
    height = max(i.height for i in images) + label_h
    out = Image.new("RGB", (width, height), BANNER_BG)
    draw = ImageDraw.Draw(out)
    font = _font(15)
    x = 0
    for img, text in zip(images, labels):
        out.paste(img, (x, label_h))
        box = draw.textbbox((0, 0), text, font=font)
        draw.text((x + max((img.width - (box[2] - box[0])) / 2, 0) - box[0], 5),
                  text, font=font, fill=(228, 232, 240))
        x += img.width + gap
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(str(out_path))
    return True


# --------------------------------------------------------------------------- #
# 最佳循环点扫描：找出与首帧最接近的帧（= 尾帧锚点 / 素材裁剪点）
# --------------------------------------------------------------------------- #
def _scaled_rgb(cv2, rgb, scale: int = 4):
    """降采样（扫描时用：更快、且对发丝相位噪声更宽容）。"""
    if scale <= 1:
        return rgb
    height, width = rgb.shape[:2]
    return cv2.resize(rgb, (max(width // scale, 1), max(height // scale, 1)),
                      interpolation=cv2.INTER_AREA)


def scan_best_loop(src: typing.Union[str, Path], info: typing.Dict, first,
                   bg_mask=None, scale: int = 4, step: int = 1) -> typing.Dict:
    """顺序扫描源，找与首帧差异（主体 mean）最小的帧。

    返回 {"index": int, "stats": {...}}（低分辨率统计，用于排序）；扫描失败返回 {}。
    用途：① 给 Seedance 指定尾帧参考；② 给已生成素材挑裁剪点（得到更顺的循环）。
    """
    cv2 = _cv2()
    src = Path(src)
    step = max(int(step), 1)
    ref = _scaled_rgb(cv2, first, scale)
    mask = None
    if bg_mask is not None:
        mask = cv2.resize(bg_mask.astype("uint8"), (ref.shape[1], ref.shape[0]),
                          interpolation=cv2.INTER_NEAREST).astype(bool)
    best: typing.Dict = {}

    if info.get("kind") == "frames":
        files = info["files"]
        for idx in range(0, len(files), step):
            raw = _imread(files[idx])
            if raw is None:
                continue
            stats = diff_stats(ref, _scaled_rgb(cv2, _to_rgb(raw), scale), bg_mask=mask)
            if not best or stats["fg_mean"] <= best["stats"]["fg_mean"]:
                best = {"index": idx, "stats": stats}
        return best

    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        cap.release()
        return {}
    try:
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % step == 0:
                stats = diff_stats(ref, _scaled_rgb(cv2, _to_rgb(frame), scale),
                                   bg_mask=mask)
                if not best or stats["fg_mean"] <= best["stats"]["fg_mean"]:
                    best = {"index": idx, "stats": stats}
            idx += 1
    finally:
        cap.release()
    return best


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_hex(text: str) -> typing.Tuple[int, int, int]:
    """`--bg RRGGBB` → (R,G,B)。"""
    s = str(text).strip().lstrip("#")
    if len(s) != 6:
        raise SystemExit("--bg 应为 6 位 hex（如 00FF00），收到: %r" % text)
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError:
        raise SystemExit("--bg 非法: %r" % text)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="抽关键帧（绿幕原样）+ 核验首尾帧循环 / 跨素材一致性")
    ap.add_argument("--src", required=True, help="原始绿幕 mp4，或已抠好的帧目录")
    ap.add_argument("--out-dir", required=True, help="关键帧与核验图输出目录")
    ap.add_argument("--name", default=None, help="素材名（默认取源文件名）")
    ap.add_argument("--count", type=int, default=3,
                    help="抽帧数量（含首尾，默认 %(default)s；填 1 = 只抽首帧当参考图）")
    ap.add_argument("--check-loop", action="store_true",
                    help="核验首帧 vs 末帧（循环是否顺畅）")
    ap.add_argument("--ref", default=None,
                    help="参考图（@character.png / idle_normal 首帧）→ 核验跨素材一致性")
    ap.add_argument("--find-loop", action="store_true",
                    help="扫描全片，找与首帧最接近的帧（尾帧锚点 / 循环裁剪点）")
    ap.add_argument("--src-fps", type=float, default=24.0,
                    help="--src 为帧目录时的源帧率（默认 %(default)s）")
    ap.add_argument("--bg", default="00FF00", metavar="RRGGBB",
                    help="绿幕基准色（默认 %(default)s）")
    ap.add_argument("--bg-tol", type=int, default=60,
                    help="绿幕色容差，越大越宽松（默认 %(default)s）")
    return ap


def _safe_stdout() -> None:
    """中文 Windows 控制台/重定向默认 GBK：`✓ ⚠` 之类符号不在 GBK 内会直接崩，故兜一层。"""
    stream = getattr(sys, "stdout", None)
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(errors="replace")
        except (ValueError, OSError):
            pass


def _load_ref(path: Path):
    """读参考图（RGB/RGBA uint8）。"""
    if not path.is_file():
        raise SystemExit("--ref 不存在: %s" % path)
    raw = _imread(path)
    if raw is None:
        raise SystemExit("无法读取参考图: %s" % path)
    return _to_rgb(raw)


def main(argv: typing.Optional[typing.List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    _safe_stdout()
    src = Path(args.src)
    if not src.exists():
        raise SystemExit("--src 不存在: %s" % src)
    bg = parse_hex(args.bg)
    out_dir = Path(args.out_dir)
    name = args.name or src.stem

    info = probe_source(src, args.src_fps)
    print("源: %s（%s %dx%d @%.2f fps, %d 帧, %.2f s）"
          % (src.name, info["kind"], info["width"], info["height"],
             info["fps"], info["frames"], info["duration"]))
    print("输出目录: %s" % out_dir)

    # 1) 关键帧（**绿幕原样**落盘：可直接喂 Seedance 当首帧/尾帧/参考图）
    indices: typing.List[int] = []
    for seconds in sample_times(info["duration"], args.count):
        idx = frame_index_at(seconds, info["fps"], info["frames"])
        if idx not in indices:
            indices.append(idx)
    frames: typing.Dict[int, typing.Any] = {}
    for idx in indices:
        seconds = idx / info["fps"] if info["fps"] > 0 else 0.0
        rgb = read_frame(src, idx, info)
        frames[idx] = rgb
        out_path = out_dir / ("%s_t%05.2f_f%06d.png" % (name, seconds, idx))
        save_rgb(out_path, rgb)
        print("  [关键帧] %s" % out_path.name)

    first_idx, last_idx = indices[0], indices[-1]
    first = frames[first_idx]
    first_mask = auto_bg_mask(first, bg, args.bg_tol)
    code = 0

    # 2) 自循环核验（首帧 vs 末帧）—— 循环素材的核心指标
    if args.check_loop:
        print("")
        if first_idx == last_idx:
            print("[循环核验] 只抽到 1 帧，无法核验（--count 至少 2）")
        else:
            stats = diff_stats(first, frames[last_idx], bg_mask=first_mask)
            judge = loop_verdict(stats)
            title = "[循环核验] %s  首帧 f%d vs 末帧 f%d" % (name, first_idx, last_idx)
            for line in report_lines(title, stats, judge):
                print(line)
            png = out_dir / ("%s_loop_check.png" % name)
            ok = compose_compare([first, frames[last_idx], heat_image(first, frames[last_idx])],
                                 ["首帧 f%d" % first_idx, "末帧 f%d" % last_idx, "差异热力 x4"], png)
            print("    对比图: %s" % (png.name if ok else "(跳过：需 Pillow)"))
            if judge == "FAIL":
                code = 1

    # 3) 跨素材一致性核验（首帧 vs 参考图）—— 9 态切换不跳大小的保证
    if args.ref:
        print("")
        ref = _load_ref(Path(args.ref))
        if ref.shape[:2] != first.shape[:2]:
            print("[一致性核验] 跳过：尺寸不一致 首帧 %s vs 参考图 %s"
                  % (tuple(first.shape[:2]), tuple(ref.shape[:2])))
        else:
            stats = diff_stats(first, ref, bg_mask=first_mask)
            judge = ref_verdict(stats)
            title = "[一致性核验] %s 首帧 f%d vs 参考图 %s" % (name, first_idx,
                                                        Path(args.ref).name)
            for line in report_lines(title, stats, judge):
                print(line)
            png = out_dir / ("%s_ref_check.png" % name)
            ok = compose_compare([first, ref, heat_image(first, ref)],
                                 ["首帧 f%d" % first_idx, "参考图", "差异热力 x4"], png)
            print("    对比图: %s" % (png.name if ok else "(跳过：需 Pillow)"))
            if judge == "FAIL":
                code = 1

    # 4) 最佳循环点（可选）：找与首帧最接近的帧 → 尾帧锚点 / 裁剪建议
    if args.find_loop:
        print("")
        found = scan_best_loop(src, info, first, bg_mask=first_mask)
        if not found:
            print("[最佳循环点] 扫描失败（源不可读？）")
        else:
            best_idx = int(found["index"])
            best_seconds = best_idx / info["fps"] if info["fps"] > 0 else 0.0
            best_rgb = read_frame(src, best_idx, info)
            stats = diff_stats(first, best_rgb, bg_mask=first_mask)
            judge = loop_verdict(stats)
            title = "[最佳循环点] %s  首帧 f0 vs f%d（t=%.2fs）" % (name, best_idx, best_seconds)
            for line in report_lines(title, stats, judge):
                print(line)
            best_png = out_dir / ("%s_loop_best_f%06d.png" % (name, best_idx))
            save_rgb(best_png, best_rgb)
            ok = compose_compare([first, best_rgb, heat_image(first, best_rgb)],
                                 ["首帧 f0", "最佳循环帧 f%d" % best_idx, "差异热力 x4"],
                                 out_dir / ("%s_loop_best_check.png" % name))
            print("    最佳帧: %s%s" % (best_png.name, "" if ok else "（对比图跳过：需 Pillow）"))
            print("    用法: ① 当 Seedance 的**尾帧**参考；"
                  "② 已生成素材按 f0..f%d（%.2fs）裁剪，循环更顺。" % (best_idx, best_seconds))
            if judge == "FAIL":
                code = 1

    print("")
    print("[完成] %s" % ("全部通过（PASS/WARN）" if code == 0 else "存在 FAIL 项，见上"))
    return code


if __name__ == "__main__":
    sys.exit(main())
