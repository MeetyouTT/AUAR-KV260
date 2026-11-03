# 🤖 GPT Prompt · 雾镜 Lite 玩偶方案 B2V（矢量底图 + 程序化表情层）

> 用途：将本文件 **§2–§5 连同附件 `cat_avatar_base.JPG`** 一起发给 GPT（ChatGPT），
> 由 GPT 完成方案 B2V（矢量底图）返工：用 `QPainterPath` 矢量严格描摹猫头主体以
> 替换当前位图底图，保留程序化表情层。GPT 返回后，把成品代码与文档交回 Cline
> （人3 开发会话）接入工程并测试提交。
>
> 工程：`wujing-lite`（2026 全国大学生嵌入式芯片与系统设计竞赛·FPGA 创新设计赛道，
> 复旦微 FMQL30TAI）｜ 无板开发月 A2 阶段（PC / SIMULATED，板端 LVGL 于 10 月迁移）
> 生成日期：2026-08-31 ｜ 维护：人3（Runtime & Integration）

---

## §0 使用说明（发给 GPT 前先读）

- **发送方式**：把 **§2–§5** 复制为文字 + **把 `board/ui/image/cat_avatar_base.JPG` 作为图片附件**
  一并发给 GPT。GPT 以该图为**严格描摹参考**，将其主体造型重绘为 QPainterPath 矢量。
- 当前基线：`python -m pytest tests/ -q` → **84 passed**（A1 60 + A2 15 + 方案C 接口 2 +
  方案B2 执行层 7）。
- 当前实现为 **B2 位图底图**（`QImage(cat_avatar_base.JPG)` + 表情层，见 §3.1）；本任务将其
  返工为 **B2V 矢量底图**：删除位图加载，改为 `_draw_sprite_base` 矢量绘制。
- 本任务**不修改** `avatar_fsm.py`、`ui_state.py`、`ui_spec/*.json` 的公开接口与合同版本。

---

## §1 角色与任务

> **角色**：你是一名精通 PySide6 与 LVGL 嵌入式图形开发的专家。
> **任务目标**：依据附件 `cat_avatar_base.JPG`，把当前"位图底图 + 程序化表情层"的玩偶渲染
> 返工为"**矢量底图 + 程序化表情层**"（方案 B2V）：用 `QPainterPath`/`QPainter` 几何路径
> 严格描摹猫头主体（头形、双耳、脸颊、花纹、胡须等），以代码替代位图；表情层（眼/嘴）与
> 方案 C 三层接口全部保留。并输出 LVGL 迁移指南与技术总结文档。

## §2 方案 B2V 核心需求

1. **矢量底图**：以附件 `cat_avatar_base.JPG` 为**造型参考**，用 `QPainterPath` 等矢量 API
   在 `avatar_rect`（568×397 px 区域）内**严格描摹猫头主体**：头形轮廓、双耳、脸颊、花纹、
   胡须等全部元素均由矢量代码绘制（`_draw_sprite_base`），**不得再加载任何位图**。
2. **猫脸锚框（关键改进）**：矢量路径是你自己写的，因此你**最清楚猫脸位置**——必须同时输出
   `_face_anchor(rect) -> QRectF`（归一化猫脸锚框），供表情层定位眼睛/嘴巴，**取代上一版
   `_sprite_face_rect` 的百分比猜测**，确保表情与矢量主体对齐。
3. **程序化表情层（保留）**：眼睛（眨眼 `blink_close` / 视线 `look_dx`）、嘴巴（张合 `mouth` /
   弧度）、缩放 `scale` 继续由 `_anim_state(t)` 动画值驱动，使用现有 `_draw_eyes`/`_draw_mouth`，
   叠加在矢量底图之上。
4. **配色语义**：矢量主体按附件 JPG 原图配色描摹；**表情层（眼/嘴）继续使用
   `AvatarSpec.token_key` 对应色**（正常=accent 蓝 `#4FC3F7`、降级=warning 黄 `#FFB300`、
   错误=error 红 `#E53935`），保证状态语义一致。
