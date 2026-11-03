# 雾镜 Lite 玩偶方案 B2V 交付物

本文档依据 `GPT_PROMPT_AVATAR_B2V.md` §2–§5 生成。附件图中的可见构成是：深蓝色双耳猫头、白色脸部填充、固定蓝色鼻子，以及下方 `CATLY / SIMPLE DESIGN CO.` 字标。B2V 将主体改为 `QPainterPath`/`QPainter` 矢量绘制；眼睛和嘴巴仍由程序化表情层绘制，因此可以继续响应方案 C 动画和 `AvatarSpec.token_key` 状态色。

当前工作区没有 `wujing-lite` 工程源码，以下内容是按提示词要求生成的可直接合入附件。工程侧的 84 项测试、9 态截图、demo 和 smoke 尚未在本工作区执行。

## 1. PySide6 成品代码

### 1.1 导入与初始化删除项

B2V 不再读取任何位图。删除 `qt_widgets.py` 中以下内容：

- `__init__` 中的 `_avatar_base_path` 和 `_avatar_base` 初始化块；
- `_fit_image_rect`；
- `_sprite_face_rect`；
- `QImage` 导入；
- 如果 `os` 在该文件其他位置没有用途，也一并删除 `os` 导入。

`QPointF`、`QRectF`、`QBrush` 和 `QPainterPath` 保留。题目给出的当前导入区已经包含这些符号；不需要新增第三方依赖。

### 1.2 `AvatarPanel` 可直接替换的方法

下面代码保持 `paintEvent` 调用 `_render_avatar(p, avatar_rect, st, snap)` 不变，也不修改 `avatar_fsm.py`、`ui_state.py` 或 `ui_spec/*.json`。

