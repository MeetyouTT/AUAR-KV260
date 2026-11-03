# 汐蓝板端缓存播放准备

用户在确认玩偶部署到板卡、A 负责视觉及 FPGA 后询问“那现在做什么”。本轮推进可与 A 并行的缓存有声玩偶基线，完成本地入口、资源预检与软件验证。工作目录：`/home/ghmd/aura-board-avatar-baseline-20261009`。没有执行板端播放。

## 依据与连接检查

先读 ZIP README、当前执行分工、最新日志、原播放器/声线/移机交接。采用现有素材、声线和播放逻辑，未生成新图像/声线，机构仍等 3D 模型。

当前未检测 `/dev/serial/by-id`、ttyUSB 或 ttyACM。沙箱内 `ip -brief address` 被 netlink 权限拒绝，按规则在沙箱外只读重试成功；只有 Wi-Fi、回环与未启用 Docker 接口。没有获知 KV260 IP。已通过异步输入询问板卡是否连接、网络地址或是否由 A 使用；记录时未收到答案。没有探测局域网其他设备或尝试未知 SSH 地址。

## 实际实现

- `tools/selected_voice_service.py` 增加显式 `cached_only`。缓存命中走现有校验，缺失/损坏/格式或身份不匹配时失败，不创建 GPU 子进程；默认模式不变。PCM/口型分析依赖延迟加载，线程池关闭兼容本地 Python 3.8。
- `tools/realtime_stage.py` 增加 `--cached-only`、`--cache-sequences`、`--evidence-root`。缓存模式关闭对话，正式序列缓存默认 3，运行日志另建独立目录，不覆盖 Windows 原验证记录。它仍复用原 Qt 演示布局，未验收最终 1024×600 界面或总内存。
- 首次标准库检查暴露 `audio/__init__.py` 提前加载 ASR/NumPy，导致只读缓存检查也失败；已改为按需导出，保留原 36 个名称。VAD 本身也依赖 NumPy，未把它改写为零依赖；兼容测试实际调用无 NumPy 的 TtsStyle。
- 新增只读资源/环境检查 `tools/board_avatar_preflight.py`、独立关闭对话的 `config/board_avatar_baseline.json`、7 项缓存限制/接口兼容测试和 [板端基线说明](/home/ghmd/Win共享文件/共享文件夹/aura/docs/BOARD_AVATAR_BASELINE.md)。更新主入口、当前安排与框架状态。
- 三个原源码文件原始字节和 SHA 保存在工作目录 `previous/`、`source_before.json`；未修改原 stage 配置、缓存 WAV、参考录音、素材或 A 的平台工程。

## 实际验证

- 最终 `unittest discover -s tests/framework` 为 **48 项通过**、0 errors/failures/skips，即原 41 + 新 7；结果为工作目录 `unittest_validation.json` 和 `unittest_output.txt`。首次依赖导入失败和一次测试误把 VAD 当成零依赖已定位并修正，最终检查不依赖 NumPy/PySide6。
- 资源只读检查 **PASS**：原清单中的 **16 套/573 帧 PNG** 大小/SHA 一致，4 段演示 WAV 的选定身份、SHA、24 kHz/单声道/16 bit 及真实时长一致，42 张眨眼图层与 anchor 指纹一致。记录 `resource_validation.json`。五套嘴部动态合成与实际绘制未执行。
- 当前 Ubuntu x86_64/Python 3.8.10，有 Pillow，缺 NumPy/PySide6/QtMultimedia；环境检查按预期 **NOT_READY**、退出码 2。记录 `ubuntu_environment.json`；这是主机结果，不替代板端镜像检查。
- 源码 AST、JSON、新说明链接、36 个原导出名称与不提前导入 ASR/KWS/TTS 的检查通过。源码补丁包 10 个载荷文件与清单逐项 SHA/字节回读通过，实际路径/大小/哈希见工作目录 `package_validation.json`；它不含完整素材和相邻交付资源，不能作为独立运行发行包。

## 验证边界与下一步

没有启动 Qt 窗口、安装依赖、播放声音、连接板卡、访问相机、改写 FPGA 或驱动舵机；没有复跑原 Windows 547/550 项 GUI/素材回归。新增缓存限制的标准库证据不等于真实 UI/设备兼容性。

下一步是确认 KV260 连接与 A 的可用时段，在实际板端运行预检，再验证缓存音频与动画、眨眼、口型、暂停/恢复、打断和实屏。原演示布局需要按实际 1024×600 目标调整；随后与 A 的视觉/FPGA版本并行测资源和响应，再接 Windows 动态媒体。连接信息未到前不将此阶段写成板端通过。