5. **性能与迁移**：纯矢量、无位图依赖，低开销、任意缩放无损；板端 LVGL 迁移用
   `lv_canvas` 矢量绘制或预渲染 sprite 数组（见 §5.2）。

---

## §3 上下文代码（真实工程摘录）

### §3.1 渲染接入点与执行层 —— `board/ui/qt_widgets.py`（AvatarPanel 当前 B2 实现）

**导入区（1–17 行）**：
```python
# -*- coding: utf-8 -*-
"""PySide6 面板：CameraPanel（左 55%）、StatusBar（底部）、AvatarPanel（右 45%）。
渲染后端（无板阶段）；板端 LVGL 版复用逻辑层（avatar_fsm / ui_state），
仅替换 paint 实现，布局/配色按 ui_spec/ 合同。"""
import math
import os
import time
import typing

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QTimer, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPolygon
from PySide6.QtWidgets import QWidget

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
```

**`AvatarPanel.__init__` 与 `paintEvent`（当前含 B2 位图加载，待 B2V 移除）**：
```python
class AvatarPanel(QWidget):
    """右侧玩偶区（45%）：状态动画 + 状态标签 + 对话文字。"""

    def __init__(self, ui_state: UiState, parent: typing.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.ui = ui_state
        self.style = get_style()
        self.setMinimumSize(576, 640)
        # 动画接口（方案 C）：由 MainWindow._refresh 统一驱动重绘；动画引擎见 _anim_state
        # 方案 B2·底图：一次性加载 cat_avatar_base.JPG（路径由 __file__ 回到工程根，与 cwd 无关）
        self._avatar_base_path = os.path.normpath(
            os.path.join(
                os.path.dirname(__file__),
                "..", "..", "board", "ui", "image", "cat_avatar_base.JPG",
            )
        )
        self._avatar_base = QImage(self._avatar_base_path)
        if self._avatar_base.isNull():
            # 缺图时仍允许 UI 启动，表情层和状态标签继续工作。
            self._avatar_base = QImage()

    # ------------------------------------------------------------------ #
    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        st = self.style
        snap = self.ui.snapshot()
        p.fillRect(self.rect(), _qcolor(st.color("panel_bg")))
        # 左边界线
        p.setPen(_qcolor(st.color("panel_border")))
        p.drawLine(self.rect().x(), self.rect().y(),
                   self.rect().x(), self.rect().y() + self.rect().height())

        ratio = st.layout["right_inner"]["avatar_ratio"]
        avatar_rect = QRect(self.rect().x() + 4, self.rect().y() + 8,
                            self.rect().width() - 8,
                            int(self.rect().height() * ratio))
        dialogue_rect = QRect(self.rect().x() + 12,
                              avatar_rect.y() + avatar_rect.height() + 6,
                              self.rect().width() - 24,
                              self.rect().height() - avatar_rect.height() - 24)

        self._render_avatar(p, avatar_rect, st, snap)
        self._paint_dialogue(p, dialogue_rect, st, snap)
        p.end()
```

