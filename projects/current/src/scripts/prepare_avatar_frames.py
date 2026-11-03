# -*- coding: utf-8 -*-
"""prepare_avatar_frames —— 绿幕素材 → **板端可跑**的入库帧序列（降清晰度 + 降帧率）。

## 约定（团队决策：原始素材不动，入库素材降采样）
- **原始素材保持不变**：脚本只*读*原始绿幕 mp4（并记录其 sha256 指纹），**从不修改它**；
- **入库素材降采样**：等比缩放到「长边 ≤ `--max-side`」+ 按 `--fps` 抽帧，
  目标是**在开发板上流畅运行**（规格与实测体积表见 `board/interaction/avatar_lod.py` 与
  `docs/玩偶帧序列素材接入_技术记录.md` 第 5.4 节）；
- 产物落 `assets/avatar/<素材名>/`：`000000.png…` + `meta.json` + `manifest.json`（sha256 清单）。

## 流程
    原始绿幕 mp4（或**未抠的绿幕帧目录**，加 --matte-src）─(桌宠 src.matting
    -m adaptive video|folder 抠像 → %TEMP% 全分辨率 RGBA 帧)─▶
    强化去绿（scripts/despill_frames.py：A 硬限绿 + D1 蓝发去青，--post-despill）─▶
    按时间抽帧 + QImage 平滑缩放 ─▶ assets/avatar/<素材名>/000000.png…

## 用法
    # 单状态（--state 自动映射素材名，见 avatar_assets.STATE_ASSET）
    python scripts/prepare_avatar_frames.py --state IDLE --src "...\\idle_normal.mp4"

    # 批量：目录内每个 <素材名>.mp4 → assets/avatar/<素材名>/
    python scripts/prepare_avatar_frames.py --src "D:\\...\\绿幕素材"

    # 只打印规格与体积预估（不生成）
    python scripts/prepare_avatar_frames.py --state IDLE --src x.mp4 --dry-run

    # 交付前校验已入库素材与 manifest 是否一致
    python scripts/prepare_avatar_frames.py --verify

环境标签：PC / SIMULATED（生成阶段）；产物供板端 LVGL 复用。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import typing
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from board.interaction import avatar_assets, avatar_lod  # noqa: E402

DEFAULT_MATTING_PROJECT = Path(r"D:\share、\项目开发\桌面AI桌宠")
FRAME_FORMATS = ("png", "rgb565")


def parse_formats(text: str) -> typing.Tuple[str, ...]:
    """`--formats png,rgb565` → 元组（PNG 始终保留：PC 端显示也需要）。"""
    items = [t.strip().lower() for t in str(text).split(",") if t.strip()]
    bad = [t for t in items if t not in FRAME_FORMATS]
    if bad:
        raise SystemExit("--formats 非法值 %s（可选：%s）"
                         % (bad, " / ".join(FRAME_FORMATS)))
    if "png" not in items:
        items.append("png")
    return tuple(dict.fromkeys(items))


def parse_bg(text: typing.Optional[str]) -> typing.Optional[typing.Tuple[int, int, int]]:
    """`--rgb565-bg RRGGBB` → (R,G,B)；空值返回 None（透明像素置黑）。"""
    if not text:
        return None
    s = str(text).strip().lstrip("#")
    if len(s) != 6:
        raise SystemExit("--rgb565-bg 应为 6 位 hex（如 00FF00），收到: %r" % text)
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError:
        raise SystemExit("--rgb565-bg 非法: %r" % text)


def image_size(path: Path) -> typing.Tuple[int, int]:
    """读图片尺寸（**Pillow 优先**：本机便携 Python 无 PySide6 时的回退路径）。"""
    try:
        from PIL import Image
        with Image.open(path) as im:
            return int(im.width), int(im.height)
    except ImportError:
        from PySide6.QtGui import QImage
        image = QImage(str(path))
        if image.isNull():
            raise SystemExit("无法读取源帧: %s" % path)
        return image.width(), image.height()


def write_scaled_frame(src_path: Path, out_path: Path, crop, size) -> bool:
    """读源帧 → 纵向裁切 → 平滑缩放 → 写 PNG（**Pillow 优先**，PySide6 回退）。

    语义与原来的 QImage 路径一致：`crop` = (x, y, w, h) 绝对框，`size` 已是目标尺寸
    （等比换算在 `plan_spec` 内完成），故此处是 IgnoreAspectRatio 语义的直接 resize。
    """
    cx, cy, cw, ch = crop
    try:
        from PIL import Image
    except ImportError:
        Image = None                                  # type: ignore[assignment]
    if Image is not None:
        with Image.open(src_path) as im:
            im = im.convert("RGBA")
            if (cw, ch) != (im.width, im.height):
                im = im.crop((cx, cy, cx + cw, cy + ch))
            im = im.resize((int(size[0]), int(size[1])), Image.LANCZOS)
            im.save(str(out_path), "PNG")
        return True
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage
    image = QImage(str(src_path))
    if image.isNull():
        return False
    if (cw, ch) != (image.width(), image.height()):
        image = image.copy(cx, cy, cw, ch)
    scaled = image.scaled(int(size[0]), int(size[1]), Qt.IgnoreAspectRatio,
                          Qt.SmoothTransformation)
    return bool(scaled.save(str(out_path), "PNG"))


def rgba_bytes(path: Path) -> typing.Tuple[bytes, int, int]:
    """读 PNG → (RGBA8888 字节, 宽, 高)（**Pillow 优先**，PySide6 回退）。"""
    try:
        from PIL import Image
        with Image.open(path) as im:
            im = im.convert("RGBA")
            return im.tobytes(), im.width, im.height
    except ImportError:
        from PySide6.QtGui import QImage
        img = QImage(str(path)).convertToFormat(QImage.Format_RGBA8888)
        raw = img.constBits()
        data = raw.tobytes() if isinstance(raw, memoryview) else bytes(raw)
        return data, img.width(), img.height()


def probe_video(path: Path) -> typing.Optional[typing.Dict]:
    """探测绿幕视频（宽/高/帧率/帧数）；cv2 不可用时返回 None。"""
    try:
        import cv2
    except ImportError:
        return None
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise SystemExit("无法打开视频: %s" % path)
    try:
        return {
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": float(cap.get(cv2.CAP_PROP_FPS) or 0.0),
            "frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0),
        }
    finally:
        cap.release()


def run_matting(mp4: Path, out_dir: Path, project: Path, mode: str,
                extra: typing.Sequence[str] = ()) -> None:
    """调用桌宠 `python -m src.matting video|folder …` 抠像（**只读**原始素材）。"""
    if not (project / "src" / "matting" / "__init__.py").is_file():
        raise SystemExit("找不到桌宠 matting 工程: %s（可用 --matting-project 指定）"
                         % project)
    kind = "folder" if mp4.is_dir() else "video"   # 绿幕帧目录 → folder 子命令
    cmd = [sys.executable, "-m", "src.matting", kind, str(mp4),
           "-m", mode, "--out-dir", str(out_dir), *list(extra)]
    print("  [抠像] %s" % " ".join(cmd))
    subprocess.run(cmd, cwd=str(project), check=True)


# --------------------------------------------------------------------------- #
# RGB565（板端无 alpha 帧流）
#   与桌宠 `src/matting/export.py::rgb565_bytes` **同规则**：R5|G6|B5、大端字节序；
#   给了 background 就先把半透明边缘与底色合成，否则 alpha<128 置黑。
# --------------------------------------------------------------------------- #
def rgba_to_rgb565(rgba: bytes, width: int, height: int, bpl: int,
                   background: typing.Optional[typing.Tuple[int, int, int]] = None
                   ) -> bytes:
    """RGBA8888 像素缓冲 → RGB565 大端字节流（有 numpy 走向量化，否则纯 Python 回退）。"""
    try:
        import numpy as np
    except ImportError:
        np = None  # type: ignore[assignment]

    if np is not None:
        arr = np.frombuffer(rgba, dtype=np.uint8)
        if bpl != width * 4:                      # 行尾可能有填充
            arr = arr.reshape(height, bpl)[:, : width * 4]
        px = arr.reshape(height, width, 4).astype(np.uint16)
        r, g, b, a = px[..., 0], px[..., 1], px[..., 2], px[..., 3]
        a8 = a
        if background is not None:
            br, bg_g, bb = (int(v) for v in background)
            r = (r * a8 + br * (255 - a8) + 127) // 255
            g = (g * a8 + bg_g * (255 - a8) + 127) // 255
            b = (b * a8 + bb * (255 - a8) + 127) // 255
        else:
            keep = a8 >= 128
            r = np.where(keep, r, 0)
            g = np.where(keep, g, 0)
            b = np.where(keep, b, 0)
        v = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
        return v.astype(">u2").tobytes()

    out = bytearray(width * height * 2)
    pos = 0
    for y in range(height):
        base = y * bpl
        for x in range(width):
            o = base + x * 4
            r, g, b, a = rgba[o], rgba[o + 1], rgba[o + 2], rgba[o + 3]
            if background is not None:
                br, bg_g, bb = background
                r = (r * a + br * (255 - a) + 127) // 255
                g = (g * a + bg_g * (255 - a) + 127) // 255
                b = (b * a + bb * (255 - a) + 127) // 255
            elif a < 128:
                r = g = b = 0
            v = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
            out[pos] = (v >> 8) & 0xFF
            out[pos + 1] = v & 0xFF
            pos += 2
    return bytes(out)


def qimage_rgb565(image, background=None) -> bytes:
    """QImage → RGB565 大端字节流（内部统一转 RGBA8888）。"""
    from PySide6.QtGui import QImage

    img = image.convertToFormat(QImage.Format_RGBA8888)
    raw = img.constBits()
    data = raw.tobytes() if isinstance(raw, memoryview) else bytes(raw)
    return rgba_to_rgb565(data, img.width(), img.height(),
                          img.bytesPerLine(), background)


def frame_files(directory: Path) -> typing.List[Path]:
    """目录内帧文件（按名排序；目录不存在返回空表）。"""
    d = Path(directory)
    if not d.is_dir():
        return []
    return sorted(p for p in d.iterdir()
                  if p.is_file() and p.suffix.lower() in avatar_assets.FRAME_EXTS)


def _write_json(path: Path, payload: typing.Dict) -> None:
    """写出 UTF-8 / 缩进 2 的 JSON（便于 git diff）。"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


