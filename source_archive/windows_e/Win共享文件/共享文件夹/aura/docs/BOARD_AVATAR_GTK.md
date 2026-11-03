# 汐蓝 GTK3/GStreamer 板端缓存播放器

2026-10-11 更新：原素材、声线和播放器继续使用，操作已扩展为 [五页触屏界面](BOARD_TOUCH_UI_DESIGN.md)，并接入 [真实相机预览](BOARD_CAMERA_UI.md)。人物渲染移到单一后台所有者，视频独立显示，诊断后台保存。新版本已在相机运行时通过缓存音频播放、暂停/继续和取消，原生操作回执为 88～141ms；这不是新的 TTS 或真实麦克风验证。当前版本和证据见 [本轮报告](/home/ghmd/aura-board-ui-design-20261009/UI_DESIGN_REPORT.md)。以下 10 月 9 日内容保留追溯；启动状态以 [最新说明](BOARD_UI_STARTUP.md) 为准。

更新：2026-10-09。目标为 KV260 PS/Linux 的 1024×600 显示与 MCP01 播放；A 继续负责视觉和 FPGA，机构等待 3D 模型。

最新：[独立界面开机服务](BOARD_UI_STARTUP.md) 已安装启用并完成真实启动、快速服务重启与设置恢复，最终音量 18%。整板正常重启/冷启动尚未验收；下段的“GUI 自启待完成”为此前状态。

同日后续已通过 U 盘安装完整素材，真实中文窗口、MCP01 四段播放/暂停/恢复/打断通过；用户反馈声音偏小后曾按要求将 PCM 从 29% 调到 100%。现已增加 [图形操作与设置页](BOARD_UI_SETTINGS.md)，支持音量滑块/加减、静音、全屏、省电和持久化。70 项主机、12 项板端设置测试及指针检查通过。最新已识别微雪 `WS170120`，真实手指音量滑块与页签切换通过；最终保存音量为 18%，驱动开机加载已配置。新配置重启验收、GUI 自启、触摸边缘/多指及流畅度优化仍待完成。下方“未部署/未播放”段落为适配完成时的历史状态，由本段更新。

## 当前交付

- 入口 `tools/board_avatar_gtk.py`：GTK3 窗口、四段已缓存台词、暂停/恢复、打断、重置、记录保存；沿用现有 FSM、素材池、眨眼和音强口型。画布、右侧玩偶框、contain/底部对齐及底色读取原 `ui_layout_spec.json` / `ui_tokens.json`，不重新生成素材。
- `tools/gstreamer_audio*.py`：音频独立进程，明确使用 `hw:CARD=MCP01,DEV=0`；WAV 校验后经格式/采样转换输出 48 kHz 双声道 S16LE。口型取 ALSA sink 的 GStreamer position，暂停冻结、取消释放当前管线、旧代次命令丢弃。查询的精度和声学延迟仍须真实设备测量。
- `tools/pillow_compat.py`：原口型复用和眨眼 warp 兼容板端 Pillow 8.3.2；现有 PC Qt 音频入口保留默认 worker，新增参数只供 GTK 指定独立后端。
- `assets/fonts/`：携带 Droid Sans Fallback 中文字体、来源指纹、版权和 Apache 2.0 许可文件。只注册到播放器进程的 Fontconfig，不安装系统字体。
- `tools/package_board_avatar.py`：完整缓存运行包，或供板端原生库/时钟检查的小包。每个载荷带大小和 SHA256，打包后回读核对。

首轮界面左侧提供缓存播放控制，右侧显示原玩偶。正式视频、身份、麦克风、Windows 动态回答及系统信息仍按框架接入；本入口的左侧控制页是本地播放验收入口。

## 已验证

工作目录：`/home/ghmd/aura-board-avatar-gtk-20261009`。

| 验证 | 实际结果 | 范围 |
| --- | --- | --- |
| 主机标准库测试 | **58 项通过**：原 48 + 新音频生命周期 10 | 缓存、代次、取消、设备失败、暂停和时钟逻辑；不等于真实音频 |
| 原素材/音频/眨眼 | **16 套/573 帧、4 段选定 WAV、42 张眨眼层核验通过** | 原清单 SHA、身份、格式与时长保持一致 |
| Ubuntu GStreamer 1.16.3 | 原生转换/暂停/恢复/取消/EOS 检查通过 | fakesink，无设备发声；1 秒 fixture 转换输出 191996 字节，48 kHz 双声道 |
| KV260 GStreamer 1.18.5 | 同一原生检查通过，10 项生命周期测试通过 | 独立小包实际上板；fakesink，无音频设备打开 |
| KV260 GTK/Pillow | Gtk 可连接 `:0`；Pillow 8.3.2 兼容常量与变换通过 | 未创建玩偶窗口或播放声音 |
| 小包/UART | 9 个载荷，31 份命令响应的大小/SHA 完整性通过，回显恢复 | 小包目录为 `/home/root/aura-avatar-gtk-stage/native-probe-c9a53bcb97d3acda` |

