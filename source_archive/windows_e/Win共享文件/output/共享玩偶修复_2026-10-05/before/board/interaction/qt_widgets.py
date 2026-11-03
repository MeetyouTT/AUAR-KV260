# -*- coding: utf-8 -*-
"""PySide6 面板：CameraPanel（左 55%）、StatusBar（底部）、AvatarPanel（右 45%）。

渲染后端（无板阶段）；板端 LVGL 版复用逻辑层（avatar_fsm / ui_state），
仅替换 paint 实现，布局/配色按 ui/ 合同。
"""
import math
import time
import typing
from dataclasses import dataclass

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QTimer, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QImage, QLinearGradient,
                           QPainter, QPainterPath, QPen, QPolygon)
from PySide6.QtWidgets import QWidget

from . import avatar_assets
from . import avatar_timing
from .avatar_fsm import animation_frames, avatar_spec, expression_spec
from .qt_style import get_style
from .ui_state import UiState


def _qcolor(hex_str: str) -> QColor:
    return QColor(hex_str)


def _pen(color, width: int, cap=Qt.RoundCap, join=Qt.RoundJoin) -> QPen:
    """构造带圆头/圆角的笔（QPen 构造不支持 cap/join 参数）。"""
    pen = QPen(color, width)
    pen.setCapStyle(cap)
    pen.setJoinStyle(join)
    return pen


@dataclass
class _SpriteSequence:
    """玩偶帧序列（已缩放到目标显示尺寸）+ 帧率。"""

    frames: typing.List[QImage]
    fps: float
    burst: bool = False           # 一次性动作（AWAKE / ACK_NOD）：播到末帧即停
    # ---- SOP 运行时数据（`tools/build_motion_table.py` / `split_avatar_segments.py` 预计算）----
    diffs: typing.Optional[typing.List[float]] = None   # 逐帧运动量 → 匀速化
    segments: typing.Any = None                          # enter/loop/exit 三段 → 三段式
    slowdown: float = 1.5                                # 整体放慢倍率

    def duration(self) -> float:
        """整段素材时长（秒）；fps 非法时按 24fps 估算。"""
        fps = self.fps if self.fps > 0 else 24.0
        return (len(self.frames) / fps) if self.frames else 0.0

    def frame_at(self, t: float) -> typing.Optional[QImage]:
        """按时间取当前帧：loop 素材取模无限循环，burst 素材夹在末帧（停住）。

        取帧口径**单一来源** = `avatar_timing.frame_index()`：播放层与验收脚本
        （tools/demo_scenario / tools/verify_v2_timing）必须逐字同口径，否则会出现
        "验收测的不是播放层"（见 .cline-handover.md 第 28 条）。
        """
        if not self.frames:
            return None
        return self.frames[avatar_timing.frame_index(
            t, len(self.frames), self.fps, self.burst)]

    def finished(self, t: float) -> bool:
        """burst 是否已播完（loop 素材恒 False；何时回迁由状态机决定）。"""
        if not self.burst:
            return False
        return float(t) >= self.duration()


