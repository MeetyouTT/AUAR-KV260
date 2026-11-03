# 同一 ECAPA 权重的板端 ONNX 候选

当前完成 Windows CPU 导出及真实 ARM 公开样本数值验证，没有部署。没有读取私人声纹库、真实录音或身份模板，没有打开麦克风/播放、修改阈值或授予个人记忆权限。

[ARM实测报告](arm_equivalence.json)：Python3.9.9、NumPy1.21.2、隔离ORT1.17.3，四个原公开 WAV 全部通过。最大 embedding 分量误差 `3.77e-7`，样本对 cosine 最大误差 `1.70e-7`。单线程加载2.028秒，逐项编码2.198–3.914秒，RTF为1.21–1.26，本进程HWM/RSS为182264KiB，约178MiB。同模型已证明能够在板端运行；本配置编码慢于音频实时速度，尚未完成在线调度/并发或真人声纹标定。

测试进程已确认退出，UART echo恢复，临时公开资源服务器按180秒TTL退出；板端前后均IDLE、麦克风/播放/跟随关闭。候选保存在 `/home/root/aura-board-owner-candidate-20261030/speaker-c695feae5eaf88eb`，只读复用FFT候选的隔离ORT。详见[汇总](summary.json)和[evidence最终回执](evidence/20261030T131012280507Z-poll/result.json)。

时钟需单独处理：板端启动记录的wall clock约为2021年，Ubuntu证据UTC目录为2026年。本次性能计时使用perf_counter，不受此差异影响；真实记忆迁移前应明确核验时间基准。本任务没有修改系统时间或NTP。

候选资源全部位于 `D:\AIModels\speaker-identity\board-onnx-20261030`，原 `ecapa` 目录的模型 manifest 复核通过。共享目录只保存源码、CPU 报告、资源指纹和隔离导出依赖，不保存语言模型权重。`export_dependencies` 是 Windows 导出依赖，禁止作为 ARM 运行包复制。

## 已验证内容

- 来源：原有 `speechbrain/spkrec-ecapa-voxceleb`，revision `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286`，embedding checkpoint SHA256 `0575cb64845e6b9a10db9bcb74d5ac32b326b8dc90352671d345e2ee3d0126a2`。
- 原入口：16kHz mono PCM16，除以32768，80维 Fbank，400点周期 Hamming、FFT400、160点 hop、中心补零，80dB动态范围裁剪；逐句均值归一化，不做标准差归一化；192维 ECAPA 输出做 L2 归一化。
- `encode_batch(normalize=False)` 不调用全局 embedding 均值归一化，也不调用7205类 classifier。导出图只包含原 FP32 embedding 网络，原 window 与 mel matrix 另存为只读 NumPy 常数。实际1.0.3实现使用 constant padding；未依据旧文档中的 reflect 描述替换。
- 图：opset17、IR8、单批次、动态帧数、输出192维；83,439,430字节。前处理常数66,438字节，公开验证夹具968,694字节。
- [CPU数值报告](cpu_equivalence.json)：四个原公开 WAV，加公开音频100ms裁剪与20s重复边界，共六种长度。归一化 embedding 最大分量误差 `8.77e-7`，任意样本对 cosine 最大误差 `3.57e-7`；预先采用 `5e-5` 分量/样本对误差门槛。数值接近不等于现场说话人准确率或阈值已经标定。
- 十六项独立失败/边界测试通过，包括PCM长度、无效输出、零向量、文件篡改、输入名称和线程范围。CPU测试不证明ARM延迟或整机并发余量。

## ARM 公开夹具验证

[资源白名单](assets_manifest.json)只列同模型图、常数、公开夹具、两个候选源码及既有官方 ARM ORT wheel，共约90.35MB。可复用 `../ubuntu/serve_candidate_assets.py` 的临时、仅板端GET白名单服务器。按每项SHA验证，复制到新的候选目录；不读私人模板或原录音，不改任何活动服务。此次板测直接复用已验证的隔离ORT，未再传wheel或改baseenv。

原板端 ORT 导入已在相邻任务中观测到进程 abort，不能因为 find_spec 成功就继续使用。使用原有官方 `onnxruntime-1.17.3-cp39-cp39-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl`，仅在新目录解包，通过短命进程的 PYTHONPATH 选择。模型IR8/opset17处于官方1.17的IR9/opset20支持范围内；运行时实际导入和建图仍须验收。

串口由 root 统一交接。建议先用单CPU线程、低进程优先级、90秒外部超时，仅跑四个原公开 WAV；20秒重复边界在CPU已验证，首轮ARM明确省略。

```sh
PYTHONNOUSERSITE=1 PYTHONPATH='<isolated-ort-deps>' timeout 90s nice -n 10 python3 -B arm_verify_public.py \
  --candidate-dir '<isolated-candidate>' \
  --encoder-module '<isolated-candidate>/board_speaker_onnx.py' \
  --expected-manifest-sha256 d59b61bd1dfffacabf4927ec55e9469550882ff213c1b5ac5d3b6fa2dd6f77fe \
  --expected-fixtures-sha256 a3d536b79a713ba726a0be4a1c341d188be8a988465c4d858c232084e1463ccb \
  --indices 0,1,2,3 --threads 1 --budget-seconds 75 --report '<isolated-candidate>/arm_report.json'
```

runner 输出每项数值误差、耗时、RTF和本进程RSS/HWM，不输出 embedding 向量，不导入Torch/SpeechBrain，不打开身份库或音频设备。ARM实测可能不足以满足在线实时预算，必须按报告保留限制。原WebRTC VAD、声纹采样和身份授权链不属于本次encoder导出的完成范围。

## 官方依据

- [SpeechBrain 官方模型与16kHz输入要求](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb)
- [SpeechBrain 特征模块接口](https://speechbrain.readthedocs.io/en/latest/API/speechbrain.processing.features.html)
- [PyTorch 2.5 ONNX导出接口](https://docs.pytorch.org/docs/2.5/onnx.html)
- [ONNX Runtime版本兼容表](https://onnxruntime.ai/docs/reference/compatibility.html)

官方资料提供模型、特征及导出接口；本候选的端到端一致性结论来自本目录实际数值报告，不能将第三方预导出模型当成同一工件。