准确证据为工作目录 `software_validation.json`、`resource_validation.json`、`ubuntu_native_validation.json`、`board_native_validation.json` 与 `evidence/20261009T112018.737176Z-native-probe/`。原文件备份为 `previous/`、`source_before.json`。

适配初次完成时只有原生检查小包；后续完整包已部署，并完成真实窗口、播放控制与基础手指触控检查。中文和玩偶截图已核对。前次曾与视觉并行运行，本轮外部重启后未发现视觉进程；口型观感、触摸边缘/多指、长期并行性能与整机验收仍须继续验证。

## 完整包与部署

在 Ubuntu 主仓生成完整包：

```bash
python3 -B tools/package_board_avatar.py --profile runtime
```

输出在 `artifacts/releases/aura-board-avatar-gtk-runtime-<时间>-<编号>.zip`，对应 `.verification.json` 记录真实包大小/SHA和逐项回读结果。包的范围为有声玩偶子系统，包含源码、原正式 PNG/SOP、口型候选、眨眼层、四段 WAV及身份/参考、中文字体和许可；没有模型权重或板卡固件。`native-probe` 包仅供原生兼容性检查。

将完整 ZIP 放入板上**独立的新目录**并核对包 SHA，再展开；展开后目录必须保持相邻：

```text
本次运行目录/
├── runtime_manifest.json
├── aura/
│   ├── tools/board_avatar_gtk.py
│   ├── config/board_avatar_gtk.json
│   ├── assets/avatar/
│   ├── assets/fonts/
│   └── ui/
└── deliverables/
    ├── 2026-10-06_avatar_reuse/
    ├── 2026-10-06_voice_blink/
    ├── 2026-10-06_voice_selected_soft_young/
    └── 2026-10-06_xilan_live/
```

当前板端 `eth0` 已启用但无载波和可用 IP；完整包已用 U 盘部署，871 个原载荷大小/SHA 回读通过。之后旧 Pillow 两处调用、GTK 重绘调度及设置页更新分别保留旧源和明确补丁 SHA。U 盘已在板端安全卸载，运行文件保存在板卡存储。

在板端包的 `aura/` 中，先做资源与库检查：

```bash
DISPLAY=:0 python3 -B tools/board_avatar_gtk.py --check
```

然后启动真实播放器：

```bash
DISPLAY=:0 python3 -B tools/board_avatar_gtk.py
```

默认全屏，Esc 关闭、空格暂停/恢复。输出设备读取 `config/board_avatar_gtk.json`；MCP01 不可用或被占用时明确报错，由本次播放进程处理自己的管线。没有切换显示模式、改系统音量或控制其他进程的入口。

首轮按待机/眨眼 → 问候 → 开心点头 → 安慰 → 长句 → 暂停恢复 → 说话中打断的顺序验收。确认真实声音立即停止、旧声音不恢复、嘴部收起、最后回待机；保存记录并留实屏照片/录像。窗口按 33 ms 调度是目标间隔，不能当成实测 30 fps。

运行证据另存到相邻 `deliverables/board_avatar_runs/gtk_<唯一编号>/`，含源指纹、帧间隔、口型/眨眼/声音状态和截图；保留 Windows 原验证记录。环回控制为 `http://127.0.0.1:8783`，GTK 入口仅接收已选台词、暂停、取消/重置和保存，不调用新模型。

单项真实验收通过后，再与 A 的视觉/FPGA版本并行记录 CPU、内存、帧间隔、停声和响应，最后接 Windows 动态媒体服务。

实现依据：[GStreamer position 查询](https://gstreamer.freedesktop.org/documentation/gstreamer/gstelement.html)、[ALSA sink 设备选择](https://gstreamer.freedesktop.org/documentation/alsa/alsasink.html)、[时钟同步](https://gstreamer.freedesktop.org/documentation/application-development/advanced/clocks.html)。官方 API 用于实现依据，当前镜像适配以本次实测为准。
