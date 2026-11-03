# 🤖 GPT Prompt · 雾镜 Lite 玩偶方案 B2（Sprite 底图 + 程序化表情层）

> 用途：将本文件 **§2–§5** 整体复制发给 GPT（ChatGPT），由 GPT 完成方案 B2 的
> `_render_avatar` 代码实现 + LVGL 迁移指南 + 技术总结。GPT 返回后，把成品代码与
> 文档交回 Cline（人3 开发会话）接入工程并测试提交。
>
> 工程：`wujing-lite`（2026 全国大学生嵌入式芯片与系统设计竞赛·FPGA 创新设计赛道，
> 复旦微 FMQL30TAI）｜ 无板开发月 A2 阶段（PC / SIMULATED，板端 LVGL 于 10 月迁移）
> 生成日期：2026-08-31 ｜ 维护：人3（Runtime & Integration）

---

## §0 使用说明（发给 GPT 前先读）

- **只把 §2–§5 复制给 GPT**（§0/§1 是给项目组内的使用与交接说明，可一并附上，不影响）。
- 底图真实路径：`board/ui/image/cat_avatar_base.JPG`（工程根相对路径，JPG、无 Alpha 通道）。
- 现有基线：`python -m pytest tests/ -q` → **77 passed**（A1 60 + A2 15 + 方案C 接口 2）。
  当前 `_render_avatar` 为**占位实现**（仅画状态文字，无猫脸），本任务将其替换为方案 B2。
- GPT 交付物验收、接入与 git 提交由 Cline 负责，见 §6。

---

## §1 角色与任务

> **角色**：你是一名精通 PySide6 与 LVGL 嵌入式图形开发的专家。
> **任务目标**：根据下方提供的代码框架，实现方案 B2（基于单色/几何猫头底图 +
> 程序化/局部表情渲染的 `_render_avatar` 接口），并输出 LVGL 迁移指南与技术总结文档。

## §2 方案 B2 核心需求

1. **底图**：以 `board/ui/image/cat_avatar_base.JPG` 为玩偶主体底图（无 Alpha，矩形贴图），
   保持单色/极简几何观感；渲染区域为 `avatar_rect`（568 × 397 px），底图等比缩放居中放置。
2. **程序化表情层**：眼睛（眨眼 `blink_close` / 视线偏移 `look_dx`）、嘴巴（张合 `mouth` /
   弧度）、整体缩放 `scale` 全部由代码绘制（PySide6 `QPainter` 矢量原语）叠加在底图之上，
   不得依赖更多图片素材。
3. **管线兼容**：完美消费 `_anim_state(t)` 输出的 `{"blink_close","look_dx","scale","mouth"}`
   驱动参数，以及 `expression_spec(expression)` 的几何参数（`eye_dx/eye_dy/eye_r/mouth/look`）；
   状态文字（`spec.label + [runtime_state]`）保留原有展示逻辑。
4. **性能与迁移**：单图 + 少量矢量原语，低开销；未来平滑迁移板端 LVGL——
   `lv_img` 显示底图 + `lv_canvas` 绘制表情层，表情几何参数与配色与 PySide6 版逐项一致。

### 附加硬约束
- 渲染函数签名 **不得改变**：`_render_avatar(self, p: QPainter, rect: QRect, st, snap: dict)`，
  `paintEvent` 已按此签名调用（见 §3.1）。
- **不得新增第三方依赖**（工程仅 `jsonschema` + `PySide6`）：JPG 加载用 `QImage/QPixmap` 内置
  JPG 插件，不引入 Pillow。
- 资源路径用**工程根相对解析**（`os.path`，兼容 `run_ui.py` 在任意 cwd 下运行）。
- 必须**保持 77 个现有 pytest 全绿**：现有测试只覆盖逻辑层（`avatar_fsm.py` / `ui_state.py`），
  不覆盖渲染，因此 `_render_avatar` 内部实现可自由修改，但不得改逻辑层接口。
- `UiState.avatar_anim["enabled"]=False`（默认）时渲染**静态**底图 + 表情静态几何；`enabled=True`
  时按动画帧表推进（见 §4.3）。

---

## §3 上下文代码（真实工程摘录）

### §3.1 渲染接入点与执行层 —— `board/ui/qt_widgets.py`（AvatarPanel 相关）