# --------------------------------------------------------------------------- #
# 规格规划：探测源素材 → 目标尺寸 / 抽帧索引 / 输出帧率 / 体积预算
# --------------------------------------------------------------------------- #
def source_info(src: Path, args) -> typing.Dict:
    """统一得到源素材信息 `{width, height, fps, frames, dir?}`。

    - 传视频文件：用 cv2 探测（未装 cv2 则报错退出）；
    - 传**已抠好的全分辨率帧目录**：尺寸取首帧、帧率取 `--src-fps`（默认 24）。
    """
    if src.is_file():
        info = probe_video(src)
        if info is None:
            raise SystemExit("未安装 cv2，无法探测视频（pip install opencv-python-headless）")
        if info["width"] <= 0 or info["height"] <= 0 or info["frames"] <= 0:
            raise SystemExit("视频元数据异常: %s" % info)
        if info["fps"] <= 0:
            raise SystemExit("视频帧率无效(%s)：请先把帧抠到目录，再用 "
                             "--src <目录> --src-fps <源帧率>" % info["fps"])
        return info

    if src.is_dir():
        frames = frame_files(src)
        if not frames:
            raise SystemExit("源帧目录内没有帧: %s" % src)
        width, height = image_size(frames[0])
        info = {"width": width, "height": height,
                "fps": float(args.src_fps or 24.0), "frames": len(frames),
                "dir": src}
        if getattr(args, "matte_src", False):
            # `--matte-src`：`--src` 传的是**未抠的绿幕帧目录** → 去掉 dir 标记，
            # 让主流程先跑桌宠抠像（folder 子命令）再入库。
            info.pop("dir")
        return info

    raise SystemExit("--src 不存在: %s" % src)


