<!-- local-open-source-integrated-20261021 -->
用户已选择本地开源并完成首阶段接入，当前结果、启动与回退见 [INTEGRATION.md](INTEGRATION.md)。313回归通过，监听保留，现场噪声/新版打断仍待实测；声纹尚未进入正式聊天。以下为之前的隔离评估历史。

# 环境声前端：成熟组件隔离验证

2026-10-21。当前阶段完成组件与流式路径验证，**没有切换正式对话入口**。正式仍为922dab、监听true、IDLE_READY。用户关于开源、商业SDK、成品阵列的偏好尚未确定；“有什么区别”不是对收费授权或购买硬件的选择。

## 已得出的实现选择

使用上游预训练组件，不训练或重写降噪、VAD、声纹网络：

- 普通环境声候选为GTCRN降噪＋Silero v5 VAD，优先通过已有sherpa-onnx成熟API组合。
- 板端保留现有收音/AEC/归属和取消控制。组合前端放电脑CPU：板端组合跑不实时，不能硬塞进UI或继续积压PCM。
- 声纹继续复用D盘现有SpeechBrain ECAPA，未接入生产或更改门槛，未读取个人库。
- 这不解决所有电视/旁人人声，也不是固定发声者锁。声纹、视觉/空间归属及专用人声隔离后续分层处理。