```python
# -*- coding: utf-8 -*-
"""PySide6 面板：CameraPanel（左 55%）、StatusBar（底部）、AvatarPanel（右 45%）。
渲染后端（无板阶段）；板端 LVGL 版复用逻辑层（avatar_fsm / ui_state），
仅替换 paint 实现，布局/配色按 ui_spec/ 合同。"""
import math
import typing

from PySide6.QtCore import QRect, QTimer, Qt, QPoint
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QPolygon, QPainterPath
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


class AvatarPanel(QWidget):
    """右侧玩偶区（45%）：状态动画 + 状态标签 + 对话文字。"""

    def __init__(self, ui_state: UiState, parent: typing.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.ui = ui_state
        self.style = get_style()
        self.setMinimumSize(576, 640)
        # 动画接口（方案 C）：由 MainWindow._refresh 统一驱动重绘；动画引擎见 _anim_state

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


    # ------------------------------------------------------------------ #
    def _render_avatar(self, p: QPainter, rect: QRect, st, snap: typing.Dict) -> None:
        """玩偶渲染接口占位（待方案 B2 替换）。

        方案 C 接口：
          数据层  UiState.avatar_anim（上层下发动画名+参数，见 ui_state.py）
          映射层  avatar_fsm.ANIMATION_FRAMES（动画帧表，见 avatar_fsm.py）
          执行层  self._anim_state(t) → 动画值 dict → 绘制原语消费
        当前 enabled=False → 静态（仅状态文字）。
        """
        state = snap.get("runtime_state", "IDLE")
        spec = avatar_spec(state)
        _av = self._anim_state(0.0)  # noqa: F841 - TODO(新方案): 消费动画值驱动渲染

        # 状态标签（保留：状态信息展示）
        p.setPen(_qcolor(st.color("text_primary")))
        p.setFont(QFont("Microsoft YaHei", st.font_size("label"), QFont.Bold))
        p.drawText(QRect(rect.x(), rect.y() + 4, rect.width(), 24), Qt.AlignCenter,
                   "%s [%s]" % (spec.label, state))
        p.setPen(_qcolor(st.color("text_secondary")))
        p.setFont(QFont("Microsoft YaHei", st.font_size("small")))
        p.drawText(QRect(rect.x(), rect.y() + rect.height() // 2 + 30, rect.width(), 24),
                   Qt.AlignCenter, "渲染待接入 · anim=%s expr=%s" % (spec.animation, spec.expression))

    def _anim_state(self, t: float) -> typing.Dict:
        """方案 C·执行层：统一动画引擎——读 UiState.avatar_anim + 帧表 → 当前动画值。

        TODO(新方案)：按帧表/参数插值出 blink_close / look_dx / scale / mouth 等。
        当前 enabled=False 返回静态值。
        """
        anim = self.ui.snapshot().get("avatar_anim", {})
        if not anim.get("enabled"):
            return {"blink_close": 0.0, "look_dx": 0, "scale": 1.0, "mouth": 0.0}
        frames = animation_frames(anim.get("name", ""))  # noqa: F841 - TODO(新方案) 帧表推进
        return {"blink_close": 0.0, "look_dx": 0, "scale": 1.0, "mouth": 0.0}

    def _draw_eyes(self, blink_close: float, look_dx: int) -> None:  # pragma: no cover
        """方案 C·绘制原语：眼睛。TODO(新方案) 由新渲染方案实现。"""
        raise NotImplementedError("新动画渲染方案待接入")

    def _draw_mouth(self, open_ratio: float) -> None:  # pragma: no cover
        """方案 C·绘制原语：嘴。TODO(新方案) 由新渲染方案实现。"""
        raise NotImplementedError("新动画渲染方案待接入")


    def _paint_dialogue(self, p: QPainter, rect: QRect, st, snap: typing.Dict) -> None:
        p.setPen(_qcolor(st.color("panel_border")))
        p.drawLine(rect.x(), rect.y(), rect.x() + rect.width(), rect.y())
        dialogue = snap.get("dialogue", {})
        reply = dialogue.get("last_reply", "")
        thinking = dialogue.get("thinking", False)
        p.setFont(QFont("Microsoft YaHei", st.font_size("dialogue")))
        p.setPen(_qcolor(st.color("accent")))
        if thinking:
            p.drawText(rect, Qt.AlignLeft | Qt.AlignTop, "……思考中")
        elif reply:
            p.drawText(rect.adjusted(4, 6, -4, -4),
                       Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, reply)
        else:
            p.setPen(_qcolor(st.color("text_secondary")))
            p.drawText(rect, Qt.AlignCenter, "（等待对话）")
```


### §3.2 状态→表现映射层 —— `board/ui/avatar_fsm.py`（全文，纯逻辑层，两端共用）

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

