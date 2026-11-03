# 双层界面首版审阅

双击打开 `index.html`，用截图上方的按钮切换玩偶交流、视觉追踪和调试层。图片本身是实际主机 GTK 截图，图片内按钮不响应操作。

`main.png` / `vision.png` 是两个主页面；`presentation_settings.png` 是从视觉页进入的设置；`debug_*.png` 是调试页；`offline_*.png` 是断连状态。

这些PNG保留上板前主机预览：照片、文本、人数、目标与叠加框为示例。后续已按用户授权上板，当前真实截图见 `board/main.jpg`、`board/vision.jpg`、`board/debug.jpg`；真实相机、原生点击与录音复验通过，实物手指和Windows问答仍待验收。

需要实际交互预览时，在有 GTK3、Pillow 和图形桌面的 Linux 项目根目录运行：

```sh
python3 tools/preview_board_touch.py
```

这个入口不启动设备、模型或网络服务；除导航和放大外只提示预览状态。真实运行入口仍为 `tools/board_avatar_gtk.py`。
