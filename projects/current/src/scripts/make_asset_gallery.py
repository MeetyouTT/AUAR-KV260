# -*- coding: utf-8 -*-
"""make_asset_gallery —— 生成玩偶素材的**效果图证据**（动图 / 帧带 / 画质对比 / 板端帧流自检 / 面板实拍）。

用途：入库素材（降清晰度 + 降帧率）到底"能不能看、在面板里是什么样、板端帧流对不对"，
用图片一次性讲清楚，也便于交付评审时留证。

产出（默认落 `evidence_shots/`）：
    avatar_sheet_<素材名>.png      入库帧带（等距取 8 帧，带帧号/时刻）
    avatar_loop_<素材名>.gif       循环动图（按 meta.json 的 fps 播放，可看真实观感）
    avatar_quality_<素材名>.png    原分辨率抠像 vs 入库素材 的画质对比（含 1:1 局部放大）
    avatar_rgb565_<素材名>.png     板端 RGB565 帧流自检（现场编码→解码回图 + 色差统计）
    avatar_panel_<素材名>.png      玩偶面板实拍（可选，多时刻横向拼接）

依赖：Pillow（生成图）+ PySide6（仅 `--panel-at` 时通过 subprocess 调用预览脚本）。
用法：
    python scripts/make_asset_gallery.py --name idle_normal --panel-at 0,1.5,3
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from board.interaction import avatar_assets, avatar_lod  # noqa: E402
from scripts.prepare_avatar_frames import frame_files  # noqa: E402

BG = (16, 20, 28)            # 深色底（与 UI 一致，便于看透明边缘）
FG = (228, 232, 240)
ACCENT = (94, 160, 255)
FONT_CANDIDATES = (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf")


def _font(size: int):
    from PIL import ImageFont

    for path in FONT_CANDIDATES:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _flatten(image, bg=BG):
    """RGBA → RGB（合成到深色底，模拟面板背景）。"""
    from PIL import Image

    canvas = Image.new("RGB", image.size, bg)
    canvas.paste(image, (0, 0), image if image.mode == "RGBA" else None)
    return canvas


def _label_strip(width: int, text: str, height: int = 24):
    """生成一条带文字的标签条（深色底 + 居中文字）。"""
    from PIL import Image, ImageDraw

    strip = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(strip)
    font = _font(15)
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((width - (box[2] - box[0])) / 2 - box[0], (height - (box[3] - box[1])) / 2 - box[1]),
              text, font=font, fill=FG)
    return strip


def _pick(frames, count: int):
    """等距取 count 帧（含首帧，不含重复）。"""
    if len(frames) <= count:
        return list(enumerate(frames))
    step = (len(frames) - 1) / float(count - 1)
    seen: list = []
    for i in range(count):
        index = int(round(i * step))
        seen.append((index, frames[index]))
    return seen


# --------------------------------------------------------------------------- #
# 1) 帧带（等距 8 帧 + 帧号/时刻）
# --------------------------------------------------------------------------- #
def make_sheet(frames, fps: float, out_path: Path, cols: int = 8,
               title: str = "") -> Path:
    from PIL import Image

    picked = _pick(frames, cols)
    cell_w, cell_h = Image.open(picked[0][1]).size
    gap, strip_h, head_h = 10, 24, 34
    width = gap + cols * (cell_w + gap)
    height = head_h + cell_h + strip_h + gap

    sheet = Image.new("RGB", (width, height), BG)
    sheet.paste(_label_strip(width, title, head_h).crop((0, 0, width, head_h)),
                (0, 0))
    for i, (index, path) in enumerate(picked):
        x = gap + i * (cell_w + gap)
        frame = _flatten(Image.open(path).convert("RGBA"))
        sheet.paste(frame, (x, head_h))
        sheet.paste(_label_strip(cell_w, "#%03d  %.2fs" % (index, index / fps)),
                    (x, head_h + cell_h))
    sheet.save(out_path)
    return out_path


# --------------------------------------------------------------------------- #
# 2) 循环动图（delay = 1000/fps ms，忠实还原入库帧率下的观感）
# --------------------------------------------------------------------------- #
def make_gif(frames, fps: float, out_path: Path, scale: float = 1.0) -> Path:
    from PIL import Image

    delay = max(20, int(round(1000.0 / max(1e-6, fps))))
    images = []
    for path in frames:
        img = _flatten(Image.open(path).convert("RGBA"))
        if abs(scale - 1.0) > 1e-6:
            size = (max(2, int(img.width * scale)), max(2, int(img.height * scale)))
            img = img.resize(size, Image.LANCZOS)
        images.append(img)
    images[0].save(out_path, save_all=True, append_images=images[1:],
                   duration=delay, loop=0, optimize=True, disposal=2)
    return out_path


# --------------------------------------------------------------------------- #
# 3) 画质对比（整体同尺寸 + 同一部位的像素级放大）
# --------------------------------------------------------------------------- #
def _alpha_bbox(image):
    """RGBA 图的前景包围盒（用 alpha 通道；失败则整幅）。"""
    alpha = image.getchannel("A")
    box = alpha.point(lambda v: 255 if v >= 32 else 0).getbbox()
    return box or (0, 0, image.width, image.height)


def make_quality(lod_path: Path, original_path: Path, out_path: Path,
                 zoom: float = 2.0, title: str = "") -> Path:
    """`原分辨率抠像` vs `入库帧`：左=整体等尺寸对比，右=头脸部位 1:1 像素放大。

    故意用 **NEAREST** 放大，让"降清晰度"的代价（块状/糊）看得见。
    """
    from PIL import Image, ImageDraw

    lod = Image.open(lod_path).convert("RGBA")
    orig = Image.open(original_path).convert("RGBA")
    ratio = lod.width / float(orig.width)          # 720→180 = 0.25

    # a) 整体：原图缩到入库尺寸后并排（尺寸/构图是否一致）
    disp_orig = orig.resize(lod.size, Image.LANCZOS)
    # b) 头脸部位：原图按 zoom 放大、入库按 zoom/ratio 放大（同一部位、同一输出尺寸）
    bx0, by0, bx1, by1 = _alpha_bbox(orig)
    bw, bh = bx1 - bx0, by1 - by0
    face = (int(bx0 + 0.30 * bw), int(by0 + 0.06 * bh),
            int(bx0 + 0.70 * bw), int(by0 + 0.32 * bh))
    crop_orig = orig.crop(face)
    crop_lod = lod.crop(tuple(int(v * ratio) for v in face))
    target = (int(crop_orig.width * zoom), int(crop_orig.height * zoom))
    zoom_lod = (target[0] / crop_lod.width, target[1] / crop_lod.height)
    big_orig = crop_orig.resize(target, Image.NEAREST)
    big_lod = crop_lod.resize((max(2, int(crop_lod.width * zoom_lod[0])),
                               max(2, int(crop_lod.height * zoom_lod[1]))),
                              Image.NEAREST)

    gap, strip_h, head_h = 12, 24, 34
    col_w = max(lod.width, target[0])
    width = gap + col_w * 2 + gap
    height = head_h + lod.height + strip_h + gap + target[1] + strip_h + gap
    canvas = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(canvas)
    draw.text((gap, 8), title, font=_font(16), fill=ACCENT)

    def place(img, col, top, label):
        x = gap + col * (col_w + gap) if col else gap
        x += (col_w - img.width) // 2
        canvas.paste(_flatten(img), (x, top))
        canvas.paste(_label_strip(col_w, label), (gap + col * (col_w + gap), top + img.height))

    place(disp_orig, 0, head_h, "原始 720x1280 -> 等比缩到入库尺寸")
    place(lod, 1, head_h, "入库素材 180x320（1:1，播放用的就是它）")
    top2 = head_h + lod.height + strip_h + gap
    place(big_orig, 0, top2, "原始 头脸 1:1 x%.1f" % zoom)
    place(big_lod, 1, top2, "入库 头脸 1:1 x%.1f（看到的真实像素）"
          % (zoom / ratio))
    canvas.save(out_path)
    return out_path


# --------------------------------------------------------------------------- #
# 4) 板端 RGB565 帧流自检（现场编码 → 解码回图 + 色差统计）
# --------------------------------------------------------------------------- #
def rgb565_decode(data: bytes, width: int, height: int):
    """大端 R5G6B5 字节流 → PIL RGB 图（板端读到的就是这份像素）。"""
    import array

    from PIL import Image

    vals = array.array("H")
    vals.frombytes(bytes(data[: width * height * 2]))
    if sys.byteorder == "little":
        vals.byteswap()
    buf = bytearray(width * height * 3)
    for i, v in enumerate(vals):
        o = i * 3
        buf[o] = ((v >> 11) & 0x1F) * 255 // 31
        buf[o + 1] = ((v >> 5) & 0x3F) * 255 // 63
        buf[o + 2] = (v & 0x1F) * 255 // 31
    return Image.frombytes("RGB", (width, height), bytes(buf))


def make_rgb565_check(frames, fps: float, out_path: Path, count: int = 4,
                      title: str = "") -> tuple:
    """把入库 PNG 现场编成板端 RGB565（大端 / alpha<128 置黑）→ 解码回图 + 色差统计。"""
    from PIL import Image, ImageChops, ImageStat

    from scripts.prepare_avatar_frames import rgba_to_rgb565

    picked = _pick(frames, count)
    width, height = Image.open(frames[0]).size
    tiles, labels = [], []
    for index, path in picked:
        rgba = Image.open(path).convert("RGBA")
        blob = rgba_to_rgb565(rgba.tobytes(), width, height, width * 4, None)
        back = rgb565_decode(blob, width, height)
        diff = ImageChops.difference(back, _flatten(rgba))
        mean = sum(ImageStat.Stat(diff).mean) / 3.0
        peak = max(mx for _mn, mx in diff.getextrema())
        tiles.append(back)
        labels.append("#%03d  mean=%.1f peak=%d" % (index, mean, peak))

    gap, strip_h, head_h = 10, 24, 34
    width_total = gap + count * (width + gap)
    height_total = head_h + height + strip_h + gap
    canvas = Image.new("RGB", (width_total, height_total), BG)
    from PIL import ImageDraw

    ImageDraw.Draw(canvas).text((gap, 8), title, font=_font(16), fill=ACCENT)
    for i, tile in enumerate(tiles):
        x = gap + i * (width + gap)
        canvas.paste(tile, (x, head_h))
        canvas.paste(_label_strip(width, labels[i]), (x, head_h + height))
    canvas.save(out_path)
    return out_path, labels


# --------------------------------------------------------------------------- #
# 5) 面板实拍（复用 examples/preview_avatar_frames.py，多个时刻拼接）
# --------------------------------------------------------------------------- #
def make_panel(times, out_path: Path, frames_root=None, state: str = "IDLE",
               scale: float = 0.5, title: str = "") -> Path:
    from PIL import Image, ImageDraw

    preview = _ROOT / "examples" / "preview_avatar_frames.py"
    if not preview.is_file():
        raise SystemExit("找不到预览脚本: %s" % preview)

    with tempfile.TemporaryDirectory() as tmp:
        shots = []
        for t in times:
            shot = Path(tmp) / ("t%s.png" % str(t).replace(".", "_"))
            cmd = [sys.executable, str(preview), "--state", state,
                   "--at", str(t), "--screenshot", str(shot)]
            if frames_root:
                cmd += ["--frames-root", str(frames_root)]
            subprocess.run(cmd, cwd=str(_ROOT), check=True)
            img = Image.open(shot).convert("RGB")
            shots.append((t, img.resize((max(2, int(img.width * scale)),
                                         max(2, int(img.height * scale))),
                                        Image.LANCZOS)))

        gap, strip_h, head_h = 10, 24, 34
        cols = len(shots)
        cell_w, cell_h = shots[0][1].size
        canvas = Image.new("RGB", (gap + cols * (cell_w + gap),
                                   head_h + cell_h + strip_h + gap), BG)
        ImageDraw.Draw(canvas).text((gap, 8), title, font=_font(16), fill=ACCENT)
        for i, (t, img) in enumerate(shots):
            x = gap + i * (cell_w + gap)
            canvas.paste(img, (x, head_h))
            canvas.paste(_label_strip(cell_w, "t=%.2fs" % t),
                         (x, head_h + cell_h))
        canvas.save(out_path)
    return out_path


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="玩偶素材效果图：动图 / 帧带 / 画质对比 / 板端帧流自检 / 面板实拍")
    ap.add_argument("--name", default="idle_normal", help="素材名（默认 %(default)s）")
    ap.add_argument("--frames-root", default=None,
                    help="素材根目录（默认工程 assets/avatar）")
    ap.add_argument("--out-dir", default="evidence_shots",
                    help="输出目录（默认 %(default)s）")
    ap.add_argument("--state", default="IDLE",
                    help="面板实拍用的运行时状态（默认 %(default)s）")
    ap.add_argument("--sheet-cols", type=int, default=8,
                    help="帧带列数（默认 %(default)s）")
    ap.add_argument("--gif", dest="gif", action="store_true", default=True,
                    help="生成循环动图（默认开）")
    ap.add_argument("--no-gif", dest="gif", action="store_false",
                    help="不生成动图")
    ap.add_argument("--gif-scale", type=float, default=1.0,
                    help="动图缩放（默认 %(default)s）")
    ap.add_argument("--original", default=None,
                    help="原始（未降采样）抠像帧目录，用于画质对比；"
                         "默认自动探测 %%TEMP%%\\wujing_avatar_demo\\<素材名>")
    ap.add_argument("--no-quality", action="store_true", help="跳过画质对比")
    ap.add_argument("--no-rgb565", action="store_true", help="跳过板端帧流自检")
    ap.add_argument("--panel-at", default="",
                    help="面板实拍时刻，逗号分隔（如 0,1.5,3）；默认不拍")
    ap.add_argument("--panel-scale", type=float, default=0.5,
                    help="面板截图缩放（默认 %(default)s）")
    return ap


def _mib(num_bytes: int) -> str:
    return "%.2f MiB" % (num_bytes / (1024.0 * 1024.0))


def main(argv: typing.Optional[typing.List[str]] = None) -> int:
    from PIL import Image

    args = build_parser().parse_args(argv)
    directory = avatar_assets.asset_dir(args.name, root=args.frames_root or None)
    frames = frame_files(directory)
    if not frames:
        raise SystemExit("未找到素材帧: %s" % directory)

    fps = avatar_assets.frames_fps(directory)
    total = sum(p.stat().st_size for p in frames)
    size = Image.open(frames[0]).size
    title = "%s  %dx%d  @%.2ffps  %d 帧  %s" % (
        args.name, size[0], size[1], fps, len(frames), _mib(total))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    print("素材: %s" % directory)
    print(title)
    made: typing.List[Path] = []

    made.append(make_sheet(frames, fps,
                           out_dir / ("avatar_sheet_%s.png" % args.name),
                           args.sheet_cols,
                           title + "   —— 入库帧带（等距 %d 帧）" % args.sheet_cols))
    if args.gif:
        made.append(make_gif(frames, fps,
                             out_dir / ("avatar_loop_%s.gif" % args.name),
                             args.gif_scale))

    original = Path(args.original) if args.original else (
        Path(tempfile.gettempdir()) / "wujing_avatar_demo" / args.name)
    if not args.no_quality:
        orig_frames = frame_files(original)
        if orig_frames:
            made.append(make_quality(
                frames[0], orig_frames[0],
                out_dir / ("avatar_quality_%s.png" % args.name),
                title=title + "   —— 降清晰度的代价"))
        else:
            print("[提示] 未找到原始帧目录（%s），跳过画质对比" % original)

    if not args.no_rgb565:
        path, labels = make_rgb565_check(
            frames, fps, out_dir / ("avatar_rgb565_%s.png" % args.name),
            title=title + "   —— 板端 RGB565 帧流（现场编码→解码回图）")
        made.append(path)
        print("  RGB565 色差: %s" % " | ".join(labels))

    if args.panel_at.strip():
        times = [float(t) for t in args.panel_at.split(",") if t.strip()]
        made.append(make_panel(
            times, out_dir / ("avatar_panel_%s.png" % args.name),
            frames_root=args.frames_root, state=args.state,
            scale=args.panel_scale,
            title=title + "   —— 玩偶面板实拍（%s）" % args.state))

    for path in made:
        print("  %-32s %s" % (path.name, _mib(path.stat().st_size)))
    print("\n[完成] 共 %d 张效果图 → %s" % (len(made), out_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())