**辅助方法 + `_render_avatar`（当前 B2 版；B2V 将删除位图相关、新增 `_draw_sprite_base`/`_face_anchor`）**：
```python
    # ------------------------------------------------------------------ #
    @staticmethod
    def _fit_image_rect(source_width: float, source_height: float,
                        target: QRectF) -> QRectF:
        """将底图等比 contain 到 target，并返回居中的目标矩形。【B2V 将删除】"""
        if source_width <= 0.0 or source_height <= 0.0:
            return QRectF(target)
        ratio = min(target.width() / source_width,
                    target.height() / source_height)
        width = source_width * ratio
        height = source_height * ratio
        return QRectF(
            target.center().x() - width / 2.0,
            target.center().y() - height / 2.0,
            width,
            height,
        )

    @staticmethod
    def _sprite_face_rect(image_rect: QRectF) -> QRectF:
        """固定百分比猜测猫脸锚框。【B2V 将删除，由 _face_anchor 取代】"""
        return QRectF(
            image_rect.x() + image_rect.width() * 0.36,
            image_rect.y() + image_rect.height() * 0.20,
            image_rect.width() * 0.28,
            image_rect.height() * 0.56,
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
        """对单个通道的关键帧做循环线性插值。【B2V 保留】"""
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

    def _render_avatar(self, p: QPainter, rect: QRect, st,
                       snap: typing.Dict) -> None:
        """绘制 B2：sprite 底图 + 程序化表情层 + 状态标签。【B2V 改造为矢量底图】"""
        state = snap.get("runtime_state", "IDLE")
        spec = avatar_spec(state)
        expression = expression_spec(spec.expression)
        state_color = _qcolor(st.color(spec.token_key))

        # 状态标签保留原有展示逻辑；token_key 同时表达 warning/error 色语义。
        p.save()
        p.setPen(state_color)
        p.setFont(QFont("Microsoft YaHei", st.font_size("label"), QFont.Bold))
        p.drawText(
            QRect(rect.x(), rect.y() + 4, rect.width(), 24),
            Qt.AlignCenter,
            "%s [%s]" % (spec.label, state),
        )

        # 标签占用顶部空间，底图在其下方 contain 居中显示。
        body_rect = QRectF(rect).adjusted(8.0, 30.0, -8.0, -8.0)
        if self._avatar_base.isNull():
            image_rect = QRectF(body_rect)
            p.setPen(_pen(_qcolor(st.color("text_secondary")), 1))
            p.drawText(body_rect, Qt.AlignCenter, "cat_avatar_base.JPG 未找到")
        else:
            image_rect = self._fit_image_rect(
                float(self._avatar_base.width()),
                float(self._avatar_base.height()),
                body_rect,
            )
            p.drawImage(image_rect, self._avatar_base)
        p.restore()

        # time.monotonic() 是唯一的动画时间基准；静态模式仍然只计算一次
        # 零值状态，不改变底图。
        anim_state = self._anim_state(time.monotonic())
        face_rect = self._sprite_face_rect(image_rect)
        face_center = face_rect.center()
        scale = self._clamp(self._number(anim_state.get("scale"), 1.0),
                            0.80, 1.25)

        p.save()
        p.translate(face_center)
        p.scale(scale, scale)
        p.translate(-face_center)
        self._draw_eyes(
            p,
            face_rect,
            expression,
            self._clamp(self._number(anim_state.get("blink_close"), 0.0),
                        0.0, 1.0),
            self._clamp(self._number(anim_state.get("look_dx"), 0.0),
                        -1.0, 1.0),
            state_color,
        )
        self._draw_mouth(
            p,
            face_rect,
            expression.get("mouth", "line"),
            self._clamp(self._number(anim_state.get("mouth"), 0.0),
                        0.0, 1.0),
            state_color,
        )
        p.restore()
```

**`_anim_state` / `_draw_eyes` / `_draw_mouth`（B2V 全部保留，仅表情层锚框改由 `_face_anchor` 提供）**：
```python
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
```

> **渲染区域几何（当前值）**：右面板 geometry = (704, 40, 576, 640)；`avatar_rect` =
> (708, 48, 568, 397)。矢量底图应直接在 `body_rect`（= avatar_rect 去掉标签区与边距）内
> 归一化绘制；`_face_anchor` 应基于你的矢量几何输出，返回 QRectF 供表情层使用。

### §3.2 状态→表现映射层 —— `board/ui/avatar_fsm.py`（全文，纯逻辑层，两端共用，B2V 不改）

