# -*- coding: utf-8 -*-
"""UI 样式加载器：从 ui/ 读取一致性合同（布局/令牌），供渲染后端使用。

PySide6 原型与板端 LVGL 版都从这里读取同一份数值，保证布局/配色一致。
合同版本：ui_layout_spec.json **1.1**（板端 1024×600 · 上左右 + 下通栏三区）、
ui_tokens.json **1.1**（板端字号档）。PC 1280×720 档已废弃。
"""
import json
import os
import typing

_SPEC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "ui")


class UiStyle:
    def __init__(self, spec_dir: typing.Optional[str] = None) -> None:
        d = os.path.normpath(spec_dir or _SPEC_DIR)
        with open(os.path.join(d, "ui_layout_spec.json"), encoding="utf-8") as f:
            self.layout = json.load(f)
        with open(os.path.join(d, "ui_tokens.json"), encoding="utf-8") as f:
            self.tokens = json.load(f)

    # ---- 布局 ----
    @property
    def canvas(self) -> typing.Tuple[int, int]:
        c = self.layout["canvas"]
        return c["width"], c["height"]

    def rect(self, key: str) -> typing.Tuple[int, int, int, int]:
        """返回 (x, y, w, h)。key 为 layout 中的区域名（left_panel/right_panel/bottom_bar）。"""
        r = self.layout[key]
        return r["x0"], r["y0"], r["x1"] - r["x0"], r["y1"] - r["y0"]

    def area(self, key: str) -> typing.Dict:
        """直接取 layout 中的区块字典（如 left_inner / right_inner / framing）。"""
        return dict(self.layout.get(key) or {})

    # ---- 颜色 ----
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


# --------------------------------------------------------------------------- #
# 中文渲染保障（离屏 / 无字体环境）
# --------------------------------------------------------------------------- #
# 症状：`QT_QPA_PLATFORM=offscreen` 时 Qt 不会加载系统字体，
# 中文（含界面里所有中文标签）会渲染成 **方框** —— 证据截图直接不可用。
# 处置：显式注册 Windows 自带的微软雅黑（缺失则退黑体），只做一次。
_CJK_FONT_CANDIDATES: typing.Tuple[str, ...] = (
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
)
_cjk_font_path: typing.Optional[str] = None
_cjk_font_checked = False


def ensure_cjk_font() -> typing.Optional[str]:
    """注册中文字体（幂等）。返回字体文件路径；找不到可用字体时返回 None。"""
    global _cjk_font_path, _cjk_font_checked
    if _cjk_font_checked:
        return _cjk_font_path
    _cjk_font_checked = True
    try:
        from PySide6.QtGui import QFontDatabase
    except ImportError:                      # 无 Qt 环境（纯逻辑单测）直接跳过
        return None
    for path in _CJK_FONT_CANDIDATES:
        if os.path.isfile(path):
            if QFontDatabase.addApplicationFont(path) >= 0:
                _cjk_font_path = path
                return _cjk_font_path
    return None