### §3.3 动画数据层 —— `board/ui/ui_state.py`（avatar_anim 相关）

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

### §3.4 样式加载器 —— `board/ui/qt_style.py`（全文）

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

### §3.5 样式令牌与布局合同 —— `ui_spec/ui_tokens.json`、`ui_spec/ui_layout_spec.json`

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


## §4 上下文文档（接口规约与 LVGL 迁移约束）

### §4.1 方案 C 三层接口规范（摘录自 docs/NEW_WINDOW_PROMPT.md · 五）

UI 动画采用方案 C，三层接口职责如下（**不得破坏此分层**）：

| 层 | 载体 | 职责 |
|---|---|---|
| **数据层** | `UiState.avatar_anim`（`set_avatar_anim(name, params, enabled)` / `snapshot()["avatar_anim"]`） | 上层下发当前动画名与参数；`enabled=False` 时渲染端静态 |
| **映射层** | `avatar_fsm.ANIMATION_FRAMES` + `animation_frames(name)` | 动画名 → 关键帧序列（帧表），与渲染后端无关 |
| **执行层** | `AvatarPanel._anim_state(t)`（统一引擎）+ `_draw_eyes/_draw_mouth`（绘制原语） | 帧表/参数 → 当前动画值 → 绘制原语消费 |

- 渲染接入点固定为 `AvatarPanel._render_avatar`（当前占位、enabled=False 静态）。
- 数据合同以 `ui_spec/*.json` 为唯一权威数值；**改合同须同步提升 schema 版本并通知依赖方**。
- 环境标签：PC / SIMULATED / BOARD_REQUIRED 严格区分；本次实现为 **PC（PySide6 原型）**，
  LVGL 版属 10 月板端阶段，本任务只交付"迁移指南"，不写 LVGL 实际代码。

### §4.2 LVGL 迁移规约（摘录自 docs/ui_consistency_checklist.md · 四）

| # | 项 | 源文件 | 状态 |
|---|---|---|---|
| M1 | 9 态→表现映射 | `avatar_fsm.py` AVATAR_MAP | ✅ 两端复用 |
| M2 | 表情几何参数 | `avatar_fsm.py` EXPRESSION_EYES | ✅ 两端复用（待新方案消费） |
| M3 | UI 状态聚合 | `ui_state.py`（事件→UiState） | ✅ 两端复用 |
| M4 | 数据合同 | `ui_spec/ui_state.schema.json` | ✅ 两端复用 |
| M5 | 方案C·动画数据接口 | `UiState.avatar_anim` | ✅ 接口就绪（enabled=False 静态） |
| M6 | 方案C·动画帧表 | `avatar_fsm.ANIMATION_FRAMES` + `animation_frames()` | ✅ 接口就绪 |
| M7 | 方案C·执行层 | `AvatarPanel._anim_state` + `_draw_eyes/_draw_mouth` | ⬜ 本任务实现 |
| M8 | 渲染入口占位 | `AvatarPanel._render_avatar` | ✅ 占位（本任务替换为 B2） |

一致性要求：PySide6 原型与板端 LVGL 版的**布局/配色/逻辑/数据**逐项一致；
LVGL 迁移不得另起一套状态映射或数据合同（禁止同时维护两套 UI）。

### §4.3 动画驱动方式与帧表映射约定（Cline 补充，务必遵守）

1. **驱动**：`MainWindow._refresh` 每 50ms（20Hz）对 `avatar_panel.update()` 触发重绘；
   `_render_avatar` 在每次 `paintEvent` 中被调用。动画时间基准用 `time.monotonic()`，
   不要用 `QElapsedTimer` 之外自造的计时；`_anim_state(t)` 的 `t` 建议传 `time.monotonic()`。
2. **帧表通道 → 动画值字典映射**：
   - `("eye", v)`      → `blink_close` = v（0 睁 … 1 闭）
   - `("look_dx", v)`  → `look_dx` = v（-1 左 … 1 右）
   - `("scale", v)`    → `scale` = v（>1 放大）
   - `("mouth", v)`    → `mouth` = v（0 闭 … 1 全张）
   - 帧表为关键帧序列，可做线性插值；周期优先取 `UiState.avatar_anim["params"]["period_ms"]`，
     缺省取 `ui_tokens.json["animations"][animation]["period_ms"]`。