```python
# -*- coding: utf-8 -*-
"""玩偶状态 → 表现映射（Week A2 · 9/9）
纯逻辑层（无渲染依赖）：将 RuntimeState（9 态）映射为玩偶表现规格，
PySide6 原型与板端 LVGL 版均复用本映射，保证"状态→表现"一致。"""
import typing
from dataclasses import dataclass


@dataclass(frozen=True)
class AvatarSpec:
    """一个运行时状态对应的玩偶表现。
    animation   动画标识：breath/attention/listen/think/speak/static
                （参数见 ui_spec/ui_tokens.json -> animations）
    expression  表情：neutral/curious/attentive/thinking/happy/sad
    label       状态文字（显示在玩偶区）
    token_key   主题色令牌键（colors 中的键）
    """
    animation: str
    expression: str
    label: str
    token_key: str = "accent"


# 9 态 → 表现（RuntimeState 名称即 UiState.runtime_state 枚举值）
AVATAR_MAP = {
    "IDLE": AvatarSpec("breath", "neutral", "待机", "accent"),
    "PRESENT": AvatarSpec("attention", "curious", "注视", "accent"),
    "LISTENING": AvatarSpec("listen", "attentive", "聆听", "accent"),
    "THINKING": AvatarSpec("think", "thinking", "思考", "accent"),
    "SPEAKING": AvatarSpec("speak", "happy", "播报", "accent"),
    "CAMERA_LOST": AvatarSpec("static", "neutral", "摄像头丢失", "warning"),
    "NETWORK_LOST": AvatarSpec("breath", "neutral", "本地模式", "warning"),
    "CANCELLED": AvatarSpec("breath", "neutral", "已取消", "warning"),
    "ERROR": AvatarSpec("static", "sad", "错误", "error"),
}

# 表情描述（渲染后端参考；保持简单几何绘制）
EXPRESSION_EYES = {
    "neutral": {"eye_dx": 0.16, "eye_dy": -0.05, "eye_r": 0.055, "mouth": "line"},
    "curious": {"eye_dx": 0.16, "eye_dy": -0.06, "eye_r": 0.062, "mouth": "o"},
    "attentive": {"eye_dx": 0.16, "eye_dy": -0.07, "eye_r": 0.060, "mouth": "line"},
    "thinking": {"eye_dx": 0.16, "eye_dy": -0.05, "eye_r": 0.050, "mouth": "line", "look": "up_right"},
    "happy": {"eye_dx": 0.16, "eye_dy": -0.05, "eye_r": 0.058, "mouth": "arc_up"},
    "sad": {"eye_dx": 0.16, "eye_dy": -0.02, "eye_r": 0.052, "mouth": "arc_down"},
}


def avatar_spec(runtime_state: str) -> AvatarSpec:
    """运行时状态 → 玩偶表现（未知状态回退 IDLE）。"""
    return AVATAR_MAP.get(runtime_state, AVATAR_MAP["IDLE"])


def expression_spec(expression: str) -> typing.Dict:
    """表情 → 几何参数（眼睛/嘴），渲染后端使用。"""
    return EXPRESSION_EYES.get(expression, EXPRESSION_EYES["neutral"])


def all_states() -> typing.List[str]:
    return list(AVATAR_MAP.keys())


# --------------------------------------------------------------------------- #
# 方案 C · 映射层：动画帧表（动画名 → 关键帧序列）
# 每个关键帧为 (通道, 值)：
#   ("eye", v)    → v 为闭眼程度 0.0(睁) ~ 1.0(闭)
#   ("look_dx", v)→ v 为归一化视线偏移 -1.0(左) ~ 1.0(右)
#   ("scale", v)  → 缩放系数（预留）
# 统一引擎按 UiState.avatar_anim 下发动画名 + 参数（周期/强度）播放帧表。
# --------------------------------------------------------------------------- #
ANIMATION_FRAMES = {
    "blink": [("eye", 0.0), ("eye", 1.0), ("eye", 0.0)],     # 眨眼：睁→闭→睁
    "look": [("look_dx", -1.0), ("look_dx", 1.0)],            # 左右扫视
    "breathe": [("scale", 1.02)],                             # 呼吸（预留）
    "speak": [("eye", 0.0), ("mouth", 0.6)],                  # 播报（嘴张，预留通道）
}


def animation_frames(name: str) -> typing.List[typing.Tuple[str, float]]:
    """按动画名查帧表（未定义回退空表）。"""
    return list(ANIMATION_FRAMES.get(name, []))
```

### §3.3 动画数据层 —— `board/ui/ui_state.py`（avatar_anim 相关，B2V 不改）