def plan_spec(info: typing.Dict, args) -> typing.Dict:
    """由源信息 + 规格参数算出取景裁切 / 目标尺寸 / 抽帧索引 / 输出帧率 / 体积预算，并打印。"""
    ratio = avatar_lod.parse_framing(getattr(args, "framing", "full"),
                                     getattr(args, "crop_bottom_ratio", None))
    crop = avatar_lod.crop_box(info["width"], info["height"], ratio)
    size = avatar_lod.target_size(crop[2], crop[3], args.max_side)
    if ratio > 0.0:
        print("  取景 %s：裁掉下部 %.0f%%（保留上部 %.0f%%）→ %dx%d → %dx%d（宽度不变）"
              % (getattr(args, "framing", "full"), ratio * 100.0,
                 (1.0 - ratio) * 100.0, info["width"], info["height"],
                 crop[2], crop[3]))
    if args.fit_budget:                    # 自动挑「能装进预算的最高帧率」
        fit = avatar_lod.fit_to_budget(info["fps"], info["frames"], size,
                                       args.formats, args.budget_mb)
        if abs(fit["fps"] - args.fps) > 1e-9:
            print("  [预算自适应] %.1ffps → %.1ffps（%d 帧，预计 %.2f MiB）"
                  % (args.fps, fit["fps"], fit["frames"],
                     fit["report"]["total_mb"]))
            args.fps = fit["fps"]
    indices = avatar_lod.select_indices(info["frames"], info["fps"], args.fps)
    fps_out = avatar_lod.effective_fps(info["fps"], info["frames"], len(indices))
    burst = int(getattr(args, "burst_frames", 0) or 0)
    if burst > 0 and len(indices) > burst:
        # burst 一次性动作素材：只留前 N 帧。**帧率不重算**——effective_fps 是按
        # "等距抽帧"推断的，截断后帧间距不再是等距，重算会得到 ~13fps 的假帧率，
        # 播放时 0.92s 的动作会被拖成 1.6s 慢动作（状态系统重设计 §1.1 判据②）。
        indices = indices[:burst]
        print("  [burst] 一次性动作：只取前 %d 帧（帧率保持 %.2ffps，时长 %.2fs）"
              % (len(indices), fps_out, len(indices) / fps_out))
    report = avatar_lod.budget_report(len(indices), size, args.formats, args.budget_mb)
    src_px = info["width"] * info["height"]
    dst_px = max(1, size[0] * size[1])
    print("  源 %dx%d @%.2ffps / %d 帧  →  入库 %dx%d @%.2ffps / %d 帧（像素量 1/%.1f）"
          % (info["width"], info["height"], info["fps"], info["frames"],
             size[0], size[1], fps_out, len(indices), src_px / float(dst_px)))
    print("  体积预估: %s → 合计 %.2f MiB（预算 %.1f MiB）%s"
          % (" + ".join("%s %.2f MiB" % (k.upper(), avatar_lod.mib(v))
                        for k, v in report["per_format_bytes"].items()),
             report["total_mb"], report["budget_mb"],
             "  [超预算]" if report["over_budget"] else "  [OK]"))
    if report["over_budget"]:
        fit = avatar_lod.fit_to_budget(info["fps"], info["frames"], size,
                                       args.formats, args.budget_mb)
        if fit["fits"]:
            print("  [建议] 加 --fit-budget 可自动降到 %.1f fps（%d 帧 ≈ %.2f MiB）；"
                  "或调小 --max-side（当前 %s）"
                  % (fit["fps"], fit["frames"], fit["report"]["total_mb"],
                     args.max_side))
        else:
            print("  [建议] 该尺寸下仍装不下预算：请调小 --max-side（当前 %s）"
                  % args.max_side)
    return {"size": size, "indices": indices, "fps": fps_out, "budget": report,
            "crop": crop, "crop_bottom_ratio": ratio,
            "framing": getattr(args, "framing", "full")}