3. **表达式几何**：`expression_spec(expression)` 返回归一化参数（相对渲染区的比例系数）：
   `eye_dx`（眼横向偏移比例）、`eye_dy`（眼纵向偏移比例，负值偏上）、`eye_r`（眼半径比例）、
   `mouth`（嘴型标识：`line` 直线 / `o` O 型 / `arc_up` 上弧 / `arc_down` 下弧）、
   `look`（可选，视线方向，如 `up_right`）。渲染端自行换算为 `avatar_rect` 内像素坐标。

## §5 交付要求（GPT 输出物清单）

请按以下三部分输出，全部写入一个 Markdown 回复（或附件）：

### 5.1 成品代码
1. 完整实现/重构后的 `_render_avatar` 及相关组件（`_anim_state`、`_draw_eyes`、`_draw_mouth`，
   以及你认为必要的辅助方法/常量），**可直接替换** `board/ui/qt_widgets.py` 中 AvatarPanel
   的对应方法；保持 `paintEvent` → `_render_avatar(p, rect, st, snap)` 调用签名不变。
2. 代码须满足：
   - 无新增第三方依赖（仅 `PySide6` 标准控件/绘制 API + Python 标准库）；
   - 底图加载幂等（重复重绘不重复 IO），建议在 `__init__` 中一次 `QImage/QPixmap` 加载；
   - `enabled=False` 时静态绘制（底图 + 当前 expression 静态几何 + 状态标签）；
   - `enabled=True` 时按帧表 + 周期插值出 `blink_close/look_dx/scale/mouth` 并驱动表情层；
   - 状态标签行保留（`spec.label [runtime_state]`，含 token_key 配色语义）。
3. 可选：如你认为现有 `EXPRESSION_EYES` 归一化参数需要解释/微调才能适配底图，请说明，
   但**不得修改 `avatar_fsm.py` 与 `ui_state.py` 的公开接口**（保持 77 测试全绿）。

### 5.2 LVGL 迁移指南与技术总结
1. **PySide6 → LVGL 映射表**：逐项说明当前实现如何映射到 LVGL 控件/API，例如：
   - 底图 `QImage/QPixmap` → `lv_img`（LVGL v9 `lv_image`；数据来源：JPG 解码或转 C 数组 RGB565）；
   - 表情矢量绘制 → `lv_canvas`（点/线/圆弧/填充）或 `lv_obj` 组合，说明画布尺寸与逐像素 vs 矢量权衡；
   - 状态文字 → `lv_label`；动画时间基准 → `lv_anim` 或 `lv_timer`。
2. **内存与性能评估**：
   - JPG 底图解码后内存估算（示例基准：568×397 RGB565 ≈ 450KB；ARGB8888 ≈ 902KB；
     含 Alpha PNG 与纯矢量绘制的对比）；
   - 表情层矢量绘制在 20Hz 下的 CPU/GPU 开销估算与优化建议（缓存画布/降频到 10Hz 等）；
   - LVGL 配置项（如 `LV_USE_CANVAS`、`LV_IMG_CACHE_DEF_SIZE`、颜色深度配置）。
3. **一致性核对**：说明迁移后如何满足 §4.2 的 M1–M8（哪些复用、哪些等价实现）。

### 5.3 变更摘要
- 列出你改动的文件与函数清单、测试建议（若有新增逻辑，建议的 pytest 断言）。

---

## §6 验收约束（Cline 接入侧，供人3 使用）

收到 GPT 成品代码后，Cline 按以下流程接入工程：

1. 将成品代码合入 `board/ui/qt_widgets.py`（保留 `paintEvent` 调用签名与现有绘制布局）；
2. 运行 `python -m pytest tests/ -q` → 保持 **77 passed 无回归**；
3. 出图验证（PC / SIMULATED）：
   - `python examples/run_ui.py --state IDLE --screenshot evidence_shots/b2_idle.png`
   - 依次 `PRESENT / LISTENING / THINKING / SPEAKING / CAMERA_LOST / NETWORK_LOST / ERROR`
     （覆盖表情变化与 token_key 配色）；
   - `python examples/run_ui.py --demo`（动画切换窗口）人工目检眨眼/扫视/嘴动；
4. `python examples/smoke.py` 冒烟通过；
5. git 提交：`feat: 玩偶渲染方案 B2（sprite 底图 + 程序化表情层）接入 _render_avatar`；
6. 同步更新 `docs/ui_consistency_checklist.md`（M7 勾选、M8 状态、截图证据行）与
   `docs/NEW_WINDOW_PROMPT.md` 进度表。

---

*（本提示词文件由 Cline 依据 wujing-lite 工程现状生成，2026-08-31 · PC / SIMULATED）*
