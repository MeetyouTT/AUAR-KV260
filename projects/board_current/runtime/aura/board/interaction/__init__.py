# -*- coding: utf-8 -*-
"""board.interaction —— 55/45 分屏 UI（人3 / A2）。

结构：
  avatar_fsm.py  状态→表现映射（纯逻辑，LVGL 版复用）
  ui_state.py    UiState 聚合（线程安全，从 EventBus 事件更新）
  qt_widgets.py  PySide6 三个面板（渲染后端，板端换 LVGL 后端）
  qt_app.py      MainWindow + 启动/截图

一致性合同见 ui/：布局/令牌/状态数据三个 JSON 为唯一权威数值。
"""
