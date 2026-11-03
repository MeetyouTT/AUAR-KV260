# 雾镜 Lite 玩偶方案 B2 交付物

本文档是依据 `GPT_PROMPT_AVATAR_B2.md` §2–§5 整理的接入成品。当前工作区未包含 `wujing-lite` 源码，因此以下代码尚未写入实际 `board/ui/qt_widgets.py`，也未执行工程测试或截图命令；接入者可将代码块中的导入、`__init__` 增量和 `AvatarPanel` 私有方法合入现有文件。

## 1. PySide6 成品代码

### 1.1 导入增量

在现有导入中补充以下标准库/PySide6 符号；已有导入不要重复添加：

```python
import os
import time

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QBrush, QImage
```

现有代码已经导入 `QColor`、`QFont`、`QPainter`、`QPen`、`QPainterPath`、`QPolygon` 和 `QRect`，可继续复用。

### 1.2 `AvatarPanel.__init__` 增量

保留原有初始化内容，在 `self.setMinimumSize(...)` 后加入一次性底图加载。路径由 `__file__` 回到工程根目录，因此 `examples/run_ui.py` 从任意 cwd 启动都能定位资源；重复重绘不会再次产生文件 IO。

```python
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
```

### 1.3 可直接替换的 AvatarPanel 私有实现

下面的方法保持 `_render_avatar(self, p, rect, st, snap)` 的入口签名不变。`_draw_eyes`、`_draw_mouth` 是执行层私有方法，参数扩展只影响本类内部调用，不改变 `avatar_fsm.py` 或 `ui_state.py` 的公开接口。

```python
    # ------------------------------------------------------------------ #
    @staticmethod
    def _fit_image_rect(source_width: float, source_height: float,
                        target: QRectF) -> QRectF:
        """将底图等比 contain 到 target，并返回居中的目标矩形。"""
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
        """返回随 sprite 缩放的猫脸锚框。

        `cat_avatar_base.JPG` 是宽幅极简猫头标识，猫脸约位于 sprite
        的 x=36%..64%、y=20%..76%。把锚点集中在这里，可以让
        EXPRESSION_EYES 的归一化参数在不同窗口尺寸下保持一致。
        """
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

    def _render_avatar(self, p: QPainter, rect: QRect, st,
                       snap: typing.Dict) -> None:
        """绘制 B2：sprite 底图 + 程序化表情层 + 状态标签。"""
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
```

实现说明：

- `enabled=False` 返回零动画值，底图和当前表达式静态绘制。
- `enabled=True` 按 `period_ms` 循环线性插值；参数优先级是 `UiState.avatar_anim.params.period_ms`，其次是 `ui_tokens.json` 中当前动画配置，最后是 1000 ms。
- 帧表的 `eye/look_dx/scale/mouth` 通道分别映射到 `blink_close/look_dx/scale/mouth`；未知通道忽略，不会破坏现有逻辑层。
- `intensity` 是兼容性增强参数，缺省值为 1.0；scale 围绕 1.0 缩放，其他通道围绕 0 缩放。
- `_sprite_face_rect` 的锚点是针对题目提供的宽幅 `cat_avatar_base.JPG` 的相对比例。若实际工程中的 JPG 被替换为裁剪版，只需调整这一处常量，不修改 `avatar_fsm.py` / `ui_state.py` 接口。
- 表情层直接叠加在底图上，不加载额外素材；底图使用 Qt 内置 JPG 解码。

## 2. LVGL 迁移指南

### 2.1 PySide6 → LVGL 映射

| PySide6 原型 | LVGL 端等价实现 | 一致性要点 |
|---|---|---|
| `QImage(cat_avatar_base.JPG)` | LVGL v9 `lv_image`（v8 名称为 `lv_img`）；资源可由 JPG decoder 读取，或预转换为 RGB565 C 数组 | 使用同一张底图、同一 contain 居中矩形；设备侧优先预转换 RGB565，避免运行时 JPG 解码抖动 |
| `QPainter.drawImage()` | `lv_image_set_src()` + `lv_obj_set_pos/size()` | 图片显示矩形由同一宽高比计算，禁止拉伸变形 |
| `QPainterPath` 嘴线 | `lv_canvas` 像素/线段绘制，或用 `lv_obj` 组合近似弧线 | 表情层使用和 PySide6 相同的归一化参数、颜色和锚点；无 GPU 时优先短线段/小画布 |
| `drawEllipse` 眼睛和 O 嘴 | `lv_canvas` 的圆/填充圆，或小尺寸圆形 `lv_obj` | blink 时切换为短圆头线；眼睛位置应用同一 `eye_dx/eye_dy/look_dx` |
| `p.scale(scale, scale)` | 在表情层绘制前围绕 face center 手动变换坐标；或调整组合对象的 transform/尺寸 | 底图不跟随缩放，表情层围绕相同 face center 缩放 |
| 状态标签 `drawText` | `lv_label` | 文本仍为 `spec.label + " [" + runtime_state + "]"`，颜色取 `spec.token_key` |
| 对话区 `drawText(...TextWordWrap)` | `lv_label` 设置宽度和长文本换行 | 对话布局继续由 `ui_layout_spec.json` 驱动 |
| `time.monotonic()` + 20 Hz `update()` | `lv_timer` 周期 50 ms，或 `lv_anim` 驱动 phase；推荐统一由 UiState/执行层推进 | 周期和关键帧仍由同一 `avatar_anim`/`ANIMATION_FRAMES` 合同提供 |
| `st.color()/font_size()` | 从同一份 JSON 生成 C 令牌表，或编译期生成 `ui_tokens.h` | 不在 LVGL 侧另维护状态→表现映射 |