```python
# -*- coding: utf-8 -*-
"""UiState —— UI 状态聚合（Week A2 · 9/10）
线程安全：UI 线程读 snapshot()，事件线程（EventBus 分发）写 update()。
输出符合 ui_spec/ui_state.schema.json。
"""
import threading
import typing

from board.runtime.event_bus import EventEnvelope
from board.runtime.events import EventType

_DEVICE_KEYS = ("camera", "npu", "pl", "audio", "network")


class UiState:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._s = {
            "schema_version": "1.0",
            "runtime_state": "IDLE",
            "mode": "CORE_LOCAL",
            "camera": {"state": "idle", "detail": ""},
            "npu": {"state": "idle", "detail": ""},
            "pl": {"state": "idle", "detail": ""},
            "audio": {"state": "idle", "detail": ""},
            "network": {"state": "offline", "detail": ""},
            "privacy": False,
            "scene": {
                "scene_seq": 0, "people_count": 0,
                "current_target": None, "recent_events": [],
            },
            "dialogue": {"last_reply": "", "thinking": False},
            "fps": 0.0,
            "avatar_anim": {"name": "", "params": {}, "enabled": False},
        }
        self._recent_text = []  # 事件文本（演示用），容量 8

    def snapshot(self) -> typing.Dict:
        with self._lock:
            return dict(self._s)

    def set_avatar_anim(self, name: str, params: typing.Optional[typing.Dict] = None,
                        enabled: bool = False) -> None:
        """方案 C·数据层：上层下发当前动画名与参数（enabled=False 时渲染端静态）。

        name 对应 avatar_fsm.ANIMATION_FRAMES 帧表；params 含 period_ms/intensity 等。
        """
        with self._lock:
            self._s["avatar_anim"] = {
                "name": name,
                "params": dict(params or {}),
                "enabled": bool(enabled),
            }
```

### §3.4 样式加载器 —— `board/ui/qt_style.py`（全文，B2V 不改）

```python
# -*- coding: utf-8 -*-
"""UI 样式加载器：从 ui_spec/ 读取一致性合同（布局/令牌），供渲染后端使用。
PySide6 原型与板端 LVGL 版都从这里读取同一份数值，保证布局/配色一致。"""
import json
import os
import typing

_SPEC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ui_spec")


class UiStyle:
    def __init__(self, spec_dir: typing.Optional[str] = None) -> None:
        d = os.path.normpath(spec_dir or _SPEC_DIR)
        with open(os.path.join(d, "ui_layout_spec.json"), encoding="utf-8") as f:
            self.layout = json.load(f)
        with open(os.path.join(d, "ui_tokens.json"), encoding="utf-8") as f:
            self.tokens = json.load(f)

    @property
    def canvas(self) -> typing.Tuple[int, int]:
        c = self.layout["canvas"]
        return c["width"], c["height"]

    def rect(self, key: str) -> typing.Tuple[int, int, int, int]:
        r = self.layout[key]
        return r["x0"], r["y0"], r["x1"] - r["x0"], r["y1"] - r["y0"]

    def color(self, key: str) -> str:
        return self.tokens["colors"].get(key, "#FFFFFF")

    def font_size(self, key: str) -> int:
        return self.tokens["fonts"].get(key, 14)

    def line_width(self, key: str) -> int:
        return self.tokens["line_widths"].get(key, 1)

    def animation(self, key: str) -> typing.Dict:
        return self.tokens["animations"].get(key, {"period_ms": 1000, "scale": 0.02})

    def status_items(self) -> typing.List[str]:
        return list(self.layout.get("status_items", []))


_style: typing.Optional[UiStyle] = None


def get_style() -> UiStyle:
    global _style
    if _style is None:
        _style = UiStyle()
    return _style
```

### §3.5 样式令牌与布局合同 —— `ui_spec/ui_tokens.json`、`ui_spec/ui_layout_spec.json`（B2V 不改）

