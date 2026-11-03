# 当前模型处理位置与大小

**最新实施更新（UTC2026-10-22 07:25后）：YuNet已通过30分钟实时检查并保留DPU配置；SFace又通过真人三模型影子短测（10次完成，平均14.48ms），随后恢复到YOLO＋YuNet常驻，SFace正式身份仍配置WindowsCPU。** YuNet活动xmodel576,254B，新SFace候选10,796,375B；影子不判定身份/不写库，当前关闭。完整状态/性能/限制见[实时交付](../2026-10-21_dpu_live_baseline/README.md)和[真人短测](../2026-10-21_dpu_live_baseline/SFace_真人影子短测.md)。下方早期只读操作说明及Windows未在线确认等保留其证据范围。

**后续纠正：本页原表仅覆盖6项主业务，漏列了当前语音前端的GTCRN和Silero VAD v5。实际配置共涉及8项功能模型；另有OmniVoice内部组件、待接Light-ASD/VLM及历史候选，完整解释以[全模型概览_当前.md](全模型概览_当前.md)为准。新增两项已配置Windows CPU/8795，但当前健康查询超时，权重大小未实读。下表保留本轮原六项大小证据。**

日期：2026-10-21（America/Los_Angeles），采集对应 UTC 2026-10-22。先读完整 ZIP 的 README、整体方案/分工、最新项目日志及双机入口，再通过已有独占 UART 只读查询实际相机配置、模型文件 stat 和服务健康。没有下载、推理、部署、重启、控制显示或发运动指令。

**最新配置：YOLO和YuNet CNN在KV260 DPU；YuNet预后处理仍ARM CPU；SFace正式特征后端仍配置WindowsCPU。语音识别、27B文本对话及OmniVoice仍是Windows端链路。** SFace DPU已完成固定板测、接入候选/纯配置检查与真人影子执行，当前生产身份没有选用该候选；独立登记/阈值待验。

| 模型 | 用途 | 当前处理位置 | 模型文件大小（十进制） | 本轮证据范围 |
| --- | --- | --- | --- | --- |
| YOLOX-Nano / person | 人体检测 | KV260 PL / B4096 DPU | 2,127,303 B ≈ 2.13 MB | 实际活动配置、板端 stat；相机健康约 9.91 Hz |
| YuNet 2022mar，INT8 CNN | 人脸框、五点关键点 | KV260 PL / DPU卷积＋ARM预后处理 | 活动xmodel576,254 B≈0.576MB；回退ONNX345,478 B | 最新30分钟实板9.95Hz YOLO/2.37Hz YuNet，已保留配置 |
| SFace 2021dec | 人脸身份特征 | Windows CPU / ONNX Runtime，板卡调用 8792 | 38,696,353 B ≈ 38.70 MB | 活动 feature_backend=windows_sface；实际代码标记 WINDOWS_CPU_SFACE_ORT；Windows 本轮未在线确认 |
| Paraformer INT8 | 中文语音识别 | Windows CPU，原运行配置为 2 线程 | 243,371,218 B ≈ 243.37 MB | 本地共享权重 stat；执行位置来自实际服务源码及最近运行证据 |
| 27B 本地标签 aura-qwen3.8-27b-abliterated:iq4_xs | 文本对话 | Windows GPU / Ollama | 保存的 Ollama size=13,885,180,476 B ≈ 13.89 GB（12.93 GiB） | 10-18 保存运行记录，parameter_size=27.3B、IQ4_XS；本轮未实读 D 盘或实时 GPU |
| OmniVoice，16 步 | 语音合成 | Windows GPU，原运行配置 float16 | 两份权重共 3,256,009,740 B ≈ 3.26 GB（3.03 GiB） | 本地共享实际权重 stat；GPU 位置来自实际代码/已接受运行记录 |

这里的大小是磁盘模型文件大小，不能直接当作推理峰值内存/显存。MB/GB 按 1000 进制；MiB/GiB 按 1024 进制。

## OmniVoice 内部组成与其他资源

