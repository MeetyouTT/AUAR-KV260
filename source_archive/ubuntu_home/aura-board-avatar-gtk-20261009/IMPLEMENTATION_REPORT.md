# 汐蓝板端 GTK/GStreamer 适配交付

2026-10-09。接用户“怎么做”，完成原生播放器适配、原资源回收、中文字体及独立运行包；将小包写入板卡独立目录并执行不发声原生检查。完整素材包未部署，真实玩偶窗口/MCP01 播放未验收。

## 完成内容

主仓为 `/home/ghmd/Win共享文件/共享文件夹/aura`。

- 新增 `tools/board_avatar_gtk.py`、`config/board_avatar_gtk.json`：读取现有 1024×600 布局/底色合同，复用原 FSM、三档五套口型、眨眼与四段声线缓存；提供暂停/恢复、打断、重置、保存，独立输出运行证据。
- 新增 `tools/gstreamer_audio.py`、`gstreamer_audio_engine.py`、`gstreamer_audio_worker.py`：独立音频进程，校验原缓存后转换 48 kHz/双声道/S16LE，明确 MCP01；sink position 控制口型时间，暂停冻结，旧代次拒绝，取消释放本进程管线，设备错误/启动超时明确上报。
- 新增 `tools/pillow_compat.py`，修改 `tools/facial_layers.py` 与相邻 `deliverables/2026-10-06_avatar_reuse/preview_script.py` 的常量使用，兼容 Pillow 8.3.2。`tools/realtime_audio.py` 仅扩展可选 worker 路径/参数，默认 PC Qt worker 入口保留。
- 新增 `tools/check_gstreamer_clock.py`、`tests/framework/test_gstreamer_audio.py`：测试真实原生转换/时钟管线及失败/取消/暂停/代次行为；原生检查使用 fakesink，绝不打开音频设备。
- 新增 `tools/package_board_avatar.py`、`assets/fonts/`，携带原 Droid 字体、指纹、版权与许可；新增 `docs/BOARD_AVATAR_GTK.md`，更新 README/当前安排/框架状态。
- 独立 Ubuntu 工作目录保留原 6 份可修改文件字节/SHA 备份。没有改原 PNG、WAV、参考转写或已选声线身份。

## 实际验证

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| `unittest discover -s tests/framework -v` | **58 项通过**，0 failures/errors/skips | `software_validation.json`，原 48 + 音频 10 |
| 原资源只读核验 | **16 套/573 帧、4 段 WAV、42 张眨眼层通过** | `resource_validation.json` |
| Ubuntu 原生管线 | GStreamer 1.16.3 转换、pause/resume/cancel、旧代次与 EOS 通过 | `ubuntu_native_validation.json`；fakesink，无发声 |
| KV260 原生管线 | GStreamer 1.18.5 同项通过，48 kHz 双声道；fixture 输出 191996 字节 | `board_native_validation.json`；fakesink，无发声 |
| KV260 生命周期测试 | **10 项通过** | 板端 `lifecycle-tests.output` |
| KV260 图形/旧 Pillow | Gtk 连接 `:0`、旧常量和变换通过 | `gtk-pillow.output`；没有创建窗口 |
| 小包/串口 | 9 载荷、31 响应逐项 SHA/大小通过，console echo 恢复 | `evidence/20261009T112018.737176Z-native-probe/` |
| 源码/配置/文档 | 10 Python AST、新配置 JSON 和 6 个新说明链接通过 | 本地检查输出；源模板保持旧常量数值 |
| 完整运行包 | **871 载荷＋清单逐项大小/SHA 回读通过** | 下方包及相邻 `.verification.json` |

board 小包目录：

```text
/home/root/aura-avatar-gtk-stage/native-probe-c9a53bcb97d3acda
```

完整缓存运行包：

```text
/home/ghmd/Win共享文件/共享文件夹/aura/artifacts/releases/aura-board-avatar-gtk-runtime-20261009T112752Z-57fc8c.zip
```

- 大小：**217023529 字节（约 207 MiB）**。
- SHA256：`1a8677ce385516b406344f5e22acfed72e1fd9ab1ffe79aa745760e1137917de`。
- 范围为玩偶显示/缓存播放子系统，包含实际依赖源码、原 PNG/SOP、五套口型来源/眨眼、四段 WAV 与声线参考身份、中文字体及许可。不携带 GPU 模型和 FPGA 固件；需要目标镜像的现有原生库及实屏/设备验收。
- 小包为 `aura-board-avatar-gtk-native-probe-20261009T111150Z-bf9367.zip`，18646 字节，SHA256 `c9a53bcb97d3acda2243036bfb7e911a2363c3bb02ca41d3ad7d1f57076c71de`。它仅含兼容性测试所需 9 源文件，不是完整玩偶运行包。

## 尚未验证与下一步

当前没有创建正式玩偶窗口或播放 MCP01，没有测口型声学对齐/中文字体实屏/最终帧率/内存预算/与视觉并行性能；无声 fixture 管线通过不等于真实设备发声通过。源码默认 33 ms 调度及三序列缓存是设定，总内存与实际帧率须测量。

已通过异步文本询问是否能接网线，记录时没有收到答案。最新环境证据仍为 eth0 DOWN / 无板卡 IP，不能把等待时间当作连接已就绪。正式部署需要可用有线网络或拷贝介质；完整包较大，未通过 UART 传输完整动画。

部署到新的独立目录、校验 ZIP SHA 并展开后，保持 aura/deliverables 相邻。在实际板端 `aura/` 中执行：

```bash
DISPLAY=:0 python3 -B tools/board_avatar_gtk.py --check
DISPLAY=:0 python3 -B tools/board_avatar_gtk.py
```

之后逐项验收待机/眨眼→四段回应→暂停恢复→打断停声/收口→保存实屏；再和 A 的视觉/FPGA 并行测响应。机构继续等待 3D 模型。本轮没有安装镜像依赖、改网络或显示模式/音量、访问相机、停止 A 的程序、加载 FPGA 或驱动舵机。

详细操作见 [板端入口说明](/home/ghmd/Win共享文件/共享文件夹/aura/docs/BOARD_AVATAR_GTK.md)，证据见 [板端原生核验](/home/ghmd/aura-board-avatar-gtk-20261009/board_native_validation.json)。