class CameraPanel(QWidget):
    """上左「交互信息」区（585×556）：摄像头画面 + 信息行 + ASR/回复全文 + 延迟 + 事件流。

    对话全文由原右侧 45% 面板**移入本区**（三区布局 v1.1）：右下栏只留给玩偶动画。
    """

    def __init__(self, ui_state: UiState, parent: typing.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.ui = ui_state
        self.style = get_style()
        self.setMinimumSize(585, 556)

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt 命名
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        st = self.style
        snap = self.ui.snapshot()
        rect = self.rect()
        pad = st.layout["left_panel"]["padding"]
        li = st.layout["left_inner"]

        p.fillRect(rect, _qcolor(st.color("panel_bg")))

        # 纵向逐段排布（全部数值来自合同 left_inner；顺序固定，便于 LVGL 对齐）
        x = rect.x() + pad
        w = rect.width() - 2 * pad
        y = rect.y() + pad + li["top_offset"]

        # 1) 摄像头画面
        view = QRect(x, y, w, li["video"]["height"])
        p.fillRect(view, _qcolor(st.color("bg")))
        if snap.get("privacy"):
            self._paint_privacy(p, view, st)
        else:
            self._paint_camera_sim(p, view, st)
            self._paint_overlay(p, view, st, snap)
        y = view.y() + view.height()

        # 2) 信息行（场景/设备摘要）
        y += li["info_line"]["height"]
        self._paint_info_line(p, x, y, st, snap)

        # 3) 分隔线 + ASR 原文 + 回复全文 + 端到端延迟（对话区，v1.1 从右侧移入）
        y = self._paint_separator(p, x, y, w, st, li)
        y = self._paint_dialogue_area(p, x, y, st, snap, li)
        y = self._paint_separator(p, x, y, w, st, li)

        # 4) 最近事件流
        self._paint_events(p, x, y, st, self.ui.recent_text(li["events"]["lines"]),
                           li["events"]["line_h"])
        p.end()

    # ------------------------------------------------------------------ #
    def _paint_separator(self, p: QPainter, x: int, y: int, w: int, st, li) -> int:
        """画一条分隔线，返回分隔线**下方**的内容基线 y（间距取合同 separator_gap）。"""
        gap = li["separator_gap"]
        y += gap
        p.setPen(_qcolor(st.color("panel_border")))
        p.drawLine(x, y, x + w, y)
        return y + gap

    # ------------------------------------------------------------------ #
    def _paint_camera_sim(self, p: QPainter, view: QRect, st) -> None:
        """无板阶段：模拟摄像头画面（暗色 + 网格 + 提示）。"""
        pen = QPen(_qcolor(st.color("panel_border")), 1)
        p.setPen(pen)
        step = 48
        x = view.x()
        while x < view.x() + view.width():
            p.drawLine(x, view.y(), x, view.y() + view.height())
            x += step
        y = view.y()
        while y < view.y() + view.height():
            p.drawLine(view.x(), y, view.x() + view.width(), y)
            y += step
        p.setPen(_qcolor(st.color("text_secondary")))
        p.setFont(QFont("Microsoft YaHei", st.font_size("small")))
        p.drawText(view, Qt.AlignCenter, "CAMERA PREVIEW\n（无板模拟 · SIMULATED）")

    def _paint_privacy(self, p: QPainter, view: QRect, st) -> None:
        p.fillRect(view, _qcolor(st.color("privacy_mask")))
        p.setPen(_qcolor(st.color("text_primary")))
        p.setFont(QFont("Microsoft YaHei", st.font_size("label")))
        p.drawText(view, Qt.AlignCenter, "隐私模式\n摄像头画面已遮罩 · 停止新视觉事件")


    def _paint_overlay(self, p: QPainter, view: QRect, st, snap: typing.Dict) -> None:
        """检测框 + presence zone（FPGA overlay BOX/ZONE 合同语义）。"""
        scene = snap.get("scene", {})
        # presence zone：画面中心 80% 区域（FPGA overlay ZONE 寄存器语义）
        zx = view.x() + int(view.width() * 0.1)
        zy = view.y() + int(view.height() * 0.1)
        zw = int(view.width() * 0.8)
        zh = int(view.height() * 0.8)
        p.setPen(QPen(_qcolor(st.color("zone")), st.line_width("zone"), Qt.DashLine))
        p.drawRect(zx, zy, zw, zh)

        target = scene.get("current_target")
        if target and target.get("box"):
            b = target["box"]  # 归一化 [x0,y0,x1,y1]
            rx = view.x() + int(b[0] * view.width())
            ry = view.y() + int(b[1] * view.height())
            rw = int((b[2] - b[0]) * view.width())
            rh = int((b[3] - b[1]) * view.height())
            p.setPen(QPen(_qcolor(st.color("box")), st.line_width("box")))
            p.drawRect(rx, ry, rw, rh)
            p.setFont(QFont("Microsoft YaHei", st.font_size("small")))
            label = "track#%s %.2f" % (target.get("track_id", "?"),
                                       target.get("confidence", 0.0))
            fm = p.fontMetrics()
            lx = rx
            ly = max(view.y(), ry - fm.height() - 4)
            # label 加半透明底色，避免与 zone 边框重叠难读
            p.fillRect(lx, ly, fm.horizontalAdvance(label) + 6, fm.height() + 2,
                       _qcolor(st.color("bg")))
            p.drawText(lx + 3, ly + fm.ascent() + 2, label)

    def _paint_info_line(self, p: QPainter, x: int, y: int, st, snap: typing.Dict) -> None:
        """信息行：人/序号/帧率/摄像头/NPU（y 为文字基线）。"""
        scene = snap.get("scene", {})
        p.setPen(_qcolor(st.color("text_secondary")))
        p.setFont(QFont("Microsoft YaHei", st.font_size("small")))
        text = "people=%d  seq=%d  fps=%.1f  camera=%s  npu=%s" % (
            scene.get("people_count", 0),
            scene.get("scene_seq", 0),
            snap.get("fps", 0.0),
            (snap.get("camera") or {}).get("state", "?"),
            (snap.get("npu") or {}).get("state", "?"),
        )
        p.drawText(x, y, text)

    def _paint_dialogue_area(self, p: QPainter, x: int, y: int, st,
                             snap: typing.Dict, li) -> int:
        """ASR 原文 + 回复全文 + 端到端延迟；返回下一段基线 y。

        行数/行高来自合同 left_inner.dialogue（asr_h / reply_lines / line_h），
        回复文本超出按 TextWordWrap 在区域内换行（最多 reply_lines 行）。
        """
        cfg = li["dialogue"]
        dialogue = snap.get("dialogue", {})
        reply = str(dialogue.get("last_reply", "") or "")
        thinking = bool(dialogue.get("thinking", False))

        y += cfg["asr_h"]
        p.setPen(_qcolor(st.color("accent")))
        p.setFont(QFont("Microsoft YaHei", st.font_size("small")))
        p.drawText(x, y, "ASR  麦克风输入（KWS/VAD 命中后转写）")

        reply_h = cfg["reply_lines"] * cfg["line_h"]
        reply_rect = QRect(x, y + 6, self.rect().width() - 2 * st.layout["left_panel"]["padding"],
                           reply_h)
        p.setFont(QFont("Microsoft YaHei", st.font_size("dialogue")))
        if thinking:
            p.setPen(_qcolor(st.color("accent")))
            p.drawText(reply_rect, Qt.AlignLeft | Qt.AlignTop, "……思考中")
        elif reply:
            p.setPen(_qcolor(st.color("text_primary")))
            p.drawText(reply_rect, Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, reply)
        else:
            p.setPen(_qcolor(st.color("text_secondary")))
            p.drawText(reply_rect, Qt.AlignLeft | Qt.AlignTop, "（等待对话）")
        y += reply_h

        y += li["latency_line"]["height"]
        p.setPen(_qcolor(st.color("text_secondary")))
        p.setFont(QFont("Microsoft YaHei", st.font_size("small")))
        p.drawText(x, y, "端到端延迟 %.0f ms  |  状态 %s  |  模式 %s"
                   % (snap.get("latency_ms", 180.0), snap.get("runtime_state", "?"),
                      snap.get("mode", "CORE_LOCAL")))
        return y

    def _paint_events(self, p: QPainter, x: int, y: int, st,
                      texts: typing.List[str], line_h: int) -> None:
        """最近事件流（最多 lines 行，行高来自合同）。"""
        p.setFont(QFont("Microsoft YaHei", st.font_size("small")))
        if not texts:
            p.setPen(_qcolor(st.color("text_secondary")))
            p.drawText(x, y + line_h, "（无事件）")
            return
        p.setPen(_qcolor(st.color("accent")))
        for i, t in enumerate(texts):
            p.drawText(x, y + (i + 1) * line_h, t)


class StatusBar(QWidget):
    """下栏「系统信息」条（1024×44）：合同 status_items 逐项 = 圆点 + 名称:状态。

    含 fps（帧率）与 mode（本地/局域网）——原顶栏删除后，模式改在此呈现。
    """

    def __init__(self, ui_state: UiState, parent: typing.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.ui = ui_state
        self.style = get_style()
        self.setMinimumHeight(int(self.style.layout["bottom_bar"]["height"]))

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        st = self.style
        snap = self.ui.snapshot()
        p.fillRect(self.rect(), _qcolor(st.color("panel_bg")))
        p.setPen(_qcolor(st.color("panel_border")))
        p.drawLine(self.rect().x(), self.rect().y(),
                   self.rect().x() + self.rect().width(), self.rect().y())

        items = st.status_items()
        gap = st.tokens["spacing"]["status_gap"]
        x = self.rect().x() + 12
        y_center = self.rect().y() + self.rect().height() // 2
        for name in items:
            state, color_key = self._status(name, snap)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(_qcolor(st.color(color_key))))
            p.drawEllipse(x, y_center - 5, 10, 10)
            p.setPen(_qcolor(st.color("text_primary")))
            p.setFont(QFont("Microsoft YaHei", st.font_size("small")))
            label = "%s:%s" % (name, state)
            p.drawText(x + 14, y_center + 5, label)
            fm = p.fontMetrics()
            x += 14 + fm.horizontalAdvance(label) + gap
        p.end()

    @staticmethod
    def _status(name: str, snap: typing.Dict) -> typing.Tuple[str, str]:
        if name == "mode":
            return snap.get("mode", "CORE_LOCAL"), "accent"
        if name == "fps":
            return "%.1f" % float(snap.get("fps", 0.0) or 0.0), "accent"
        if name == "privacy":
            return ("ON" if snap.get("privacy") else "OFF"), \
                   ("warning" if snap.get("privacy") else "text_secondary")
        if name == "save":
            return "off", "text_secondary"
        if name == "lan":
            # status_items 用 "lan"，UiState 设备 key 为 "network"
            dev = (snap.get("network") or {})
            state = dev.get("state", "offline")
            if state == "online":
                return "online", "success"
            if state == "offline":
                return "offline", "warning"
            return state, "warning"
        dev = (snap.get(name) or {})
        state = dev.get("state", "?")
        if state in ("ready", "online", "ok"):
            return state, "success"
        if state in ("lost", "error"):
            return state, "error"
        if state in ("busy",):
            return state, "warning"
        return state, "text_secondary"


class AvatarPanel(QWidget):
    """上右「玩偶动画」区（439×556）：状态标签 24 + 玩偶框 423×516 + 底部渐隐收边 28。

    对话全文已移入上左交互信息区（三区布局 v1.1），本区只负责玩偶。
    """

    def __init__(self, ui_state: UiState, parent: typing.Optional[QWidget] = None,
                 sprite_root: typing.Optional[typing.Any] = None) -> None:
        super().__init__(parent)
        self.ui = ui_state
        self.style = get_style()
        self.setMinimumSize(439, 556)
        # 动画接口（方案 C）：由 MainWindow._refresh 统一驱动重绘；动画引擎见 _anim_state
        # 方案 B2V：主体为 QPainterPath 矢量绘制（_draw_sprite_base），无位图依赖
        # 帧序列素材（avatar_assets）：assets/avatar/<素材名>/ 有素材即自动优先播放；
        # sprite_root 仅供测试注入素材根目录，生产默认 None（取 avatar_assets.AVATAR_DIR）。
        self._sprite_root = sprite_root
        self._sprite_cache: typing.Dict[typing.Tuple, typing.Optional["_SpriteSequence"]] = {}
        # 状态内时间基：状态一变就归零（burst 一次性动作素材必须从第 0 帧起播）
        self._state_key: typing.Optional[str] = None
        self._state_t0: float = 0.0
        # 入场相位（P0-2）：进入 **loop** 状态时抽一次随机起始相位，打破"每次入场
        # 都是同一动作"；burst 恒 0（见 avatar_timing.frame_time）。
        self._phase_key: typing.Optional[typing.Tuple] = None
        self._phase: float = 0.0
        # 玩偶框上方「扩展位」（D2）：**默认留空**，内容待定；接入用 set_overlay_slot_painter()
        self.overlay_slot_painter: typing.Optional[typing.Callable] = None

    # ------------------------------------------------------------------ #
    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        st = self.style
        snap = self.ui.snapshot()
        rect = self.rect()
        pad = st.layout["right_panel"]["padding"]
        ri = st.layout["right_inner"]
        p.fillRect(rect, _qcolor(st.color("panel_bg")))
        # 左边界线（与左上「交互信息」区之间的分隔）
        p.setPen(_qcolor(st.color("panel_border")))
        p.drawLine(rect.x(), rect.y(), rect.x(), rect.y() + rect.height())

        # 玩偶区 = 面板内区（去 padding）：状态标签 24 + 玩偶框 423×516
        inner = QRect(rect.x() + pad, rect.y() + pad,
                      rect.width() - 2 * pad, rect.height() - 2 * pad)
        self._render_avatar(p, inner, st, snap)

        # 扩展位（D2：玩偶框上方空档）—— 默认留空，接入内容时由 overlay_slot_painter 填充
        slot = self.overlay_slot_rect()
        if not slot.isNull():
            self._paint_overlay_slot(p, slot, st, snap)

        # 底部渐隐收边：把"腰部"裁切线化掉（透明 → 面板底色）
        label_h = int(ri["label_h"])
        fade = int(ri["fade_h"])
        box = QRect(inner.x(), inner.y() + label_h,
                    inner.width(), inner.height() - label_h)
        grad = QLinearGradient(0.0, float(box.bottom() - fade),
                               0.0, float(box.bottom()))
        c0 = _qcolor(st.color("panel_bg"))
        c0.setAlpha(0)
        c1 = _qcolor(st.color("panel_bg"))
        c1.setAlpha(255)
        grad.setColorAt(0.0, c0)
        grad.setColorAt(1.0, c1)
        p.fillRect(QRect(box.x(), box.bottom() - fade, box.width(), fade),
                   QBrush(grad))
        p.end()

    # ------------------------------------------------------------------ #
    # 玩偶框上方「扩展位」（D2）：先留空，接口先留好
    # ------------------------------------------------------------------ #
    def overlay_slot_rect(self) -> QRect:
        """返回玩偶框上方扩展位矩形（面板内坐标）；未启用/高度为 0 → 空 QRect。

        位置 = 玩偶框**顶部**保留 `right_inner.overlay_slot.reserved_height` 高的一段。
        素材按「腰部以上」入库且**底部对齐**（423×436 < 框高 516），故该段天然留白；
        数值全部来自合同 → 板端 LVGL 按同一算式实现即可逐像素对齐。
        """
        st = self.style
        pad = st.layout["right_panel"]["padding"]
        ri = st.layout["right_inner"]
        slot = ri.get("overlay_slot") or {}
        if not slot.get("enabled"):
            return QRect()
        height = int(slot.get("reserved_height", 0))
        if height <= 0:
            return QRect()
        inner = self.rect().adjusted(pad, pad, -pad, -pad)
        label_h = int(ri["label_h"])
        box = QRect(inner.x(), inner.y() + label_h, inner.width(),
                    inner.height() - label_h)
        return QRect(box.x(), box.y(), box.width(), min(height, box.height()))

    def set_overlay_slot_painter(self,
                                 painter: typing.Optional[typing.Callable]) -> None:
        """接入扩展位内容（后续：状态徽标 / 节日装饰 / 字幕）。

        签名 `painter(p: QPainter, rect: QRect, st: UiStyle, snap: dict)`；
        传 `None` 恢复「留空」。**默认不绘制任何内容**（D2：具体内容待定）。
        """
        self.overlay_slot_painter = painter

    def _paint_overlay_slot(self, p: QPainter, rect: QRect, st,
                            snap: typing.Dict) -> None:
        """扩展位绘制入口（默认空实现 = 留空）。"""
        painter = self.overlay_slot_painter
        if callable(painter):
            painter(p, rect, st, snap)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _face_anchor(rect: QRectF) -> QRectF:
        """返回由 B2V 头部几何直接确定的猫脸锚框。

        矢量主体使用以下归一化头脸区间：头部左右边约为
        0.35..0.65、脸部可放置眼/鼻/嘴的区域为 x=0.36..0.64，
        y=0.28..0.68。这里的数值与 _draw_sprite_base 的控制点同源，
        不再依据位图尺寸或 JPG 内容做百分比猜测。
        """
        return QRectF(
            rect.x() + rect.width() * 0.36,
            rect.y() + rect.height() * 0.28,
            rect.width() * 0.28,
            rect.height() * 0.40,
        )

    @staticmethod
    def _clamp(value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    @staticmethod
    def _number(value, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _cyclic_keyframe_value(cls, values, phase: float,
                               default: float) -> float:
        """对单个通道的关键帧做循环线性插值。"""
        if not values:
            return default
        if len(values) == 1:
            return cls._number(values[0], default)
        phase = phase % 1.0
        position = phase * len(values)
        index = int(position) % len(values)
        next_index = (index + 1) % len(values)
        fraction = position - int(position)
        current = cls._number(values[index], default)
        following = cls._number(values[next_index], current)
        return current + (following - current) * fraction

    def _draw_sprite_base(self, p: QPainter, rect: QRectF,
                          st, spec) -> None:
        """绘制 B2V 矢量主体：双耳、头脸、鼻子和下方字标。

        主体颜色固定匹配附件参考图；st/spec 参数保留在渲染接口中，
        表情层才使用 spec.token_key 的状态语义色。
        """
        del st, spec  # 主体按参考图配色，不随运行时告警色改变。

        # 从附件 JPG 的代表性蓝色/脸部像素校准；主体不使用 token 色。
        blue = QColor("#014296")
        face_fill = QColor("#F7F8F3")
        unit = min(rect.width(), rect.height())
        outline_width = max(3, int(round(unit * 0.026)))

        def pt(x: float, y: float) -> QPointF:
            return QPointF(
                rect.x() + rect.width() * x,
                rect.y() + rect.height() * y,
            )

        p.save()
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(_pen(blue, outline_width))
        p.setBrush(QBrush(face_fill))

        # 左耳：先绘制，头部轮廓随后覆盖耳根，形成参考图中的连贯外轮廓。
        left_ear = QPainterPath()
        left_ear.moveTo(pt(0.405, 0.315))
        left_ear.lineTo(pt(0.410, 0.080))
        left_ear.lineTo(pt(0.485, 0.185))
        left_ear.lineTo(pt(0.455, 0.285))
        left_ear.closeSubpath()
        p.drawPath(left_ear)

        # 右耳为镜像结构。
        right_ear = QPainterPath()
        right_ear.moveTo(pt(0.595, 0.315))
        right_ear.lineTo(pt(0.590, 0.080))
        right_ear.lineTo(pt(0.515, 0.185))
        right_ear.lineTo(pt(0.545, 0.285))
        right_ear.closeSubpath()
        p.drawPath(right_ear)

        # 猫头和脸颊：顶部圆弧、两侧收颊、底部圆弧均为 cubic path。
        head = QPainterPath()
        head.moveTo(pt(0.405, 0.300))
        head.cubicTo(
            pt(0.425, 0.255), pt(0.465, 0.235), pt(0.500, 0.235)
        )
        head.cubicTo(
            pt(0.535, 0.235), pt(0.575, 0.255), pt(0.595, 0.300)
        )
        head.cubicTo(
            pt(0.615, 0.385), pt(0.635, 0.500), pt(0.645, 0.575)
        )
        head.cubicTo(
            pt(0.652, 0.640), pt(0.585, 0.715), pt(0.500, 0.735)
        )
        head.cubicTo(
            pt(0.415, 0.715), pt(0.348, 0.640), pt(0.355, 0.575)
        )
        head.cubicTo(
            pt(0.365, 0.500), pt(0.385, 0.385), pt(0.405, 0.300)
        )
        head.closeSubpath()
        p.drawPath(head)

        # 鼻子是主体固定几何；动态嘴巴由 _draw_mouth 绘制。
        nose = QPainterPath()
        nose.moveTo(pt(0.480, 0.505))
        nose.cubicTo(
            pt(0.490, 0.495), pt(0.510, 0.495), pt(0.520, 0.505)
        )
        nose.cubicTo(
            pt(0.515, 0.530), pt(0.500, 0.540), pt(0.500, 0.540)
        )
        nose.cubicTo(
            pt(0.500, 0.540), pt(0.485, 0.530), pt(0.480, 0.505)
        )
        nose.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(blue))
        p.drawPath(nose)

        # 参考图中的 CATLY 字标和副标题也用 QPainter 绘制，保持纯代码资源。
        p.setPen(blue)
        logo_font = QFont("Arial", max(1, int(round(rect.height() * 0.145))),
                          QFont.Bold)
        p.setFont(logo_font)
        p.drawText(
            QRectF(
                rect.x() + rect.width() * 0.32,
                rect.y() + rect.height() * 0.715,
                rect.width() * 0.36,
                rect.height() * 0.17,
            ),
            Qt.AlignCenter,
            "CATLY",
        )

        subtitle_font = QFont(
            "Arial", max(1, int(round(rect.height() * 0.050)))
        )
        p.setFont(subtitle_font)
        p.drawText(
            QRectF(
                rect.x() + rect.width() * 0.29,
                rect.y() + rect.height() * 0.865,
                rect.width() * 0.42,
                rect.height() * 0.070,
            ),
            Qt.AlignCenter,
            "SIMPLE DESIGN CO.",
        )
        p.restore()

    def _render_avatar(self, p: QPainter, rect: QRect, st,
                       snap: typing.Dict) -> None:
        """绘制 B2V：矢量主体 + 程序化表情 + 状态标签。"""
        state = snap.get("runtime_state", "IDLE")
        spec = avatar_spec(state)
        expression = expression_spec(spec.expression)
        state_color = _qcolor(st.color(spec.token_key))

        # 保留原有状态标签内容，并用 token_key 保留 warning/error 语义色。
        # 标签高度取合同 right_inner.label_h（24）——标签下方即为合同玩偶框 423×516。
        label_h = int(st.layout["right_inner"]["label_h"])
        p.save()
        p.setPen(state_color)
        p.setFont(QFont("Microsoft YaHei", st.font_size("label"), QFont.Bold))
        p.drawText(
            QRect(rect.x(), rect.y(), rect.width(), label_h),
            Qt.AlignCenter,
            "%s [%s]" % (spec.label, state),
        )
        p.restore()

        # 只在标签下方绘制内容；body_rect 为玩偶主体绘制区（宽度=合同框宽，无额外内缩）
        body_rect = QRectF(rect).adjusted(0.0, float(label_h), 0.0, 0.0)

        # 1) 帧序列素材优先：assets/avatar/<素材名>/ 有素材即自动播放（放入即生效）；
        #    无素材时回退 2) B2V 矢量主体 + 程序化表情层。
        sequence = self._sprite_sequence(state, body_rect)
        if sequence is not None:
            # 状态内相对时间（非全局）：burst 素材/AWAKE/ACK_NOD 才会从第 0 帧开始播。
            # 顺序要紧：先 _state_time（它会刷新 _state_key），再取相位/速度 —— 否则
            # 新状态会沿用上一个状态的相位键（P0-2）。
            now = time.monotonic()
            state_time = self._state_time(state, now)
            self._draw_sprite_frame(
                p, body_rect, sequence,
                self._playback_time(sequence, state, state_time, snap),
                avatar_timing.idle_offsets(now))       # 潜动层：全局时间基，不随状态归零
            return

        self._draw_sprite_base(p, body_rect, st, spec)

        anim_state = self._anim_state(time.monotonic())
        face_rect = self._face_anchor(body_rect)
        face_center = face_rect.center()
        scale = self._clamp(
            self._number(anim_state.get("scale"), 1.0), 0.80, 1.25
        )

        p.save()
        p.translate(face_center)
        p.scale(scale, scale)
        p.translate(-face_center)
        self._draw_eyes(
            p,
            face_rect,
            expression,
            self._clamp(
                self._number(anim_state.get("blink_close"), 0.0),
                0.0,
                1.0,
            ),
            self._clamp(
                self._number(anim_state.get("look_dx"), 0.0),
                -1.0,
                1.0,
            ),
            state_color,
        )
        self._draw_mouth(
            p,
            face_rect,
            expression.get("mouth", "line"),
            self._clamp(
                self._number(anim_state.get("mouth"), 0.0),
                0.0,
                1.0,
            ),
            state_color,
        )
        p.restore()

    # ------------------------------------------------------------------ #
    # 帧序列素材（avatar_assets）：加载 + 缓存 + 绘制
    # ------------------------------------------------------------------ #
    def _state_time(self, runtime_state: str, now: float) -> float:
        """当前状态内的相对时间（秒）：**状态一变就归零**。

        为什么必须归零：burst 素材（AWAKE / ACK_NOD）只播一次，若拿全局
        time.monotonic() 当相位，刚进状态就已经远超素材时长，会永远停在末帧。

        注意（P0-2 修正）：归零对 loop 素材**并非无副作用** —— 它意味着"每次入场都
        从第 0 帧起播"，正是 G1「入场一致」的根因；现由 `_loop_phase()` 补随机相位，
        再经 `avatar_timing.frame_time()` 合成真正的取帧时间。
        """
        if runtime_state != self._state_key:
            self._state_key = runtime_state
            self._state_t0 = now
        return max(0.0, now - self._state_t0)

    def _loop_phase(self, sequence: "_SpriteSequence") -> float:
        """入场随机相位（P0-2）：进入 **loop** 状态时抽一次，状态内保持稳定。

        burst 恒 0（一次性动作必须从第 0 帧起播）；键控含素材时长，换素材即重抽。
        """
        if sequence.burst:
            return 0.0
        key = (self._state_key, round(sequence.duration(), 4))
        if key != self._phase_key:
            self._phase_key = key
            self._phase = avatar_timing.random_phase(sequence.duration())
        return self._phase

    @staticmethod
    def _reply_text(snap: typing.Dict) -> str:
        """当前回复全文（`ui_state.dialogue.last_reply`）；P0-2 变速用它估句长。"""
        dialogue = snap.get("dialogue") if isinstance(snap, dict) else None
        text = dialogue.get("last_reply") if isinstance(dialogue, dict) else None
        return text if isinstance(text, str) else ""

    def _playback_time(self, sequence: "_SpriteSequence", state: str,
                       state_time: float, snap: typing.Dict) -> float:
        """★ SOP 播放口径（与 `tools/demo_stage.py` **共用同一份 `avatar_timing`**）★

        burst → 原样起播；有 `segments` → 三段式（按回复句长定循环次数）；
        否则 → **匀速化 + 放慢**（循环点速度连续，看不出一次循环结束）；
        `diffs` 缺失时 `playback_time` 内部自动降级为普通循环（不会失效）。
        """
        fps = sequence.fps
        if sequence.burst:
            return avatar_timing.frame_time(state_time, burst=True)
        if sequence.segments is not None:
            loops = avatar_timing.loops_for_duration(
                avatar_timing.estimate_seconds(self._reply_text(snap)),
                sequence.segments, fps)
            return avatar_timing.segment_time(state_time, sequence.segments, fps,
                                              loops=loops,
                                              slowdown=sequence.slowdown,
                                              loop_phase=self._loop_phase(sequence))
        return avatar_timing.playback_time(state_time, state=state,
                                           diffs=sequence.diffs, fps=fps,
                                           duration=sequence.duration(), burst=False,
                                           slowdown=sequence.slowdown)

    def _sprite_sequence(self, runtime_state: str,
                         box: QRectF) -> typing.Optional["_SpriteSequence"]:
        """按当前状态解析素材帧序列（缩放到 box 尺寸后缓存）。

        返回 None 表示无素材，交由调用方回退 B2V 矢量主体。
        缓存按 (状态, 目标尺寸) 键控，最多保留 2 个状态，避免 9 态全量驻留内存。
        """
        key = (runtime_state, int(box.width()), int(box.height()))
        if key in self._sprite_cache:
            return self._sprite_cache[key]

        sequence: typing.Optional["_SpriteSequence"] = None
        directory = avatar_assets.frames_dir(runtime_state, root=self._sprite_root)
        if directory is not None:
            frames: typing.List[QImage] = []
            for path in avatar_assets.list_frames(directory):
                image = QImage(str(path))
                if image.isNull():
                    continue
                frames.append(image.scaled(
                    int(box.width()), int(box.height()),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation,
                ))
            if frames:
                sequence = _SpriteSequence(
                    frames, avatar_assets.frames_fps(directory),
                    burst=runtime_state in avatar_assets.BURST_STATES,
                    diffs=avatar_assets.read_motion(directory),
                    # ⚠ burst 状态（点头 / 摇头 / 惊讶）**必须整段播一次**，绝不用三段式 ——
                    # 即便素材目录里残留 segments.json 也要忽略（双保险，不靠调用顺序）。
                    segments=(None if runtime_state in avatar_assets.BURST_STATES
                              else (avatar_timing.segments_from_dict(
                                  avatar_assets.read_segments(directory) or {})
                                  or None)),
                    slowdown=(avatar_assets.read_slowdown(
                        directory, avatar_timing.LOOP_SLOWDOWN)
                        or avatar_timing.LOOP_SLOWDOWN),
                )

        self._sprite_cache[key] = sequence
        while len(self._sprite_cache) > 2:
            self._sprite_cache.pop(next(iter(self._sprite_cache)))
        return sequence

    @staticmethod
    def _draw_sprite_frame(p: QPainter, box: QRectF,
                           sequence: "_SpriteSequence", t: float,
                           off: typing.Any = None) -> None:
        """把当前帧**水平居中 / 底部对齐**绘制到 box（保持素材宽高比），并叠加潜动层变换。

        素材按 `--framing waist-up` 入库（只保留腰部以上），故**底部对齐**：
        腰部切线落在框底，再由 AvatarPanel 的 28px 渐隐收边化掉横切边。

        `off` = `avatar_timing.idle_offsets()`（呼吸 / 重心 / 微摆）；锚点 = **显示框底边中心**：
        呼吸是纵向缩放（胸腔起伏，不是整个人上浮）、重心是平移、微摆是旋转。
        """
        image = sequence.frame_at(t)
        if image is None or image.isNull():
            return
        x = box.x() + (box.width() - image.width()) / 2.0
        y = box.y() + box.height() - image.height()
        if off is None:
            p.drawImage(QPointF(x, y), image)
            return
        cx = x + image.width() / 2.0
        bottom = y + image.height()
        p.save()
        p.translate(cx + off.dx, bottom - off.dy)
        p.rotate(off.tilt_deg)
        p.scale(1.0, off.scale_y)
        p.translate(-cx, -bottom)
        p.drawImage(QPointF(x, y), image)
        p.restore()

    def _anim_state(self, t: float) -> typing.Dict:
        """方案 C 执行层：UiState + 帧表 → 当前动画值。"""
        anim = self.ui.snapshot().get("avatar_anim", {})
        if not anim.get("enabled"):
            return {
                "blink_close": 0.0,
                "look_dx": 0.0,
                "scale": 1.0,
                "mouth": 0.0,
            }

        state = self.ui.snapshot().get("runtime_state", "IDLE")
        fallback_animation = avatar_spec(state).animation
        animation_name = str(anim.get("name") or fallback_animation)
        frames = animation_frames(animation_name)
        params = anim.get("params") or {}
        if not isinstance(params, dict):
            params = {}

        animation_cfg = self.style.animation(animation_name)
        period_ms = self._number(
            params.get("period_ms", animation_cfg.get("period_ms", 1000)),
            1000.0,
        )
        period_s = max(period_ms, 1.0) / 1000.0
        phase = (self._number(t, 0.0) % period_s) / period_s

        channels = {"eye": [], "look_dx": [], "scale": [], "mouth": []}
        for channel, value in frames:
            if channel in channels:
                channels[channel].append(value)

        values = {
            "blink_close": self._cyclic_keyframe_value(
                channels["eye"], phase, 0.0
            ),
            "look_dx": self._cyclic_keyframe_value(
                channels["look_dx"], phase, 0.0
            ),
            "scale": self._cyclic_keyframe_value(
                channels["scale"], phase, 1.0
            ),
            "mouth": self._cyclic_keyframe_value(
                channels["mouth"], phase, 0.0
            ),
        }

        # intensity 不是逻辑层必填字段；缺省为 1，且对 scale 以 1 为中心缩放。
        intensity = self._clamp(
            self._number(params.get("intensity", 1.0), 1.0), 0.0, 1.0
        )
        values["blink_close"] *= intensity
        values["look_dx"] *= intensity
        values["mouth"] *= intensity
        values["scale"] = 1.0 + (values["scale"] - 1.0) * intensity
        return values

    def _draw_eyes(self, p: QPainter, face_rect: QRectF,
                   expression: typing.Dict, blink_close: float,
                   look_dx: float, color: QColor) -> None:
        """绘制两只眼睛；所有坐标来自 expression_spec 的归一化参数。"""
        face_width = face_rect.width()
        face_height = face_rect.height()
        eye_dx = self._number(expression.get("eye_dx"), 0.16)
        eye_dy = self._number(expression.get("eye_dy"), -0.05)
        eye_r = max(
            1.0,
            self._number(expression.get("eye_r"), 0.055)
            * min(face_width, face_height),
        )
        center_y = face_rect.center().y() + eye_dy * face_height
        center_x = face_rect.center().x()

        look = expression.get("look", "")
        look_bias_x = 0.0
        look_bias_y = 0.0
        if "left" in look:
            look_bias_x = -0.30
        elif "right" in look:
            look_bias_x = 0.30
        if "up" in look:
            look_bias_y = -0.24
        elif "down" in look:
            look_bias_y = 0.24

        # 视线偏移只占眼半径的一小部分，避免移出脸部锚框。
        gaze_x = eye_r * (look_dx * 0.65 + look_bias_x)
        gaze_y = eye_r * look_bias_y
        vertical = max(0.04, 1.0 - blink_close)
        stroke = max(2, int(round(eye_r * 0.22)))

        p.save()
        if blink_close >= 0.92:
            p.setPen(_pen(color, stroke))
            p.setBrush(Qt.NoBrush)
            for side in (-1.0, 1.0):
                x = center_x + side * eye_dx * face_width
                path = QPainterPath()
                path.moveTo(x - eye_r, center_y + gaze_y)
                path.cubicTo(
                    x - eye_r * 0.40, center_y + gaze_y + eye_r * 0.22,
                    x + eye_r * 0.40, center_y + gaze_y + eye_r * 0.22,
                    x + eye_r, center_y + gaze_y,
                )
                p.drawPath(path)
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(color))
            for side in (-1.0, 1.0):
                x = center_x + side * eye_dx * face_width + gaze_x
                y = center_y + gaze_y
                p.drawEllipse(QRectF(
                    x - eye_r,
                    y - eye_r * vertical,
                    eye_r * 2.0,
                    eye_r * 2.0 * vertical,
                ))
        p.restore()

    def _draw_mouth(self, p: QPainter, face_rect: QRectF,
                    mouth_kind: str, open_ratio: float,
                    color: QColor) -> None:
        """按 expression_spec 的 mouth 标识绘制 line/o/arc 表情。"""
        face_width = face_rect.width()
        face_height = face_rect.height()
        center = QPointF(
            face_rect.center().x(),
            face_rect.center().y() + face_height * 0.12,
        )
        open_ratio = self._clamp(open_ratio, 0.0, 1.0)
        stroke = max(2, int(round(face_width * 0.018)))
        half_width = face_width * 0.18
        amplitude = face_height * (0.025 + 0.055 * open_ratio)
        left_x = center.x() - half_width
        right_x = center.x() + half_width

        p.save()
        if mouth_kind == "o":
            # curious 的 O 嘴在静态时也保持可见，动画 mouth 通道控制纵向张合。
            width = face_width * (0.13 + 0.07 * open_ratio)
            height = face_height * (0.08 + 0.12 * max(open_ratio, 0.20))
            p.setPen(_pen(color, stroke))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QRectF(
                center.x() - width / 2.0,
                center.y() - height / 2.0,
                width,
                height,
            ))
        else:
            # arc_up = 微笑（中心下沉），arc_down = 皱眉（中心上拱）。
            if mouth_kind == "arc_down":
                center_offset = -amplitude
            else:
                center_offset = amplitude
            endpoint_y = center.y()
            path = QPainterPath()
            path.moveTo(left_x, endpoint_y)
            path.cubicTo(
                center.x() - half_width * 0.58,
                endpoint_y + center_offset,
                center.x() + half_width * 0.58,
                endpoint_y + center_offset,
                right_x,
                endpoint_y,
            )
            p.setPen(_pen(color, stroke))
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)

            if open_ratio > 0.08:
                # 张嘴时增加一个小型填充椭圆；线/弧仍保留其表达式差异。
                open_width = face_width * (0.16 + 0.10 * open_ratio)
                open_height = face_height * (0.06 + 0.10 * open_ratio)
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(color))
                p.drawEllipse(QRectF(
                    center.x() - open_width / 2.0,
                    center.y() - open_height / 2.0,
                    open_width,
                    open_height,
                ))
        p.restore()