官方依据：[Silero](https://github.com/snakers4/silero-vad)、[sherpa VAD](https://k2-fsa.github.io/sherpa/onnx/vad/silero-vad.html)、[GTCRN作者项目](https://github.com/Xiaobin-Rong/gtcrn)、[官方流式GTCRN例子](https://github.com/k2-fsa/sherpa-onnx/blob/master/python-api-examples/online-speech-enhancement-gtcrn.py)。GTCRN是本轮新增对照：现有16kHz格式可直接测试，RNNoise的48kHz适配留作备选，不称已经集成WebRTC/RNNoise。

## 实测证据

| 验证 | 本轮结果 | 限制 |
| --- | --- | --- |
| 35个公开/生成场景 | 五个非语音场景含静音，原能量4次起点；Silero v4/v5均0次。另30个语音变体，v5均产生完整段 | 四类噪声是确定性生成信号，不是真实风扇/键盘或房间成绩；完整段不等于逐字正确 |
| 弱声、强噪声 | v4部分弱声能起听但在既定1.1秒静音尾部内未交段；v5修正该批收尾，直接强噪声检测仍有提前分段/首词退化 | 失败保留，不用提高起点门槛掩盖 |
| GTCRN后接v5 | 三段中文各清晰/弱声/5dB/0dB四变体，共12个，全部完整收尾为1段 | 降噪语音仍有词变化；ASR对ASR不是独立人工标注准确率 |
| ASR双分支 | 比较增强语音识别，以及增强只供检测、按边界截取原始PCM供识别 | 原始PCM分支减少部分变化，但最强噪声仍有词差；实时延迟对齐尚未接入，不能写首音全通过 |
| 板端v4 | FP32 CPU约11–12%单核等效，INT8约15%，本轮INT8更慢 | 仅短时独立进程，不等于开启麦克风后的整机预算 |
| 板端v5 | CPU约14%，初始化约1.37–1.58秒，20ms feed P95约6.6–11.5ms | 初始化必须提前，不能卡在UI线程或“我在听”之后 |
| 官方SDK板端组合 | 处理1秒音频用约1.26–1.51秒墙钟，CPU约1.01–1.06秒；20ms包处理P95约48–60ms | **不具备持续实时能力**，不作为板端正式方案 |
| 电脑端GTCRN | 离线流式调用计算RTF中位约0.047 | CPU例测，不是整轮回答耗时 |
| 板端→电脑CPU组合→板端 | 337个20ms公开音频帧，约6.74秒，往返P95约3.71ms、最大6.29ms，0包超过20ms；两端PCM SHA相同；主机进程CPU等效约9.3%单核 | 只验证一次有节奏的公开音频路径；不包含模型算法延迟、起止判断等待及ASR/LLM/TTS。临时端口已关闭 |
| 既有ECAPA复用 | 禁网CPU，两名公开说话人独立参考/查询，同人约0.7295/0.6649、异人约0.0552/0.0060 | 未登记、未改阈值、未读取个人库；不能据此定现场阈值或声纹抗噪成绩 |
| 相关回归 | 117通过、1平台跳过，含10项新适配边界测试与原打断/聆听/免点击测试 | 不是正式全项目回归或本版真人验收 |

原始报告：pc_benchmark.json、asr_public_comparison.json、board_benchmark_v4.json、board_benchmark_v5.json、board_sdk_benchmark.json、stream_transport_probe.json、speaker_public_baseline.json、tests_pc.log。模型/公开样本哈希在asset_manifest.json及其引用的旧声纹公开样本清单，原型计算过程保留，不把生成噪声标成真实环境。

## 已写的适配代码与启用状态

共享源码中新增`board/runtime/audio/silero_gate.py`：仅薄封装固定官方ONNX导出的20ms输入、512采样模型窗、v4/v5循环状态、校验和失败状态。`vad.py`及`automatic_capture.py`增加默认不启用的`frame_classifier`注入点；音频原始PCM、事件与当前默认判据保持。`test_silero_gate.py`覆盖连续无重叠模型窗、有限缓冲、捕获间状态隔离、v5上下文、异常拒绝及前导PCM。

这些源码仅用于隔离对照，**正式启动配置没有引用或开启它们**。优先实现方向是成熟sherpa-onnx SDK，不把这份ONNX对照封装当必须替代SDK的自研算法。当前没有新增常驻服务、板端模型导入、麦克风监听者或GPU任务。

## 运行依赖与失败记录

- 最初只读inventory查到板端ONNX包，但独立进程`import onnxruntime`即abort，见board_runtime_diagnostic.json；不能把find_spec存在写成可用。正式UI没被重启。
- PyPI官方ARM64 ORT1.17.3在独立目录可用；随后匹配的sherpa-onnx/core1.13.8同样在独立目录验证成功。仅解包测试，没有覆盖系统包。官方PyPI SHA记录在board_runtime_wheel.json、sherpa_runtime_wheels.json。
- 首次SSH在banner阶段断开，重试成功；旧板端ONNX导入失败是隔离子进程的真实失败。首次降噪输出D盘权限失败后以已审查的外部路径重跑；首次相关回归因沙箱阻止临时HTTP及文件替换出现4失败，允许条件下复测115通过，增加v5测试后117通过/1跳过。没有将这些失败算作成功证据。
- PC原有CPU依赖已满足，无pip安装或生产模型/配置更换。声纹原型固定模型哈希仍由其原有验证器校验，保留上游torch加载警告，不写成产品漏洞已修复。

模型和依赖下载位于`D:/AIModels/audio-frontend-eval-20261021`；ECAPA继续在`D:/AIModels/speaker-identity`。板端隔离目录`/home/root/aura-environment-eval-20261021`。它们没有大语言模型，也没有新增个人录音。共享目录仅源码、许可证、清单和小型报告；代码ZIP不含模型/环境/音频/身份库。

两个轻量v4导出验证了官方发布SHA；v5和GTCRN旧发布没有提供digest，本轮记录官方asset ID/长度和本地SHA，不伪称有独立上游SHA认证。

## 正式接入前尚需完成

电脑端流式前端需绑定capture/request/代次，设置有界队列、过期/取消隔离与断网处理；初始化和模型下载不得占用音频回调或UI线程。要验证GTCRN输出样本延迟、VAD边界和原始PCM前导的实时对齐，保留当前ASR/完整播放ACK/遗忘排除和回声核验。临时TCP实验没有实现这些生产契约，不能直接作为常驻服务使用。

完成适配后再进行最新正式根上的回归、隐藏界面、真实开麦负载及受控现场测试。电视、旁人、多人/远近、低声短句、播放中插话和主观延迟均须另验。未达到这些条件，本轮保留原正式入口与监听true，不以离线数字替代真人结果。