```json
// ui_spec/ui_tokens.json
{
  "schema_version": "1.0",
  "title": "UiTokens",
  "description": "UI 样式令牌：颜色/线宽/字号/间距/动画参数。PySide6 与 LVGL 版读取同一份令牌。",
  "colors": {
    "bg": "#101820", "panel_bg": "#16202B", "panel_border": "#2A3A4A",
    "accent": "#4FC3F7", "accent_dark": "#0288D1", "warning": "#FFB300",
    "error": "#E53935", "success": "#66BB6A", "privacy_mask": "#1A1A2E",
    "text_primary": "#E8EEF4", "text_secondary": "#9AA8B5",
    "box": "#4FC3F7", "zone": "#FFB300"
  },
  "line_widths": { "box": 2, "zone": 1, "status": 1 },
  "fonts": { "title": 18, "label": 14, "small": 12, "dialogue": 16 },
  "spacing": { "panel_padding": 8, "status_gap": 12 },
  "animations": {
    "breath":   { "period_ms": 3000, "scale": 0.06 },
    "attention":{ "period_ms": 1500, "scale": 0.04 },
    "listen":   { "period_ms": 800,  "scale": 0.03 },
    "think":    { "period_ms": 1200, "scale": 0.02 },
    "speak":    { "period_ms": 500,  "scale": 0.08 }
  }
}
```

```json
// ui_spec/ui_layout_spec.json
{
  "schema_version": "1.0",
  "title": "UiLayoutSpec",
  "description": "UI 像素级布局合同（1280×720）。PySide6 原型与板端 LVGL 版必须按同一数值实现。",
  "canvas": { "width": 1280, "height": 720 },
  "split": { "left_ratio": 0.55, "right_ratio": 0.45, "left_width": 704, "right_width": 576 },
  "top_bar": { "y0": 0, "y1": 40, "height": 40 },
  "left_panel": { "x0": 0, "x1": 704, "y0": 40, "y1": 680, "padding": 8 },
  "right_panel": { "x0": 704, "x1": 1280, "y0": 40, "y1": 680, "padding": 12 },
  "status_bar": { "y0": 680, "y1": 720, "height": 40 },
  "left_inner": { "info_line": { "height": 22 }, "events_area": { "height": 60 } },
  "right_inner": { "avatar_ratio": 0.62, "dialogue_ratio": 0.38 },
  "status_items": ["camera", "npu", "pl", "audio", "lan", "save", "privacy", "mode"]
}
```

> 表情/动画涉及的令牌：`accent #4FC3F7`（玩偶主色）、`warning #FFB300`、`error #E53935`、
> `text_primary #E8EEF4`、`text_secondary #9AA8B5`；动画周期见 `animations`。

---

## §4 上下文文档（接口规约与 LVGL 迁移约束）

### §4.1 方案 C 三层接口规范（摘录自 docs/NEW_WINDOW_PROMPT.md · 五）

UI 动画采用方案 C，三层接口职责如下（**不得破坏此分层**）：

| 层 | 载体 | 职责 |
|---|---|---|
| **数据层** | `UiState.avatar_anim`（`set_avatar_anim(name, params, enabled)` / `snapshot()["avatar_anim"]`） | 上层下发当前动画名与参数；`enabled=False` 时渲染端静态 |
| **映射层** | `avatar_fsm.ANIMATION_FRAMES` + `animation_frames(name)` | 动画名 → 关键帧序列（帧表），与渲染后端无关 |
| **执行层** | `AvatarPanel._anim_state(t)`（统一引擎）+ `_draw_eyes/_draw_mouth`（绘制原语） | 帧表/参数 → 当前动画值 → 绘制原语消费 |

- 渲染接入点固定为 `AvatarPanel._render_avatar`；B2V 在此方法内新增矢量主体绘制。
- 数据合同以 `ui_spec/*.json` 为唯一权威数值；**改合同须同步提升 schema 版本并通知依赖方**。
- 环境标签：PC / SIMULATED / BOARD_REQUIRED 严格区分；本次实现为 **PC（PySide6 原型）**，
  LVGL 版属 10 月板端阶段，本任务只交付"迁移指南"，不写 LVGL 实际代码。

### §4.2 LVGL 迁移规约（摘录自 docs/ui_consistency_checklist.md · 四）