# --------------------------------------------------------------------------- #
# 生成单个素材
# --------------------------------------------------------------------------- #
def prepare_one(name: str, src: Path, args, root: Path) -> int:
    """生成单个素材：抠像（只读原始素材）→ 抽帧缩放 → meta.json / manifest.json。"""
    print("\n=== [%s] %s" % (name, src))
    out_dir = root / name
    existing = frame_files(out_dir)
    if existing and not args.force:
        print("  [跳过] 已有 %d 帧（加 --force 覆盖）: %s" % (len(existing), out_dir))
        return 0

    info = source_info(src, args)
    plan = plan_spec(info, args)
    if args.dry_run:
        print("  [dry-run] 未生成任何文件")
        return 0

    # 原始素材指纹：**在抠像之前**记录，证明入库产物对应的就是这份原始素材
    src_meta: typing.Dict = {"path": str(src), "width": info["width"],
                             "height": info["height"], "fps": info["fps"],
                             "frames": info["frames"]}
    if src.is_file():
        src_meta["bytes"] = int(src.stat().st_size)
        src_meta["sha256"] = avatar_lod.sha256_file(src)

    # 1) 需要时先抠像到临时目录（原始素材只读；中间产物用完即删）
    src_dir = info.get("dir")
    temp_dir: typing.Optional[Path] = None
    if src_dir is None:
        temp_dir = (Path(args.temp_dir) / name if args.temp_dir else
                    Path(tempfile.gettempdir()) / "wujing_avatar_prep" / name)
        if temp_dir.is_dir():
            shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        run_matting(src, temp_dir, Path(args.matting_project), args.mode,
                    args.matting_arg)
        # 1.5) 强化去绿：只作用于**临时目录**里的抠像产物（原始素材与用户目录永不改写）
        if args.post_despill != "off":
            from scripts.despill_frames import despill_dir
            n = despill_dir(temp_dir, limit_green=True,
                            decyan=(args.post_despill == "ad1"),
                            q_min=args.decyan_q_min, q_max=args.decyan_q_max,
                            progress=print)
            print("  [去绿] %d 帧（A 硬限绿%s）"
                  % (n, " + D1 蓝发去青" if args.post_despill == "ad1" else ""))
        src_dir = temp_dir

    frames = frame_files(Path(src_dir))
    if not frames:
        raise SystemExit("抠像后未产出帧: %s" % src_dir)
    picked = [frames[i] for i in plan["indices"] if i < len(frames)]
    if len(picked) != len(plan["indices"]):
        print("  [警告] 实际解码 %d 帧 < 元数据 %d 帧，入库 %d 帧"
              % (len(frames), info["frames"], len(picked)))

    # 2) 取景裁切（腰部以上）→ 抽帧 + 平滑缩放 → 入库 PNG
    #    裁切发生在缩放**之前**且只裁纵向 → 等比缩放倍率不变（无插值放大失真）
    out_dir.mkdir(parents=True, exist_ok=True)
    written: typing.List[Path] = []
    for i, path in enumerate(picked):
        out_path = out_dir / ("%06d.png" % i)
        if not write_scaled_frame(path, out_path, plan["crop"], plan["size"]):
            print("  [警告] 跳过无法读取的帧: %s" % path.name)
            continue
        written.append(out_path)
    if not written:
        raise SystemExit("未写出任何帧")
    print("  [写入] %d 帧 PNG → %s" % (len(written), out_dir))

    # 3) 可选：板端无 alpha 帧流（RGB565，大端）
    if "rgb565" in args.formats:
        blob = out_dir / "frames.rgb565"
        with open(blob, "wb") as f:
            for path in written:
                data, w, h = rgba_bytes(path)
                f.write(rgba_to_rgb565(data, w, h, w * 4, args.bg))
        print("  [写入] %s（%.2f MiB，大端 R5G6B5%s）"
              % (blob.name, avatar_lod.mib(blob.stat().st_size),
                 "，已按底色合成" if args.bg else "，alpha<128 置黑"))

    # 4) meta.json + manifest.json（不含时间戳 → 同输入同产物）
    meta = avatar_lod.build_meta(
        name, plan["fps"], plan["size"], len(written),
        spec={"max_side": args.max_side, "fps": args.fps,
              "fit_budget": bool(args.fit_budget),
              "burst_frames": int(getattr(args, "burst_frames", 0) or 0),
              "framing": plan["framing"],
              "crop_bottom_ratio": plan["crop_bottom_ratio"],
              "formats": list(args.formats), "matte_mode": args.mode,
              "tool": "scripts/prepare_avatar_frames.py"},
        source=src_meta)
    _write_json(out_dir / "meta.json", meta)
    entries = avatar_lod.manifest_entries(written)
    _write_json(out_dir / avatar_lod.MANIFEST_NAME,
                avatar_lod.build_manifest(name, entries))
    actual = sum(int(e["bytes"]) for e in entries)
    print("  [清单] %s：%d 项 / 实际 %.2f MiB（预估 %.2f MiB）"
          % (avatar_lod.MANIFEST_NAME, len(entries),
             avatar_lod.mib(actual), plan["budget"]["total_mb"]))

    # 5) 清理中间目录（原始素材始终未被改动）
    if temp_dir is not None and not args.keep_temp:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("  [清理] 已删除中间目录 %s（--keep-temp 保留；原始素材未改动）" % temp_dir)
    return 0


