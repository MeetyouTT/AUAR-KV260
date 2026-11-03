# -*- coding: utf-8 -*-
"""MainWindow：板端 1024×600「上左右 + 下通栏」三区布局（PySide6 原型）。

三区（数值全部来自 ui/ui_layout_spec.json 1.1）：
  上左 585×556 「交互信息」：摄像头画面 + 信息行 + ASR/回复全文 + 延迟 + 事件流 → CameraPanel
  上右 439×556 「玩偶动画」：状态标签 24 + 玩偶框 423×516 + 底部渐隐收边 28 → AvatarPanel
  下栏 1024×44 「系统信息」：9 项状态 → StatusBar

说明：原 1280×720 顶栏（标题/模式/时间）已随 PC 档废弃一并移除，
模式(mode) 与 fps 改由下栏系统信息条呈现。

支持离屏截图（render_to_file），用于无板阶段 UI 证据。
"""
import time
import typing

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMainWindow, QWidget

from .qt_style import ensure_cjk_font, get_style
from .qt_widgets import AvatarPanel, CameraPanel, StatusBar
from .ui_state import UiState


def _qcolor(hex_str: str):
    from PySide6.QtGui import QColor
    return QColor(hex_str)


class MainWindow(QMainWindow):
    """板端 1024×600 三区主窗口：布局数值全部来自 ui/ui_layout_spec.json。"""

    def __init__(self, ui_state: UiState, parent: typing.Optional[QWidget] = None,
                 event_bus=None) -> None:
        super().__init__(parent)
        self.ui = ui_state
        if event_bus is not None:
            self.ui.bind_event_bus(event_bus)
        self.style = get_style()
        ensure_cjk_font()          # 离屏渲染下注册中文字体（否则中文为方框）
        w, h = self.style.canvas
        self.setFixedSize(w, h)
        self.setWindowTitle("雾镜 Lite · 板端三区 1024×600 原型（PC / SIMULATED）")

        layout = self.style.layout
        self.camera_panel = CameraPanel(ui_state, self)      # 上左：交互信息
        self.avatar_panel = AvatarPanel(ui_state, self)      # 上右：玩偶动画
        self.status_bar = StatusBar(ui_state, self)          # 下栏：系统信息

        # 按布局合同精确放置（三区互不重叠，合计 = 画布）
        lp = layout["left_panel"]
        rp = layout["right_panel"]
        bb = layout["bottom_bar"]
        self.camera_panel.setGeometry(lp["x0"], lp["y0"],
                                      lp["x1"] - lp["x0"], lp["y1"] - lp["y0"])
        self.avatar_panel.setGeometry(rp["x0"], rp["y0"],
                                      rp["x1"] - rp["x0"], rp["y1"] - rp["y0"])
        self.status_bar.setGeometry(bb["x0"], bb["y0"],
                                    bb["x1"] - bb["x0"], bb["y1"] - bb["y0"])

        # FPS 统计
        self._frames = 0
        self._t0 = time.time()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(33)  # ≈30Hz; preserves the 24fps source cadence

    def _refresh(self) -> None:
        self._frames += 1
        now = time.time()
        dt = now - self._t0
        if dt >= 1.0:
            self.ui.set_fps(self._frames / dt)
            self._frames = 0
            self._t0 = now
        self.camera_panel.update()          # 上左：交互信息
        self.avatar_panel.update()          # 上右：玩偶动画（移除自驱动后统一由主窗口刷新）
        self.status_bar.update()            # 下栏：系统信息

    # ------------------------------------------------------------------ #
    def render_to_file(self, path: str) -> None:
        """离屏渲染当前 UI 状态并保存 PNG（无板阶段 UI 证据）。

        强制输出 **= 窗口逻辑尺寸**（1024×600）：`QWidget.grab()` 在高 DPI 屏幕下
        会按 devicePixelRatio 放大（实测 200% 缩放屏拿到 2048×1200），
        证据图必须与合同同尺寸，故此处统一归一化。
        """
        self.show()
        for _ in range(3):
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
        pixmap = self.grab()
        if pixmap.width() != self.width() or pixmap.height() != self.height():
            pixmap = pixmap.scaled(self.width(), self.height(),
                                   Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        ok = pixmap.save(path, "PNG")
        if not ok:
            raise RuntimeError("截图保存失败: %s" % path)