| # | 项 | 源文件 | 状态 |
|---|---|---|---|
| M1 | 9 态→表现映射 | `avatar_fsm.py` AVATAR_MAP | ✅ 两端复用 |
| M2 | 表情几何参数 | `avatar_fsm.py` EXPRESSION_EYES | ✅ 两端复用 |
| M3 | UI 状态聚合 | `ui_state.py`（事件→UiState） | ✅ 两端复用 |
| M4 | 数据合同 | `ui_spec/ui_state.schema.json` | ✅ 两端复用 |
| M5 | 方案C·动画数据接口 | `UiState.avatar_anim` | ✅ 接口就绪 |
| M6 | 方案C·动画帧表 | `avatar_fsm.ANIMATION_FRAMES` | ✅ 接口就绪 |
| M7 | 方案C·执行层 | `AvatarPanel._anim_state` + `_draw_eyes/_draw_mouth` | ✅ B2 已实现（B2V 保留） |
| M8 | 渲染入口 | `AvatarPanel._render_avatar` | ⬜ B2V 改造中（矢量底图） |

一致性要求：PySide6 原型与板端 LVGL 版的**布局/配色/逻辑/数据**逐项一致；
LVGL 迁移不得另起一套状态映射或数据合同（禁止同时维护两套 UI）。

### §4.3 动画驱动方式与帧表映射约定

1. **驱动**：`MainWindow._refresh` 每 50ms（20Hz）对 `avatar_panel.update()` 触发重绘；
   `_render_avatar` 在每次 `paintEvent` 中被调用。动画时间基准用 `time.monotonic()`；
   `_anim_state(t)` 的 `t` 传 `time.monotonic()`。
2. **帧表通道 → 动画值字典映射**：
   - `("eye", v)`      → `blink_close` = v（0 睁 … 1 闭）
   - `("look_dx", v)`  → `look_dx` = v（-1 左 … 1 右）
   - `("scale", v)`    → `scale` = v（>1 放大）
   - `("mouth", v)`    → `mouth` = v（0 闭 … 1 全张）
   - 帧表为关键帧序列，循环线性插值；周期优先级：`params.period_ms` → `ui_tokens.json`
     `animations[animation].period_ms` → 1000ms。
3. **表达式几何**：`expression_spec(expression)` 返回归一化参数：`eye_dx/eye_dy/eye_r`
   （眼睛位置/半径比例）、`mouth`（`line/o/arc_up/arc_down`）、`look`（可选视线方向）。
4. **状态色**：`AvatarSpec.token_key` 对应 `ui_tokens.json` 颜色键；表情层使用该色。

### §4.4 为什么返工为矢量底图（当前 B2 位图方案的问题）

| # | B2 位图方案问题 | B2V 矢量方案解决 |
|---|---|---|
| 1 | 表情锚框靠固定百分比猜测（`_sprite_face_rect`），与 JPG 猫脸易错位 | 矢量路径由你书写，猫脸位置精确可知，`_face_anchor` 由几何直接推导 |
| 2 | 位图缩放有锯齿、无 Alpha（JPG 矩形贴图，透明区只能靠背景色） | 矢量任意缩放无损、天然透明背景 |
| 3 | 内存：568×397 ARGB≈902KB 帧缓冲；LVGL 需 JPG 解码器 | 无位图内存；LVGL `lv_canvas` 矢量绘制或预渲染 RGB565 数组 |
| 4 | 位图与表情层两个体系，视觉不统一 | 主体+表情同一矢量风格，视觉一体 |

---

## §5 交付要求（GPT 输出物清单）

请按以下三部分输出，全部写入一个 Markdown 回复（或附件）：

### 5.1 成品代码
1. 完整实现/重构后的：
   - **`_draw_sprite_base(self, p, rect, st, spec)`**：矢量主体绘制——用 `QPainterPath`/`QPainter`
     严格描摹附件 `cat_avatar_base.JPG` 的猫头主体（头形/双耳/脸颊/花纹/胡须等），在 `rect`
     （= `body_rect`，约 552×359 px）内归一化绘制，**不得加载任何位图**；
   - **`_face_anchor(self, rect) -> QRectF`**：由你的矢量几何推导的猫脸锚框（眼睛/嘴巴放置区域），
     替代 `_sprite_face_rect`；
   - **修改后的 `_render_avatar`**：底图段改为 `_draw_sprite_base`，表情层锚框改用 `_face_anchor`；
   - 明确**删除清单**：`_avatar_base_path`/`_avatar_base`（__init__ 中）、`_fit_image_rect`、
     `_sprite_face_rect`、`QImage` 导入（若不再使用）。
