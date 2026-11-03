# 2026-10-15 缓存接口修复与真实 MCP01 采录

用户在阶段复核后要求“那就继续”。本轮读取 ZIP README、项目规则、近期进度和下一轮实施清单，从已确认的缓存语音错误和真实录音入口推进。详见 [本轮报告](/home/ghmd/aura-media-integration-20261015/REPORT.md)、[操作说明](/home/ghmd/Win共享文件/共享文件夹/aura/docs/BOARD_AUDIO_CAPTURE.md)。

## 实际完成

- 恢复 `VoiceWorker(cached_only=True)`，缓存失效/直接请求拒绝推理，缓存模式预热不加载模型。原 7 项错误恢复通过，新增 2 项相关边界用例。
- 新增 MCP01 标准库采录适配器、显式 CLI 和 9 项采录测试，返回现有 `AudioRef`/PCM。最终主机框架 **149 项全部通过**，原缓存资源 **573 帧/4 段音频预检通过**。
- 主机实际发现 Xilinx 串口并连接 KV260。实测 MCP01 原生采录为 **16 kHz/单声道/S16_LE**，播放为 48 kHz/双声道/S16_LE；不能把输出格式当输入格式。
- 发布独立包 `9a829a5e2472ec17` 至板端新目录，8 文件 SHA 核验通过。没有替换正在运行的 GUI/视觉包。
- 真实录音 3.000 秒、48000 样本/96000 PCM 字节；提前停止返回 6000 样本；取消后无结果；第二个采录适配器被拒绝；结束无 PCM 设备占用。
- 录音期间相机采集 +71、检测 +57，无相机/检测/预览错误，相机服务代次及两个既有服务状态/PID/重启数保持一致。
- 26 份 UART 响应逐帧独立解码，长度/SHA 与原始输出一致；实际 WAV 回读、发布包及源码对应检查通过。见 [核验汇总](/home/ghmd/aura-media-integration-20261015/validation.json)。

## 环境与阻塞

板端 boot `87de5501-540e-4799-9285-2d7048c1ae90`，现有视觉和 UI 服务实际可用。本轮没有观察本次关机/上电全过程，不作为新冷启动验收。

`eth0` 实测 NO-CARRIER、没有 IP 或路由，跨机问答暂不能进行。已通过异步问题请求用户接入同一局域网并提供 Windows IP/服务状态；本轮没有擅自配 IP 或改变网络。

当前完成的是 M6/L2 的采录子项与缓存回归修复，**没有完成完整语音问答或 L2 放行**。触屏录音按钮、统一音频所有者、媒体传输与 Windows 返回播放仍需接入；录音的启动前播放检查不等于所有程序的严格半双工互锁。

## 处理过的问题和范围

沙箱未显示设备后，经主机侧授权检查找到实际串口；一次 `ls` 因缺 `/dev/ttyACM0` 返回 2，不影响已发现的 Xilinx USB 串口。首次验收脚本超 UART 长度预检未发送任务，后改分段上传；首次核验脚本未兼容提示符后 BEGIN 行，修正后对相同原始证据 26 份全部通过。错误限于探针/助手，不是硬件故障。

修改文件：主仓 `tools/selected_voice_service.py`、`tests/framework/test_cached_voice.py`、新增 `board/runtime/audio/capture.py`、`tools/board_audio_capture.py`、`tests/framework/test_audio_capture.py`、`docs/BOARD_AUDIO_CAPTURE.md`；同步 README/框架状态/跟踪说明和资料导航。本机工作与验证工件在 `/home/ghmd/aura-media-integration-20261015/`，操作前文件副本已保存。

未调整麦克风/播放音量，未播放本轮录音、执行新 ASR/LLM/TTS/网络问答或操作 FPGA/舵机；未重启整板或替换系统服务。人声可懂度、完整取消到停声、长稳和整机验收均未冒充通过。