```python
    # ------------------------------------------------------------------ #
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
        p.save()
        p.setPen(state_color)
        p.setFont(QFont("Microsoft YaHei", st.font_size("label"), QFont.Bold))
        p.drawText(
            QRect(rect.x(), rect.y() + 4, rect.width(), 24),
            Qt.AlignCenter,
            "%s [%s]" % (spec.label, state),
        )
        p.restore()

        # 只在标签下方绘制矢量内容；不再计算或读取任何图片矩形。
        body_rect = QRectF(rect).adjusted(8.0, 30.0, -8.0, -8.0)
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

    def _anim_state(self, t: float) -> typing.Dict:
        """方案 C 执行层：UiState + 帧表 → 当前动画值。"""
        snapshot = self.ui.snapshot()
        anim = snapshot.get("avatar_anim", {})
        if not anim.get("enabled"):
            return {
                "blink_close": 0.0,
                "look_dx": 0.0,
                "scale": 1.0,
                "mouth": 0.0,
            }

        state = snapshot.get("runtime_state", "IDLE")
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

        intensity = self._clamp(
            self._number(params.get("intensity", 1.0), 1.0),
            0.0,
            1.0,
        )
        values["blink_close"] *= intensity
        values["look_dx"] *= intensity
        values["mouth"] *= intensity
        values["scale"] = 1.0 + (values["scale"] - 1.0) * intensity
        return values

    def _draw_eyes(self, p: QPainter, face_rect: QRectF,
                   expression: typing.Dict, blink_close: float,
                   look_dx: float, color: QColor) -> None:
        """绘制程序化眼睛；位置和半径来自 expression_spec。"""
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
                    x - eye_r * 0.40,
                    center_y + gaze_y + eye_r * 0.22,
                    x + eye_r * 0.40,
                    center_y + gaze_y + eye_r * 0.22,
                    x + eye_r,
                    center_y + gaze_y,
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
        """按 expression_spec 的 mouth 标识绘制 line/o/上弧/下弧。"""
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
            center_offset = -amplitude if mouth_kind == "arc_down" else amplitude
            path = QPainterPath()
            path.moveTo(left_x, center.y())
            path.cubicTo(
                center.x() - half_width * 0.58,
                center.y() + center_offset,
                center.x() + half_width * 0.58,
                center.y() + center_offset,
                right_x,
                center.y(),
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

### 1.3 B2V 几何说明

- 所有 `pt(x, y)` 坐标都是相对于 `body_rect` 的 0–1 归一化坐标，窗口缩放不会改变猫头比例。
- 双耳和头脸外轮廓使用圆头/圆角画笔与 `QPainterPath.cubicTo`，脸颊由头部下侧连续曲线表现。
- 附件参考图没有可辨识的额外条纹或独立胡须线条；为保持严格描摹，不添加参考图中不存在的装饰。若后续设计稿加入胡须，应在 `_draw_sprite_base` 同一蓝色路径中增加，并同步扩大 `_face_anchor` 的验证范围。
- `CATLY` 和副标题使用 QPainter 文本绘制，不依赖位图；如板端需要像素级字形一致，可将同一字体转成 LVGL 字体资源，仍不改变状态/动画接口。
- `_face_anchor` 与头部路径共享 `x=0.36..0.64、y=0.28..0.68` 的脸部几何区间，眼睛/嘴巴不再从 JPG 像素反推。

## 2. LVGL 迁移指南与技术总结

### 2.1 PySide6 → LVGL 映射表

| PySide6 B2V | LVGL 等价实现 | 迁移要点 |
|---|---|---|
| `QPainterPath.moveTo/lineTo/cubicTo/closeSubpath` | `lv_canvas` 上的线段、圆、填充；贝塞尔曲线用固定采样点 polyline 近似，或预渲染为 RGB565 sprite 后用 LVGL v9 `lv_image`（v8 `lv_img`）显示 | 使用同一归一化控制点和相同蓝色/脸填充色；贝塞尔采样 8–16 段已足够覆盖 568×397 区域 |
| 双耳、头脸填充 | `lv_canvas` 的 path/line 绘制，或一次性绘入静态主体 canvas | 主体没有动态颜色，不必每 50 ms 重绘 |
| 鼻子 `QPainterPath` | `lv_canvas` 填充 path/小三角或小椭圆组合 | 固定在 `_face_anchor` 的同一相对位置 |
| `CATLY / SIMPLE DESIGN CO.` `drawText` | `lv_label` + 相同字体资源；若需轮廓级缩放则转成预生成字体/路径 | 文本不是状态文字，不参与 FSM；字号和位置仍使用同一比例 |
| `_draw_eyes` / `_draw_mouth` | 局部 `lv_canvas`，或多个圆/线/弧 `lv_obj` 组合 | 眼睛闭合、视线偏移、嘴型和颜色由同一 expression 参数驱动 |
| `p.scale` 围绕 `face_center` | 绘制前对局部坐标做 `scale` 变换，或调整表情对象组尺寸 | 底图不缩放，表情层围绕 `_face_anchor(rect).center()` 缩放 |
| 状态标签 `drawText` | `lv_label` | 内容继续是 `spec.label + " [" + runtime_state + "]"`，颜色取 `spec.token_key` |
| `time.monotonic()` + 20 Hz refresh | `lv_timer` 50 ms，或由 `lv_anim` 推进 phase | `period_ms` 优先级和 `ANIMATION_FRAMES` 不能在 LVGL 侧另写一套 |
| `panel_bg`、边框、字号、颜色 token | 由 `ui_tokens.json` 生成的 C 常量/表 | 只转换数据格式，不改变合同版本 |

建议的板端层级为：Avatar 容器 → 静态主体 canvas/`lv_image` → 局部表情 canvas/对象组 → 状态 `lv_label`。主体静态时只在进入 avatar 区域或窗口尺寸变化时绘制一次；20 Hz 仅刷新表情局部脏区。

### 2.2 内存评估

568 × 397 = 225,496 像素。

| 方案 | 计算 | 运行时内存 |
|---|---:|---:|
| B2 RGB565 位图底图 | 225,496 × 2 bytes | 450,992 bytes ≈ 440 KiB，约 450 KB |
| B2 ARGB8888 位图底图 | 225,496 × 4 bytes | 901,984 bytes ≈ 881 KiB，约 902 KB |
| B2V 纯矢量主体 | 路径/常量/字体代码，不保存全尺寸位图 | 全尺寸主体帧缓冲 0 KB；直接绘制时只需要目标显示缓冲 |
| B2V 局部表情 canvas（180 × 180，RGB565） | 32,400 × 2 bytes | 64,800 bytes ≈ 63 KiB |

“纯矢量 0 KB”指不再保存全尺寸底图帧缓冲；显示控制器本身仍有 LVGL draw buffer。若主体也缓存到 canvas，则需另外计入 canvas 大小，但可选择仅在初始化时渲染一次。若字体使用外部字库，还需另计字库内存。

### 2.3 性能评估与优化

- 每帧主体约包含 2 个耳朵 path、1 个头脸 cubic path、1 个鼻子 path 和 2 次字标绘制；表情层最多是 2 个眼睛图元、2 个闭眼 path、1 个嘴 path 及 1 个张嘴椭圆，属于低数量矢量操作。
- 20 Hz 上限约为 400 个基础图元操作/秒（按每帧 20 个保守上限估算）；实际 CPU 占用依赖 FMQL30TAI 的显示缓冲、颜色深度、贝塞尔采样数和是否整屏刷新，不能仅由图元数量精确推出。
- 全尺寸 568 × 397 RGB565 画布每秒约需写入 4.51 百万像素；180 × 180 局部表情画布每秒约 0.648 百万像素。局部 canvas/脏区刷新通常是最有效的优化。
- 主体路径可在尺寸不变时缓存，主体 canvas 只在进入场景或 resize 时重绘；动画只清理并刷新 `_face_anchor` 外扩少量边距的局部区域。
- 若无硬件加速导致 20 Hz 卡顿，可把表情层降为 10 Hz、分离 blink/look/mouth 更新频率，或预渲染几帧主体 RGB565 sprite；逻辑层和状态合同仍保持不变。

建议配置（宏名随 LVGL 大版本使用对应模板确认）：

```c
#define LV_COLOR_DEPTH 16
#define LV_USE_CANVAS 1
#define LV_USE_IMAGE 1       /* LVGL v9；v8 使用 LV_USE_IMG */
/* 直接从文件读取 JPG 时才需要启用对应文件系统/decoder。B2V 主体不需要 JPG decoder。 */
/* v8 常见：LV_IMG_CACHE_DEF_SIZE；v9 使用对应 image cache 配置名。 */
```

由于 B2V 不依赖 JPG，`LV_IMG_CACHE_DEF_SIZE`/v9 对应 image-cache 配置可设为 0 或仅缓存其他业务图片；若选择预渲染 RGB565 sprite，则按照实际 sprite 数量配置缓存。

## 3. M1–M8 一致性核对

| 项 | B2V / LVGL 实现 | 状态 |
|---|---|---|
| M1 9 态→表现映射 | 继续复用 `avatar_fsm.AVATAR_MAP` / `avatar_spec()` | 复用 |
| M2 表情几何参数 | 继续复用 `expression_spec()`；后端仅负责归一化坐标换算 | 复用 |
| M3 UI 状态聚合 | 继续读取 `UiState.snapshot()` | 复用 |
| M4 数据合同 | 不改 `ui_spec/ui_state.schema.json` 与合同版本 | 复用 |
| M5 动画数据接口 | 继续消费 `UiState.avatar_anim` / `set_avatar_anim()` | 复用 |
| M6 动画帧表 | 继续消费 `ANIMATION_FRAMES` / `animation_frames()` | 复用 |
| M7 执行层 | `_anim_state`、`_draw_eyes`、`_draw_mouth` 保持；表情锚框改用 `_face_anchor` | B2V 保留并改进 |
| M8 渲染入口 | `_render_avatar` 签名不变；B2 底图段替换为 `_draw_sprite_base` | B2V 完成 |

## 4. 变更摘要与验收建议

### 4.1 文件/函数清单

实际工程接入时只需修改：

- `board/ui/qt_widgets.py`
  - 删除 `QImage` 导入；若无其他用途，删除 `os` 导入。
  - 从 `AvatarPanel.__init__` 删除 `_avatar_base_path` / `_avatar_base` 位图加载。
  - 删除 `_fit_image_rect`、`_sprite_face_rect`。
  - 新增 `_face_anchor`。
  - 新增 `_draw_sprite_base`。
  - 更新 `_render_avatar`，改为调用矢量主体和 `_face_anchor`。
  - 保留 `_anim_state`、`_draw_eyes`、`_draw_mouth`、`_clamp`、`_number`、`_cyclic_keyframe_value`。
- 不修改 `board/ui/avatar_fsm.py`、`board/ui/ui_state.py`、`ui_spec/*.json`。

### 4.2 建议新增测试

```python
def test_face_anchor_is_normalized_and_inside_body(avatar_panel):
    rect = QRectF(0.0, 0.0, 552.0, 359.0)
    anchor = avatar_panel._face_anchor(rect)
    assert 0.0 < anchor.left() < anchor.right() < rect.right()
    assert 0.0 < anchor.top() < anchor.bottom() < rect.bottom()
    assert anchor.width() == pytest.approx(rect.width() * 0.28)
    assert anchor.height() == pytest.approx(rect.height() * 0.40)


def test_b2v_render_uses_vector_base(monkeypatch, avatar_panel, painter, style):
    called = []
    monkeypatch.setattr(
        avatar_panel,
        "_draw_sprite_base",
        lambda p, rect, st, spec: called.append(rect),
    )
    avatar_panel._render_avatar(
        painter,
        QRect(0, 0, 568, 397),
        style,
        {"runtime_state": "IDLE", "avatar_anim": {"enabled": False}},
    )
    assert len(called) == 1
    assert not hasattr(avatar_panel, "_avatar_base")
```

若测试夹具无法直接构造 `QPainter`，可只测试 `_face_anchor` 和 `_draw_sprite_base` 的调用桩；现有 B2 的 `_anim_state` / `_cyclic_keyframe_value` 七项测试应保持通过。`pytest.approx` 使用已有 pytest，不引入运行时第三方依赖。

### 4.3 工程验收命令

```text
python -m pytest tests/ -q                 # 目标：84 passed
python examples/run_ui.py --state IDLE --screenshot evidence_shots/b2v_idle.png
python examples/run_ui.py --state PRESENT --screenshot evidence_shots/b2v_present.png
python examples/run_ui.py --state LISTENING --screenshot evidence_shots/b2v_listening.png
python examples/run_ui.py --state THINKING --screenshot evidence_shots/b2v_thinking.png
python examples/run_ui.py --state SPEAKING --screenshot evidence_shots/b2v_speaking.png
python examples/run_ui.py --state CAMERA_LOST --screenshot evidence_shots/b2v_camera_lost.png
python examples/run_ui.py --state NETWORK_LOST --screenshot evidence_shots/b2v_network_lost.png
python examples/run_ui.py --state ERROR --screenshot evidence_shots/b2v_error.png
python examples/run_ui.py --state CANCELLED --screenshot evidence_shots/b2v_cancelled.png
python examples/run_ui.py --demo
python examples/smoke.py
```

最终提交信息按提示词使用：

```text
refactor: 玩偶渲染 B2V（QPainterPath 矢量底图替代位图，_face_anchor 精确锚框）
```

工程接入者还需更新 `docs/ui_consistency_checklist.md` 的 M8 与截图证据行，以及 `docs/NEW_WINDOW_PROMPT.md` 进度表。