# --------------------------------------------------------------------------- #
# 排队期进度看板（--status）：素材逐条产出时"哪几态已有 / 还缺 / 取景对不对"
# --------------------------------------------------------------------------- #
def status_all(root: Path) -> int:
    """打印 9 态素材的入库状态（帧数 / 尺寸 / 取景 / 体积 / 清单），返回 0。

    排队期用途：素材通常**逐条**产出（生成渠道排队），本命令一眼看出缺哪几态；
    并显式标出取景口径是否已是板端定稿的 `waist-up`，避免"帧齐了但要重跑"。
    """
    states = avatar_assets.STATE_ASSET
    asset_names = sorted(set(states.values()))
    have: typing.List[str] = []
    print("素材入库状态（根目录: %s）" % root)
    print("  %-20s %-6s %-11s %-9s %-10s %s"
          % ("素材名", "帧数", "尺寸", "取景", "体积", "状态"))
    for name in asset_names:
        directory = root / name
        frames = frame_files(directory)
        meta: typing.Optional[typing.Dict] = None
        meta_path = directory / "meta.json"
        if meta_path.is_file():
            try:
                with open(meta_path, encoding="utf-8") as f:
                    meta = json.load(f)
            except (OSError, ValueError):
                meta = None
        if not frames:
            print("  %-20s %-6s %-11s %-9s %-10s %s"
                  % (name, "-", "-", "-", "-", "[缺失] 待产出"))
            continue
        have.append(name)
        spec = (meta or {}).get("spec") or {}
        framing = str(spec.get("framing") or "full")
        size = (meta or {}).get("size") or ["?", "?"]
        total = sum(p.stat().st_size for p in frames)
        manifest = avatar_lod.read_manifest(directory)
        flag = "[OK] 已入库" if manifest is not None else "[警告] 缺 manifest（跑 --verify）"
        if framing != "waist-up":
            flag += "／取景=%s ≠ 板端 waist-up" % framing
        print("  %-20s %-6d %-11s %-9s %-10s %s"
              % (name, len(frames), "%sx%s" % (size[0], size[1]), framing,
                 "%.1f MiB" % avatar_lod.mib(total), flag))

    missing = [n for n in asset_names if n not in have]
    print("  小计：%d/%d 个素材目录已入库%s"
          % (len(have), len(asset_names),
             "" if not missing else "；缺少：" + ", ".join(missing)))
    missing_states = sorted(s for s, a in states.items() if a in missing)
    if missing_states:
        print("  待产出状态：%s" % ", ".join(missing_states))
    else:
        print("  9 态素材齐备 → 可跑 `--verify` 与 `python examples/run_ui.py --all-states`")
    return 0