LVGL v9 推荐层级：右侧 Avatar 容器 → 底图 `lv_image` → 表情 `lv_canvas` 或表情对象组 → 状态 `lv_label`。表情画布可以只覆盖猫脸锚框，不必覆盖整个 568 × 397 区域。

### 2.2 尺寸、内存与性能

题目给定的基准绘制区域为 568 × 397，共 225,496 像素：

| 资源 | 计算 | 解码/运行时内存（约） |
|---|---:|---:|
| JPG 文件 | 取决于压缩质量 | 仅为存储空间，不代表绘制内存 |
| RGB565 底图 | 225,496 × 2 bytes | 450,992 bytes ≈ 440 KiB，约 450 KB（十进制） |
| ARGB8888 底图 | 225,496 × 4 bytes | 901,984 bytes ≈ 881 KiB，约 902 KB（十进制） |
| 全尺寸 RGB565 表情 canvas | 225,496 × 2 bytes | 再增加约 450 KB |
| 猫脸局部 RGB565 canvas（示例 180 × 180） | 32,400 × 2 bytes | 64,800 bytes ≈ 63 KiB |

建议：

1. 设备侧无透明需求时使用 RGB565；JPG 解码到帧缓冲后不再保留第二份同尺寸 ARGB8888 副本。
2. 底图采用 `lv_image`，表情采用约 180–220 px 的局部 canvas；若直接绘制到屏幕/父 canvas，则可以省掉独立表情缓冲。
3. 20 Hz 下，每帧只需绘制两只眼和一个嘴，通常是少量圆、线和贝塞尔近似段；以 20 个基础图元上限计约 400 个图元操作/秒。实际 CPU 占用取决于 MCU、颜色深度和是否需要整画布刷新，不能仅由图元数精确推断。
4. 全尺寸表情画布在 20 Hz 时需要约 4.51 百万 RGB565 像素写入/秒；局部 180 × 180 画布约 0.648 百万像素写入/秒，且更易减少脏区刷新。
5. 如果 20 Hz 在目标板上造成卡顿，可把底图刷新保持静态，仅在表情参数改变时刷新局部 canvas；动画视觉允许时将表情层降到 10 Hz，或把 blink/look/mouth 分成不同刷新频率。

建议配置项（名称随 LVGL 大版本确认）：

```c
/* LVGL v8/v9 的具体宏名以工程采用的 lv_conf.h 模板为准。 */
#define LV_COLOR_DEPTH 16
#define LV_USE_CANVAS 1
#define LV_USE_IMAGE 1       /* LVGL v9；v8 对应 LV_USE_IMG */
#define LV_USE_FS_STDIO 1    /* 仅在设备侧直接读取 JPG/文件系统时需要 */
/* v8 常见：LV_IMG_CACHE_DEF_SIZE；v9 使用对应 image cache 配置名。 */
```

`LV_IMG_CACHE_DEF_SIZE`/v9 对应 image-cache 宏只应缓存实际会重复使用的底图数量；单一 avatar 底图不需要过大的缓存。若使用预生成 C 数组，则可以关闭不必要的文件系统 JPG 解码路径。

### 2.3 M1–M8 一致性核对