2. 代码须满足：
   - 无新增第三方依赖（仅 PySide6 标准 API + Python 标准库）；
   - 矢量主体配色**按附件 JPG 原图**；表情层用 `AvatarSpec.token_key` 色；
   - `enabled=False` 时静态绘制（矢量主体 + 当前 expression 静态表情 + 状态标签）；
   - `enabled=True` 时按帧表 + 周期插值驱动表情层；
   - 状态标签行保留（`spec.label [runtime_state]`）。
3. **不得修改** `avatar_fsm.py`、`ui_state.py`、`ui_spec/*.json` 的公开接口与合同版本。

### 5.2 LVGL 迁移指南与技术总结
1. **PySide6 → LVGL 映射表**：矢量主体 `QPainterPath` → `lv_canvas` 逐图元映射
   （线段/贝塞尔/圆/填充）或预渲染 RGB565 sprite 数组 → `lv_image`；表情层 → `lv_canvas`
   或 `lv_obj` 组合；状态文字 → `lv_label`；动画时间 → `lv_anim`/`lv_timer`。
2. **内存与性能评估**：
   - 无位图后的内存收益（对比：RGB565 底图 450KB / ARGB8888 902KB → 纯矢量 0KB 帧缓冲 +
     `lv_canvas` 局部画布约 63KB）；
   - 20Hz 下矢量图元数量与 CPU 开销估算；脏区刷新/降频优化建议；
   - LVGL 配置项（`LV_COLOR_DEPTH`、`LV_USE_CANVAS`、image cache 等）。
3. **一致性核对**：迁移后如何满足 §4.2 M1–M8（复用项 + 等价实现项）。

### 5.3 变更摘要
- 列出改动文件与函数清单、删除项清单、测试建议（建议新增 `_face_anchor` 合理性断言）。

---

## §6 验收约束（Cline 接入侧，供人3 使用）

收到 GPT 成品代码后，Cline 按以下流程接入工程：

1. 将成品代码合入 `board/ui/qt_widgets.py`：
   - 删除位图加载（`_avatar_base_path`/`_avatar_base`）、`_fit_image_rect`、`_sprite_face_rect`；
   - 接入 `_draw_sprite_base` + `_face_anchor` + 修改后的 `_render_avatar`；
   - 保留 `_anim_state`/`_draw_eyes`/`_draw_mouth`/`_clamp`/`_number`/`_cyclic_keyframe_value`；
   - 保留 `paintEvent` 调用签名与现有绘制布局。
2. 运行 `python -m pytest tests/ -q` → 保持 **84 passed 无回归**（现有 7 个 B2 测试
   只测 `_anim_state`/`_cyclic_keyframe_value`，不受底图方法删除影响）；
3. 出图验证（PC / SIMULATED）：`python examples/run_ui.py --state X --screenshot evidence_shots/b2v_X.png`
   覆盖 `IDLE / PRESENT / LISTENING / THINKING / SPEAKING / CAMERA_LOST / NETWORK_LOST / ERROR /
   CANCELLED` 九态（表情变化 + token_key 配色 + **矢量主体与 JPG 参考图的视觉一致性**）；
4. `python examples/smoke.py` 冒烟通过；
5. git 提交：`refactor: 玩偶渲染 B2V（QPainterPath 矢量底图替代位图，_face_anchor 精确锚框）`；
6. 同步更新 `docs/ui_consistency_checklist.md`（M8 勾选、截图证据行）与
   `docs/NEW_WINDOW_PROMPT.md` 进度表。

---

*（本提示词文件由 Cline 依据 wujing-lite 工程现状生成，2026-08-31 · PC / SIMULATED。
使用前请确认已把 §0 所述图片附件 `cat_avatar_base.JPG` 一并发送给 GPT。）*