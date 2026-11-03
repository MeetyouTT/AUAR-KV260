# -*- coding: utf-8 -*-
"""ui_mock_draft.py —— UI 设计草案渲染器（**非交付工具**，设计定稿后可随 ADR 一起删）

用途：把「上（左上交互信息 + 右上玩偶动画）/ 下（系统信息）」三区布局假设渲染成
**可确认的图像**，并用**真实素材**（现役 `idle_normal` 全分辨率绿幕帧 → 桌宠 matting
抠像 → 按比例裁掉下部 = 腰部以上）按真实比例合成，使人物大小 / 留白 / 裁切线
都是真实数值，而不是画方块示意。

用法：
    python scripts/ui_mock_draft.py                       # 输出到 docs/ui_draft/
    python scripts/ui_mock_draft.py --out-dir <目录>
    python scripts/ui_mock_draft.py --no-matte            # 跳过抠像（复用缓存）
    python scripts/ui_mock_draft.py --matting-project <桌宠工程目录>

产物：
    board_1024x600.png   板端三区草案（主图，p=0.58 满铺）
    variants.png         玩偶区变体对比：满铺 / +8px 安全边 / p=0.54 / 不裁切

注意：
- Qt **离屏**渲染必须显式注册中文字体（`msyh.ttc`），否则中文会渲染成方框；
- 抠像沿用入库工具的做法：先把中文路径的源帧拷到 ASCII 临时路径（OpenCV imread
  读不了中文路径），再调用桌宠 `python -m src.matting image -m adaptive`；
- 只读原始素材，产物只落在 `--out-dir`。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import typing
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")   # 离屏渲染，不开窗口

from PySide6.QtCore import QRect, Qt                                   # noqa: E402
from PySide6.QtGui import (QBrush, QColor, QFont, QFontDatabase,        # noqa: E402
                           QImage, QLinearGradient, QPainter, QPen)
from PySide6.QtWidgets import QApplication                              # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "ui_draft"
DEFAULT_KEY = ROOT / "evidence_shots" / "keyframes" / "idle_normal_t00.00_f000000.png"
DEFAULT_MATTING_PROJECT = Path("D:/share/项目开发/桌面AI桌宠")
CJK_FONT_FILE = "C:/Windows/Fonts/msyh.ttc"
FONT_FAMILY = "Microsoft YaHei"

# ui_tokens.json 的颜色令牌（草案里直接内联，定稿后由合同驱动）
C = {
    "bg": "#F2F2E9", "panel_bg": "#FCFCF3", "panel_border": "#D5D5CB",
    "accent": "#0B7FC4", "success": "#2E7D32", "warning": "#E08600",
    "text_primary": "#1F242B", "text_secondary": "#5A6572",
    "box": "#0B7FC4", "zone": "#E08600", "annot": "#5A6572",
}

# 画布档：板端 1024×600（唯一交付档；PC 1280×720 档已按用户决定废弃）
PROFILES: typing.Dict[str, typing.Dict[str, typing.Any]] = {
    "board": dict(name="board_1024x600", w=1024, h=600, bar=44, left=585, pad=8,
                  video_h=300, info_h=20, label_h=24, fade=28,
                  f_video=10, f_small=11, f_dialogue=13, f_title=13),
}

CROP_BOTTOM = 0.42          # p = 0.58：保留上部 58% = 腰部以上（底部裁掉 42%）
SAFE_MARGIN = 8             # 玩偶左右安全边（避免发辫/袖口贴面板边）


# --------------------------------------------------------------------------- #
# 素材：抠像 + 裁切 + contain
# --------------------------------------------------------------------------- #
def matte_once(key: Path, matting_project: Path, cache_dir: Path) -> QImage:
    """抠一张全分辨率透明帧（缓存；只读原始素材）。"""
    dst = cache_dir / "matted_full.png"
    if not dst.is_file():
        tmp = cache_dir / "src.png"
        shutil.copyfile(key, tmp)      # OpenCV imread 读不了中文路径
        subprocess.run([sys.executable, "-m", "src.matting", "image", str(tmp),
                        "-m", "adaptive", "-o", str(dst)],
                       cwd=str(matting_project), check=True)
    return QImage(str(dst))


def crop_bottom(img: QImage, bottom_ratio: float = CROP_BOTTOM) -> QImage:
    """按比例裁掉下部（= 只保留腰部以上）。"""
    h = int(round(img.height() * (1.0 - bottom_ratio)))
    return img.copy(0, 0, img.width(), max(1, h))


def contain(img: QImage, box_w: int, box_h: int) -> QImage:
    """等比缩放到框内（KeepAspectRatio，不拉伸）。"""
    scale = min(box_w / float(img.width()), box_h / float(img.height()))
    return img.scaled(max(1, int(round(img.width() * scale))),
                      max(1, int(round(img.height() * scale))),
                      Qt.KeepAspectRatio, Qt.SmoothTransformation)


def font(size: int, bold: bool = False) -> QFont:
    return QFont(FONT_FAMILY, size, QFont.Bold if bold else QFont.Normal)


def annot(p: QPainter, x: int, y: int, text: str) -> None:
    """草稿标注（灰色小字，定稿版不会有）。"""
    p.setPen(QColor(C["annot"]))
    p.setFont(font(9))
    p.drawText(x, y, text)


# --------------------------------------------------------------------------- #
# 基础绘制原语
# --------------------------------------------------------------------------- #
def panel(p: QPainter, x0: int, y0: int, x1: int, y1: int, title: str = "") -> None:
    p.fillRect(QRect(x0, y0, x1 - x0, y1 - y0), QColor(C["panel_bg"]))
    p.setPen(QPen(QColor(C["panel_border"]), 1))
    p.drawRect(QRect(x0, y0, x1 - x0 - 1, y1 - y0 - 1))
    if title:
        p.setPen(QColor(C["text_secondary"]))
        p.setFont(font(9))
        p.drawText(x0 + 6, y0 + 12, title)


def camera(p: QPainter, r: QRect, prof: typing.Dict) -> None:
    """摄像头画面（无板阶段为占位：网格 + presence zone + 检测框）。"""
    p.fillRect(r, QColor(C["bg"]))
    p.setPen(QPen(QColor(C["panel_border"]), 1))
    for xx in range(r.x(), r.right(), 40):
        p.drawLine(xx, r.y(), xx, r.bottom())
    for yy in range(r.y(), r.bottom(), 40):
        p.drawLine(r.x(), yy, r.right(), yy)
    p.setPen(QPen(QColor(C["zone"]), 1, Qt.DashLine))
    p.drawRect(r.adjusted(6, 6, -6, -6))
    box = QRect(int(r.x() + r.width() * 0.30), int(r.y() + r.height() * 0.16),
                int(r.width() * 0.36), int(r.height() * 0.72))
    p.setPen(QPen(QColor(C["box"]), 2))
    p.drawRect(box)
    p.setFont(font(9))
    p.drawText(box.x() + 2, box.y() - 4, "person 0.91")
    p.setPen(QColor(C["text_secondary"]))
    p.setFont(font(prof["f_video"]))
    p.drawText(r.adjusted(0, 0, 0, -8), Qt.AlignHCenter | Qt.AlignBottom,
               "摄像头画面（左上·交互信息区）")


def info_panel(p: QPainter, prof: typing.Dict, x0: int, y0: int, w: int, h: int) -> None:
    """左上·交互信息：摄像头画面 + 信息行 + ASR/回复 + 延迟 + 事件流。"""
    pad, fs, fd = prof["pad"], prof["f_small"], prof["f_dialogue"]
    bottom = y0 + h - pad
    panel(p, x0, y0, x0 + w, y0 + h, "左上·交互信息（摄像头 + 交互详情）")
    ix = x0 + pad
    iw = w - 2 * pad

    y = y0 + pad + 12
    camera(p, QRect(ix, y, iw, prof["video_h"]), prof)
    y += prof["video_h"] + prof["info_h"]

    p.setPen(QColor(C["text_secondary"]))
    p.setFont(font(fs))
    p.drawText(ix, y, "people=1   seq=125   fps=28.4   camera=online   npu=ready")
    y += fs + 4
    p.setPen(QColor(C["panel_border"]))
    p.drawLine(ix, y, ix + iw, y)
    y += fs + 5

    p.setPen(QColor(C["accent"]))
    p.setFont(font(fs))
    p.drawText(ix, y, "ASR  我看到画面里有人")
    y += fd + 7
    p.setPen(QColor(C["text_primary"]))
    p.setFont(font(fd))
    for line in ("回复  我看到画面左侧有一位来访者。",
                 "需要我帮您记录这次来访吗？",
                 "（回复全文区：13px 约 60 字/行，最多 4 行）"):
        p.drawText(ix, y, line)
        y += fd + 7
    p.setPen(QColor(C["text_secondary"]))
    p.setFont(font(fs))
    p.drawText(ix, y, "端到端 180 ms | 检测 33 ms | 回复 1.2 s | 状态 LISTENING/THINKING/SPEAKING")
    y += fs
    p.setPen(QColor(C["panel_border"]))
    p.drawLine(ix, y, ix + iw, y)
    y += fs + 5

    p.setPen(QColor(C["accent"]))
    p.setFont(font(fs))
    for text in ("14:32:07  scene.person_enter  track=7",
                 "14:32:09  kws.detected  xiaojing",
                 "14:32:11  vad.end 1.4s",
                 "14:32:14  dialogue.response 1.2s"):
        p.drawText(ix, y, text)
        y += fs + 3
    if y - (fs + 3) > bottom:
        print("[警告] 左上区内容底部 %d 超出内底 %d（需再压 %d px）"
              % (y - (fs + 3), bottom, y - (fs + 3) - bottom))


def avatar_panel(p: QPainter, prof: typing.Dict, x0: int, y0: int, w: int, h: int,
                 matted: QImage, *, crop: bool = True, margin: int = 0,
                 ratio: float = CROP_BOTTOM, title: str = "") -> None:
    """右上·玩偶动画：状态标签 + 玩偶框（contain，可含安全边）+ 底部渐隐收边。"""
    pad, fade = prof["pad"], prof["fade"]
    panel(p, x0, y0, x0 + w, y0 + h, title)
    ix, iy = x0 + pad, y0 + pad
    iw, ih = w - 2 * pad, h - 2 * pad

    p.setPen(QColor(C["accent"]))
    p.setFont(font(prof["f_title"], True))
    p.drawText(QRect(ix, iy, iw, prof["label_h"]), Qt.AlignCenter, "注视 [PRESENT]")

    box = QRect(ix, iy + prof["label_h"], iw, ih - prof["label_h"])
    p.fillRect(box, QColor(C["panel_bg"]))
    p.setPen(QPen(QColor(C["panel_border"]), 1, Qt.DotLine))
    p.drawRect(box)

    source = crop_bottom(matted, ratio) if crop else matted
    image = contain(source, box.width() - 2 * margin, box.height())
    p.drawImage(box.x() + (box.width() - image.width()) // 2,
                box.y() + box.height() - image.height(), image)   # 底部对齐

    # 底部渐隐收边（透明 → 面板底色），让"腰部"自然融掉
    grad = QLinearGradient(0, box.bottom() - fade, 0, box.bottom())
    c0 = QColor(C["panel_bg"]); c0.setAlpha(0)
    c1 = QColor(C["panel_bg"]); c1.setAlpha(255)
    grad.setColorAt(0.0, c0)
    grad.setColorAt(1.0, c1)
    p.fillRect(QRect(box.x(), box.bottom() - fade, box.width(), fade), QBrush(grad))

    kind = ("保留上部 %d%%（腰部以上）" % round((1.0 - ratio) * 100)) if crop \
        else "未裁切（膝上全身）"
    annot(p, box.x() + 4, box.y() + 16,
          "玩偶 %dx%d ／ 素材 %dx%d" % (image.width(), image.height(),
                                       source.width(), source.height()))
    annot(p, box.x() + 4, box.y() + 28,
          "%s%s ／ 放大 %.2fx" % (kind, "／安全边 %dpx" % margin if margin else "",
                                 image.width() / float(source.width())))
    annot(p, box.x() + 4, box.y() + 40,
          "占面板宽 %.0f%% ／ 占上区高 %.0f%%"
          % (100.0 * image.width() / box.width(),
             100.0 * image.height() / box.height()))
    annot(p, box.x() + 4, box.bottom() - 6, "底部渐隐收边 %dpx" % fade)


def sys_bar(p: QPainter, prof: typing.Dict) -> None:
    """下栏·系统信息：网络信号 / 交互流畅度 / 模式 / 隐私 / 设备。"""
    w, h, bar = prof["w"], prof["h"], prof["bar"]
    y0 = h - bar
    p.fillRect(QRect(0, y0, w, bar), QColor(C["panel_bg"]))
    p.setPen(QPen(QColor(C["panel_border"]), 1))
    p.drawLine(0, y0, w, y0)
    items = [("lan", "online", "success"), ("信号", "-52dBm", "success"),
             ("延时", "180ms", "accent"), ("FPS", "28.4", "accent"),
             ("mode", "CORE_LOCAL", "accent"), ("privacy", "OFF", "text_secondary"),
             ("audio", "ready", "success"), ("npu", "ready", "success"),
             ("pl", "ready", "success")]
    x, cy = 12, y0 + bar // 2
    for name, state, color_key in items:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C[color_key]))
        p.drawEllipse(x, cy - 4, 8, 8)
        p.setPen(QColor(C["text_primary"]))
        p.setFont(font(prof["f_small"]))
        text = "%s:%s" % (name, state)
        p.drawText(x + 12, cy + 5, text)
        x += 12 + p.fontMetrics().horizontalAdvance(text) + 14


# --------------------------------------------------------------------------- #
# 三张产物
# --------------------------------------------------------------------------- #
def render_board(prof: typing.Dict, matted: QImage, out_dir: Path) -> Path:
    w, h, bar, left = prof["w"], prof["h"], prof["bar"], prof["left"]
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(QColor(C["bg"]))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    info_panel(p, prof, 0, 0, left, h - bar)
    avatar_panel(p, prof, left, 0, w - left, h - bar, matted, crop=True,
                 title="右上·玩偶动画（腰部以上）")
    p.setPen(QPen(QColor(C["panel_border"]), 2))
    p.drawLine(left, 0, left, h - bar)
    sys_bar(p, prof)
    p.end()
    path = out_dir / (prof["name"] + ".png")
    img.save(str(path), "PNG")
    return path


def render_variants(prof: typing.Dict, matted: QImage, out_dir: Path) -> Path:
    """玩偶区变体对比：① 满铺 ② +安全边 ③ p=0.54（脸更大） ④ 不裁切。"""
    pw, ph, gap = prof["w"] - prof["left"], prof["h"] - prof["bar"], 16
    cases = [("1) 裁切 p=0.58 满铺", True, 0, 0.42),
             ("2) 裁切 p=0.58 + %dpx 安全边" % SAFE_MARGIN, True, SAFE_MARGIN, 0.42),
             ("3) 裁切 p=0.54（脸更大）", True, 0, 0.46),
             ("4) 不裁切（现状：膝上全身）", False, 0, 0.42)]
    img = QImage(pw * len(cases) + gap * (len(cases) + 1), ph + 48,
                 QImage.Format_ARGB32)
    img.fill(QColor(C["bg"]))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    for i, (label, crop, margin, ratio) in enumerate(cases):
        x = gap + i * (pw + gap)
        p.setPen(QColor(C["text_primary"]))
        p.setFont(font(12, True))
        p.drawText(x, 26, label)
        avatar_panel(p, prof, x, 48, pw, ph, matted,
                     crop=crop, margin=margin, ratio=ratio)
    p.end()
    path = out_dir / "variants.png"
    img.save(str(path), "PNG")
    return path


def parse_args():
    ap = argparse.ArgumentParser(description="UI 设计草案渲染（板端 1024×600 三区）")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT),
                    help="产物目录（默认 docs/ui_draft）")
    ap.add_argument("--key-frame", default=str(DEFAULT_KEY), help="真实素材首帧（绿幕原图）")
    ap.add_argument("--matting-project", default=str(DEFAULT_MATTING_PROJECT),
                    help="桌宠工程目录（其 src.matting 提供抠像）")
    ap.add_argument("--cache-dir", default=None, help="抠像缓存目录（默认 %%TEMP%%/ui_mock）")
    ap.add_argument("--no-matte", action="store_true", help="复用已缓存抠像帧，不重新抠像")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = Path(args.cache_dir) if args.cache_dir else Path(tempfile.gettempdir()) / "ui_mock"
    cache.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)                       # noqa: F841 字体渲染需要
    if os.path.isfile(CJK_FONT_FILE):
        QFontDatabase.addApplicationFont(CJK_FONT_FILE)   # 否则中文渲染为方框
    else:
        print("[警告] 未找到中文字体 %s，中文可能显示为方框" % CJK_FONT_FILE)

    key = Path(args.key_frame)
    if not key.is_file():
        raise SystemExit("首帧不存在: %s" % key)
    if args.no_matte:
        matted = QImage(str(cache / "matted_full.png"))
    else:
        matted = matte_once(key, Path(args.matting_project), cache)
    if matted.isNull():
        raise SystemExit("抠像帧读取失败（缓存目录: %s）" % cache)

    print("[素材] 抠像帧 %dx%d；裁切保留上部 %d%%（腰部以上）"
          % (matted.width(), matted.height(), round((1.0 - CROP_BOTTOM) * 100)))
    paths = [render_board(PROFILES["board"], matted, out_dir),
             render_variants(PROFILES["board"], matted, out_dir)]
    for path in paths:
        print("[写出] %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())


