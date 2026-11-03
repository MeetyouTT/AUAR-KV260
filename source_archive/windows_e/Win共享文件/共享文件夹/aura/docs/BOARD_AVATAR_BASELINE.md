# 汐蓝板端缓存播放基线

更新：2026-10-09。A 当前负责视觉与 FPGA；这项工作与 A 并行，目标为 KV260 PS/Linux 上的玩偶显示和音频播放。

## 本轮已准备

- `tools/realtime_stage.py --cached-only` 复用已有动画、眨眼、音强口型和真实音频进度逻辑，只消费已有缓存；缺失或损坏的音频明确失败，不启动 TTS 推理，关闭对话请求。
- 缓存模式默认保留最多三个正式素材序列；仍会初始化既有嘴部/眼部资源，这个数不是总内存上限。实际板端内存、解码开销和帧率须测量。
- 新模式的运行记录默认写到相邻 `board_avatar_runs/<唯一编号>/`，不覆盖旧 Windows 演示的验证记录；可用 `--evidence-root` 指定新目录。
- `tools/board_avatar_preflight.py` 在不播放声音、不启动模型的条件下核对正式 PNG、选定声线缓存和眨眼图层。资源入口只需标准库；显示和音频播放仍需目标平台支持的 Pillow、NumPy、PySide6/QtMultimedia。
- 音频包按需加载模块，保留原有 36 个公开导出名称；读取缓存不再提前加载 ASR/KWS/TTS。语音服务的 PCM 处理依赖也按需加载。Python 3.8 的线程池关闭使用其支持的参数。

旧 `stage_config.json`、缓存 WAV、选定参考声线、素材与 A 的平台工程没有被修改。原默认实时入口仍保留新台词合成能力；缓存限制必须显式选择 `--cached-only`。

## 本轮实际检查

工作目录：`/home/ghmd/aura-board-avatar-baseline-20261009`。

- 标准库框架和缓存限制测试 **48 项通过**，包括缓存命中、缺失、损坏、格式错误、声线身份改变、原默认模式及公开接口兼容性。
- 正式 **16 套/573 帧 PNG** 的原清单大小和 SHA256 一致；四段演示 WAV 的选定声线身份、SHA256、24 kHz/单声道/16 bit 格式和时长一致；42 张眨眼图层 SHA256 一致。
- 资源检查通过，不表示五套嘴部的实际合成、Qt 绘制、扬声器、MCP01、取消静音或并行性能已验收。
- 当前 Ubuntu 为 x86_64/Python 3.8.10，Pillow 存在，NumPy/PySide6 不存在；环境检查按预期返回 `NOT_READY`/退出码 2。没有安装依赖或启动窗口。
- 当前未检测到 USB 串口，网络接口检查只显示 Wi-Fi/回环及未启用的 Docker 接口。尚未获得 KV260 网络地址或可用时段，未连接或更改板卡。

具体记录：工作目录 `resource_validation.json`、`ubuntu_environment.json`、`unittest_validation.json` 与 `unittest_output.txt`。三个原源码文件的字节备份及哈希在 `previous/` 与 `source_before.json`。

## 连上目标板后的执行次序

保持以下目录相邻，按当前复用代码的相对路径回收资源：

```text
共享目录/
├── aura/                         # 当前源码、assets/avatar、ui
└── deliverables/
    ├── 2026-10-06_avatar_reuse/   # 五套复用口型来源与配置
    ├── 2026-10-06_voice_blink/    # 眨眼层与配置
    ├── 2026-10-06_voice_selected_soft_young/ # 已选声线身份与参考
    └── 2026-10-06_xilan_live/     # 四段缓存与浏览器控制页面
```

在板端实际图形会话中进入 `aura/`，先执行只读检查：

```bash
python3 -s tools/board_avatar_preflight.py --probe-display-audio
```

这项读取 Python 依赖、DISPLAY、xrandr 和 ALSA 清单，不安装软件、不切换显示模式、不播放音频。`NOT_READY` 时根据具体缺项确认镜像支持的依赖或渲染路径；不能用 Ubuntu 主机的结果代替目标板结果。通过检查仍需下一步真实设备验证。

确认资源、显示会话和音频输出就绪后：

```bash
python3 -s tools/realtime_stage.py --cached-only --config config/board_avatar_baseline.json
```

首轮按顺序操作：待机与眨眼 → 打招呼 → 开心/安慰 → 长句 → 暂停与恢复 → 说话中打断。检查声音实际停止、口型同步、旧声音不恢复、最后回待机；留下实屏照片或录像及程序证据。

此入口复用现有演示窗口与 Qt 音频适配，不是最终 1024×600 正式 UI。目标板上的布局、字体、实际 Qt 音频后端和性能均未测；按实屏结果调整后再验收。随后在 A 的视觉/FPGA版本下并行运行并记录帧间隔、内存、音频进度和响应；完成后接 Windows 的动态媒体服务。

机构与舵机标定继续等待 3D 模型。本阶段没有相机访问、运动寄存器写入或模型生成入口。