# --------------------------------------------------------------------------- #
# 校验（交付前 / CI）
# --------------------------------------------------------------------------- #
def verify_all(root: Path, only: typing.Optional[str] = None) -> int:
    """校验 root 下各素材目录的帧与 manifest 是否一致；返回失败个数。"""
    if not root.is_dir():
        print("入库根目录不存在: %s" % root)
        return 0
    names = [only] if only else [d.name for d in sorted(root.iterdir()) if d.is_dir()]
    if not names:
        print("未发现素材目录: %s" % root)
        return 0
    failed = 0
    for name in names:
        directory = root / name
        frames = frame_files(directory)
        if not frames:
            print("  [跳过] %s: 无帧" % name)
            continue
        result = avatar_lod.verify_manifest(directory, frames)
        if result["ok"]:
            print("  [OK] %s: %d 帧 / manifest 一致" % (name, result["checked"]))
        else:
            failed += 1
            print("  [失败] %s: 校验不一致" % name)
            for issue in result["issues"][:8]:
                print("      - %s" % issue)
    print("\n[校验结果] %s" % ("全部通过" if not failed
                               else "%d 个素材失败" % failed))
    return failed


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="绿幕素材 → 板端可跑的入库帧序列（降清晰度 + 降帧率；原始素材只读）")
    ap.add_argument("--src", default=None,
                    help="原始绿幕 mp4，或已抠好的全分辨率帧目录；"
                         "传**目录**时按 <素材名>.mp4 / <素材名>/ 批量处理")
    ap.add_argument("--name", default=None, help="素材名（如 idle_normal）")
    ap.add_argument("--state", default=None,
                    help="运行时状态（9 态之一），自动映射素材名（见 STATE_ASSET）")
    ap.add_argument("--out-root", default=str(avatar_assets.AVATAR_DIR),
                    help="入库根目录（默认 assets/avatar）")
    ap.add_argument("--max-side", type=int, default=avatar_lod.DEFAULT_MAX_SIDE,
                    help="入库长边上限（默认 %(default)s；竖屏素材即高度）")
    ap.add_argument("--fps", type=float, default=avatar_lod.DEFAULT_FPS,
                    help="入库目标帧率（默认 %(default)s）")
    ap.add_argument("--framing", default="full",
                    choices=tuple(sorted(avatar_lod.FRAMING_PRESETS)),
                    help="取景：full=不裁切（膝上全身）；waist-up=裁掉下部 42%%"
                         "（保留上部 58%%，腰部以上，板端定稿口径）。默认 %(default)s")
    ap.add_argument("--crop-bottom-ratio", type=float, default=None, metavar="R",
                    help="自定义底部裁切比例 R∈[0,1)（覆盖 --framing，如 0.46 = 保留上部 54%%）")
    ap.add_argument("--formats", default="png",
                    help="输出格式，逗号分隔：png,rgb565（默认 png）")
    ap.add_argument("--rgb565-bg", default=None, metavar="RRGGBB",
                    help="RGB565 合成底色（默认 alpha<128 置黑）")
    ap.add_argument("--budget-mb", type=float, default=avatar_lod.DEFAULT_BUDGET_MB,
                    help="单素材体积预算 MiB（默认 %(default)s）")
    ap.add_argument("--fit-budget", action="store_true",
                    help="按 --budget-mb 自动降帧率（取能装进预算的最高帧率）")
    ap.add_argument("--src-fps", type=float, default=24.0,
                    help="--src 为帧目录时的源帧率（默认 %(default)s）")
    ap.add_argument("--matte-src", action="store_true",
                    help="--src 传的是**未抠的绿幕帧目录**：先跑桌宠 "
                         "src.matting folder 抠像，再入库（默认把帧目录当已抠好）")
    ap.add_argument("--mode", default="adaptive",
                    choices=("adaptive", "opencv", "rembg"),
                    help="桌宠抠像模式（默认 %(default)s）")
    ap.add_argument("--matting-arg", action="append", default=[],
                    help="透传给桌宠 matting 的额外参数（可重复，如 --matting-arg --gate --matting-arg 0.5）")
    ap.add_argument("--post-despill", default="ad1", choices=("off", "a", "ad1"),
                    help="抠像后强化去绿：off=不动 / a=仅 A 硬限绿 / "
                         "ad1=A 硬限绿 + D1 蓝发去青（默认；见 scripts/despill_frames.py 与 "
                         "docs/玩偶底图裁切_waistup58定稿口径_技术记录.md §9）")
    ap.add_argument("--decyan-q-min", type=float, default=0.35,
                    help="D1 蓝发去青触发阈值 q=(g-r)/(b-r)（默认 %(default)s）")
    ap.add_argument("--decyan-q-max", type=float, default=0.50,
                    help="D1 青染比上限（默认 %(default)s；越小越偏纯蓝）")
    ap.add_argument("--matting-project", default=str(DEFAULT_MATTING_PROJECT),
                    help="桌宠工程路径（提供 src/matting）")
    ap.add_argument("--temp-dir", default=None,
                    help="中间全分辨率帧目录（默认 %%TEMP%%\\wujing_avatar_prep）")
    ap.add_argument("--keep-temp", action="store_true", help="保留中间产物（排错用）")
    ap.add_argument("--burst-frames", type=int, default=0, metavar="N",
                    help="一次性动作(burst)素材：只保留前 N 帧（0=不截断；帧率不重算）")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的素材目录")
    ap.add_argument("--dry-run", action="store_true", help="只打印规格与体积预估，不生成")
    ap.add_argument("--status", action="store_true",
                    help="只看 9 态素材入库状态（排队期进度看板；不生成、不校验）")
    ap.add_argument("--verify", action="store_true",
                    help="只校验已入库素材与 manifest 是否一致")
    return ap