- 主网络 `model.safetensors`：2,450,344,112 B，约 2.45 GB。
- 内部音频编解码组件 `audio_tokenizer/model.safetensors`：805,665,628 B，约 805.67 MB；不是另一项独立业务模型。
- 含 tokenizer/config 等资源的完整 OmniVoice 目录：本轮本地统计 3,267,467,859 B，约 3.27 GB。
- Paraformer 完整资源目录：245,097,569 B，约 245.10 MB。
- SFace DPU 工程候选 `sface_engineering.xmodel`：10,796,371 B，约 10.80 MB。它属于已做板测的候选，不能以它的大小替换当前 ONNX 业务模型大小。
- Light-ASD 尚无新的模型已接入证据；VLM 看图后端尚未冻结验收。没有为这两项填写推测大小。
- ByteTrack 在 KV260 CPU 上做跟踪，不是独立神经网络权重；板端音频播放和口型动画也不另算 TTS 模型。

## 实际路径

板卡活动模型：

- YOLO：`/home/root/aura-bytetrack-20261011/models/yolox_nano_person.xmodel`。
- YuNet活动：`/home/root/aura-dpu-vision-20261021/staging/3f10273827d88501/kit-974f2fb1a5641f10/yunet_public_int8.xmodel`；原`/home/root/aura-adaptation-20261006/identity/models/yunet_2022mar.onnx`保留作预后处理参考/CPU回退。
- SFace 原本地参考文件仍存在：`/home/root/aura-adaptation-20261006/identity/models/sface_2021dec_retry.onnx`；活动后端已配置为远程 Windows 特征服务，该文件存在不表示当前在板端执行 SFace。
- 当前活动相机配置：`/home/root/aura-dpu-vision-20261021/runtime/81fdb11903abb71e-live-134783/board_camera_ui.json`；同目录`board_identity.json`设置`face_backend.kind=dpu_yunet`、`feature_backend.kind=windows_sface`，目标`192.168.50.1:8792`。原handsfree-dialogue/candidate-0c0a8ab46ec2配置保留作整套回退。

Windows 已有配置/共享资源所指路径（本轮没有读取 Windows 进程命令行）：

- 27B 权重及下载目录：`D:\AIModels\qwen3.8-27b-abliterated`；Ollama 模型库：`D:\AIModels\Ollama-AURA`，配置见 `aura/config/model_storage.local.json`。
- ASR：`E:\Win共享文件\语音共享文件\aura\models\asr\sherpa-onnx-paraformer-zh-2023-09-14`。
- TTS：`E:\Win共享文件\语音共享文件\aura\models\tts\OmniVoice`。
- SFace 共享参考权重：`E:\Win共享文件\语音共享文件\aura\models\vision\sface_2021dec.onnx`；不能据本地镜像确认 Windows 本次加载的绝对路径。

## 当前状态与限制

三次串口事务均退出 0、响应长度/SHA 校验通过、控制台回显恢复。相机服务 PID1017，界面监督服务 PID1078，均 active / NRestarts=0；相机健康检测 9.91 Hz，camera_error/detector_error 为空，identity_recognition=true 表示功能配置启用，不等于本轮身份识别成功。

本轮从板卡访问 Windows 8792、8791 健康接口均超时。只能确认配置的执行位置和历史语音运行结果，不能确认 Windows 模型现在已加载或 SFace 远程请求现在成功。没有借此判定服务停止或网络故障的具体原因。板卡自带时钟显示 2021 年，采集时间使用 Ubuntu 主机 UTC，未修改板卡时钟。

初次沙箱内串口路径不可见，提权后既有串口可访问；未把沙箱不可见写成板卡掉线。最初探测了两个错误本地 API 路径（拒绝/404），后按活动配置确认真正接口为 `127.0.0.1:8790/health`，已查询成功。本轮没有完整模型 SHA 复核、推理正确性/真人准确率测试或峰值内存测量；本地 ONNX 包接口不兼容，未完成 ONNX 参数量统计，未将常量数伪作参数量。

过滤证据见 [evidence.json](evidence.json)。私有原始 UART 和源配置留在 `/home/ghmd/aura-model-inventory-20261021/`，不复制人脸照片、身份库或权重。Windows 是否同步接收以其独立回执为准。