| 项 | 迁移后的实现 | 状态 |
|---|---|---|
| M1 9 态→表现映射 | 两端继续调用 `avatar_fsm.AVATAR_MAP` / `avatar_spec()` | 保持复用 |
| M2 表情几何参数 | 两端继续调用 `expression_spec()`；坐标只在后端换算 | 保持复用 |
| M3 UI 状态聚合 | 两端读取同一 `UiState.snapshot()` 数据结构 | 保持复用 |
| M4 数据合同 | 继续使用 `ui_spec/ui_state.schema.json` | 保持复用 |
| M5 动画数据接口 | 继续消费 `UiState.avatar_anim`、`set_avatar_anim()` | 保持复用 |
| M6 动画帧表 | 继续消费 `ANIMATION_FRAMES` / `animation_frames()` | 保持复用 |
| M7 执行层 | 本文 PySide6 用 `_anim_state()` + `_draw_eyes()` + `_draw_mouth()`；LVGL 用等价坐标/图元实现 | 已实现/等价迁移 |
| M8 渲染入口 | `_render_avatar()` 保持入口签名；LVGL 在 avatar 容器更新回调中替代 paintEvent | 已替换占位 |

## 3. 变更摘要与验收建议

### 3.1 文件与函数清单

实际工程接入时建议修改：

- `board/ui/qt_widgets.py`
  - 增加 `os`、`time`、`QImage`、`QBrush`、`QPointF`、`QRectF` 导入。
  - `AvatarPanel.__init__`：增加一次性 `cat_avatar_base.JPG` 加载。
  - `AvatarPanel._render_avatar`：替换占位渲染。
  - `AvatarPanel._anim_state`：完成帧表、周期和 intensity 插值。
  - `AvatarPanel._draw_eyes`：实现眨眼、视线偏移和 expression 几何。
  - `AvatarPanel._draw_mouth`：实现 line/O/上弧/下弧和 mouth 张合。
  - 增加 `_fit_image_rect`、`_sprite_face_rect`、`_clamp`、`_number`、`_cyclic_keyframe_value` 辅助方法。
- `GPT_AVATAR_B2_DELIVERABLE.md`
  - 本交付说明、迁移指南和验收记录；不属于运行时代码。

不修改：`board/ui/avatar_fsm.py`、`board/ui/ui_state.py`、`ui_spec/*.json` 的公开接口和合同版本。

### 3.2 建议测试

接入真实工程后执行：

```text
python -m pytest tests/ -q
python examples/run_ui.py --state IDLE --screenshot evidence_shots/b2_idle.png
python examples/run_ui.py --state PRESENT --screenshot evidence_shots/b2_present.png
python examples/run_ui.py --state LISTENING --screenshot evidence_shots/b2_listening.png
python examples/run_ui.py --state THINKING --screenshot evidence_shots/b2_thinking.png
python examples/run_ui.py --state SPEAKING --screenshot evidence_shots/b2_speaking.png
python examples/run_ui.py --state CAMERA_LOST --screenshot evidence_shots/b2_camera_lost.png
python examples/run_ui.py --state NETWORK_LOST --screenshot evidence_shots/b2_network_lost.png
python examples/run_ui.py --state ERROR --screenshot evidence_shots/b2_error.png
python examples/run_ui.py --demo
python examples/smoke.py
```

建议补充的逻辑断言（无需启动 Qt）：

```python
def test_avatar_anim_disabled_is_static(qtbot, ui_state, avatar_panel):
    ui_state.set_avatar_anim("blink", enabled=False)
    assert avatar_panel._anim_state(123.0) == {
        "blink_close": 0.0,
        "look_dx": 0.0,
        "scale": 1.0,
        "mouth": 0.0,
    }


def test_avatar_anim_uses_period_override(ui_state, avatar_panel):
    ui_state.set_avatar_anim(
        "blink", params={"period_ms": 1000}, enabled=True
    )
    first = avatar_panel._anim_state(0.0)
    peak = avatar_panel._anim_state(1.0 / 3.0)
    assert first["blink_close"] == 0.0
    assert peak["blink_close"] > 0.99


def test_avatar_anim_channels_are_mapped(ui_state, avatar_panel):
    ui_state.set_avatar_anim("speak", enabled=True)
    values = avatar_panel._anim_state(0.0)
    assert values["blink_close"] == 0.0
    assert values["mouth"] == 0.6
```

`qtbot` 仅在工程已有 pytest-qt 时使用；如果依赖约束不允许新增插件，可改为构造最小 `UiState` 和 `AvatarPanel` 测试夹具，或只测试 `_cyclic_keyframe_value`/`_anim_state` 的逻辑。按题目约束，不能为实现 B2 新增第三方运行依赖。

### 3.3 工程侧提交建议

完成源码合入、77 项测试、8 个状态截图、demo 和 smoke 冒烟后，再由工程接入者更新 `docs/ui_consistency_checklist.md` 的 M7/M8 及截图证据行，并按提示词要求提交：

```text
feat: 玩偶渲染方案 B2（sprite 底图 + 程序化表情层）接入 _render_avatar
```