def _safe_stdout() -> None:
    """让 stdout 遇到无法编码的字符时用 `?` 顶替，而不是抛 UnicodeEncodeError。

    中文 Windows 控制台/重定向默认走 GBK：`✓ ⚠ ✗` 这类符号不在 GBK 内，
    不打这层保护就会在 `> log.txt` 时直接崩掉（本工具开发中真实踩过）。
    """
    stream = getattr(sys, "stdout", None)
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(errors="replace")
        except (ValueError, OSError):
            pass


def _targets(args) -> typing.List[typing.Tuple[str, Path]]:
    """把 `--src/--name/--state` 解析成 `[(素材名, 源路径)]`（支持批量目录）。"""
    if not args.src:
        raise SystemExit("需要 --src（原始绿幕 mp4 或已抠好的帧目录）")
    src = Path(args.src)
    if not src.exists():
        raise SystemExit("--src 不存在: %s" % src)
    if args.name and args.state:
        raise SystemExit("--name 与 --state 只能二选一")
    if args.name or args.state:
        name = args.name or avatar_assets.asset_name(str(args.state).upper())
        return [(name, src)]

    if src.is_dir():
        video_exts = (".mp4", ".mov", ".mkv", ".avi", ".webm")
        items: typing.List[typing.Tuple[str, Path]] = []
        for p in sorted(src.iterdir()):
            if p.is_file() and p.suffix.lower() in video_exts:
                items.append((p.stem, p))
            elif p.is_dir() and frame_files(p):
                items.append((p.name, p))
        if not items:
            raise SystemExit("批量目录内没有素材（*.mp4 或含帧的子目录）: %s" % src)
        unknown = [n for n, _ in items if n not in avatar_assets.all_asset_names()]
        if unknown:
            print("[提示] 以下素材名不在 STATE_ASSET 映射中（板端需补映射）: %s" % unknown)
        return items

    return [(src.stem, src)]


def main(argv: typing.Optional[typing.List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    _safe_stdout()
    args.formats = parse_formats(args.formats)
    args.bg = parse_bg(args.rgb565_bg)
    root = Path(args.out_root)

    if args.status:
        return status_all(root)

    if args.verify:
        return 1 if verify_all(root, args.name) else 0

    targets = _targets(args)
    print("入库根目录: %s" % root)
    print("入库规格: 长边≤%d / %s fps / 格式 %s / 单素材预算 %.1f MiB / 取景 %s / 抠像 %s"
          % (args.max_side, args.fps, "+".join(args.formats),
             args.budget_mb, args.framing, args.mode))
    code = 0
    for name, src in targets:
        code |= prepare_one(name, src, args, root)
    print("\n[完成] 处理 %d 个素材；原始素材仅被读取，未被修改" % len(targets))
    return code


if __name__ == "__main__":
    sys.exit(main())
