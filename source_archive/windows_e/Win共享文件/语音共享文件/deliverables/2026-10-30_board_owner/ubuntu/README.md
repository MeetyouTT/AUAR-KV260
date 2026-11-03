# 板端业务主控：运行候选与 ARM 实测

2026-10-30。此目录记录本次新增代码、依赖准备和实板候选验证，**没有切换生产业务、迁移真实库或开麦/播放/运动**。现役仍为 r3-ubuntu、286 pins。Windows 最终只承担现有 27B/OmniVoice；本次候选不是该最终归属已经上线的回执。

## 已交付的候选

- `aura/board/runtime/board_dialogue.py`：可注入 ASR、模型客户端、板端 Store、权限/记忆命令/上下文/视觉入口。按板端 ASR → scope/记忆/上下文 → Win LLM → 板端校验分句 → Win TTS → 板端播放凭据顺序工作。历史仅在显式 `history_query` 时查询；生产应注入根代理的受容量约束 `context_builder`，包括连续性摘要。
- `aura/board/runtime/board_dialogue_client.py`：HTTP 模型协议 v1；每个 LLM/TTS 子请求独立 ID，固定 boot/session/generation，沿原 monotonic deadline 递减预算，零重试。取消先停止本地交付，再进行最多一秒的独立取消清理；清理不续期结果预算。
- `aura/board/runtime/audio/board_asr.py`：只接受 16 kHz mono PCM16，严格使用原 `model.int8.onnx` 和 tokens SHA，无自动模型替换；识别失败/过期/取消不产出可采纳文本。
- `aura/board/runtime/audio/board_asr_frontend.py`：板端同模型 GTCRN/Silero 决策适配；保留现役 threshold=.5、Silero min duration=0、max=19s、1 CPU thread、32 帧预热。原 board endpoint 继续拥有 onset、700ms silence、pre-roll 及 utterance 长度；原 PCM 不被该检测器改写。
- `aura/board/runtime/audio/board_gtcrn_fft.py`：后续 FFT 候选，保留同一 GTCRN 权重、窗/隐状态/OLA/flush，用 NumPy rfft/irfft 代替官方流式实现的二次 DFT。Windows 和 ARM 均已做逐段 PCM/VAD 对照；只独立候选使用，未接生产。

控制器只准备 `PlaybackPlan`，不打开播放器。`acknowledge` 必须收到同代次、同计划的 `playback_token + sha256 + samples`；缺失、部分、不匹配或旧代次不得算成用户已经听到。`generated` 保存正文并带来源引用，完整播放前不进入助手已播放记忆。单写者启动时由集成入口显式调用 `store.recover_interrupted_turns()`。

命令 hook 为 `command_handler(text, scope, *, turn_id, generation, user_event_id)`；上下文 hook 为 `context_builder(context, text, history)`；视觉入口只调用注入的 `visual_event_sink`。内部 scope/event ID 仅留在板端来源关系中，默认历史文本也不向模型发送这些字段。

## 实测结果

| 验证 | 实测 | 判断 |
| --- | --- | --- |
| ARM 环境 | Python 3.9.9 / aarch64 / glibc 2.34 / 4×Cortex-A53 / NumPy 1.21.2；RAM 总 4,023,988 kB、可用约 2.9 GB，无 swap；`/home/root` 可用约 9.03 GiB | 可隔离准备候选；初始无 sherpa/torch/torchaudio/speechbrain/scipy/sounddevice |
| Paraformer 原模型 | 5.6146s 上游公开 WAV；同 sherpa/core 1.13.8；模型加载 12.9439s；两次识别 6.9205s / 6.9106s，RTF 1.2326 / 1.2308；两次文字相同；峰 RSS 429,572 kB | **实际 ARM 识别通过；实时/整机体验未通过** |
| GTCRN/Silero 原模型 | 同一公开 WAV 的 281 帧，185 speech；ARM 与现役 Windows Pipeline 决策逐帧一致；均 SHA `dd974e954ff4d5fe19eca38aba323ce6692b6089b772764ddab7256c1fb9f9b6` | 此公开样本语义等效；不是现场降噪/误唤醒验收 |
| ARM frontend 帧耗时 | 初始化 2.5685s；均值 32.3532ms / P95 61.8012ms / 最大 108.9906ms；238/281 帧超过 20ms；峰 RSS 81,256 kB | **不满足现役 20ms 帧预算，不能直接接逐帧采集线程** |
| 后续 FFT 候选 | ARM 同模型逐段 PCM 最大误差 5.96e-8 / RMS 7.17e-9、样本数/flush一致；281 帧 VAD 决策一致；1线程均值 18.1359ms / P95 29.5556ms / 最大49.8216ms，77/281超20ms；CPU92.57%单核基准 | 均值具备短样本实时吞吐，**严格逐帧20ms及长稳门槛仍未过，保持候选** |
| ARM 控制器烟测 | 真实 Python/SQLite/回环 HTTP；合成模型回应；8 项 ACK、取消、代次、idle 检查通过 | 证明 ARM 候选可运行；不是实模型、真实播放或生产迁移验收 |
| Windows 新逻辑回归 | 控制器/HTTP/ASR 36 项，加 `test_board_gtcrn_fft.py` 的 10 项实际资源边界，合并一次运行 46 passed | 包含真实候选 Store 联用、错误/过期/取消、跨 scope 拒绝；不与其他代理数量相加 |

ARM 控制器烟测针对 `control-d14a9312f888b7b8` 冻结快照。其后默认历史上下文只增加了内部 ID 剔除，最终源码 36 项 Windows 回归已重跑；最终发布仍须由根代理用最新冻结源码重验。

## 隔离目录与依赖

- ASR：`/home/root/aura-board-owner-candidate-20261030/asr-1.13.8`，模型/公开 WAV、两只官方 wheel 和独立 `deps/`。没有安装/改写板端 baseenv。
- frontend：`/home/root/aura-board-owner-candidate-20261030/frontend-b3d06b653876469d`。
- 控制器：`/home/root/aura-board-owner-candidate-20261030/control-d14a9312f888b7b8`，只合成 SQLite 测试；临时 DB 已由该测试清理，没有真实数据。
- FFT：`/home/root/aura-board-owner-candidate-20261030/fft-ee19b936d17aa451`，新源码和独立 ORT 1.17.3 `deps/`；复用已钉住的板上前端模型。该 ORT 已实际加载和推理，可供其他独立候选只读复用。

ASR 模型、tokens、公开 WAV 合计 243,626,686 bytes。依赖为官方同版 [sherpa-onnx 1.13.8](https://pypi.org/pypi/sherpa-onnx/1.13.8/json) `cp39-cp39-manylinux2014_aarch64`（4,175,595 bytes）和 [sherpa-onnx-core 1.13.8](https://pypi.org/pypi/sherpa-onnx-core/1.13.8/json) `py3-none-manylinux2014_aarch64`（13,353,426 bytes），符合实际 cp39/glibc>=2.17。官方安装入口见 [sherpa Python 安装说明](https://k2-fsa.github.io/sherpa/onnx/python/install.html)。解包后实际模型加载及推理已经验证，未复制 Windows 虚拟环境。

Paraformer SHA `f36a0433bcf096bd6d6f11b80a3ac8bed110bdca632fe0d731df8d1a84475945`；tokens SHA `59aba8873a2ed1e122c25fee421e25f283b63290efbde85c1f01a853d83cb6e6`。GTCRN 535,638 bytes / `e77603ac0c23dac3227dd2d7135b3a585cbee2679048aecfa886657d3ae1b534`；SileroV5 2,313,101 bytes / `6b99cbfd39246b6706f98ec13c7c50c6b299181f2474fa05cbc8046acc274396`，均为现有已配置资源。

资源通过临时 Windows 白名单 HTTP（只允许现有网线板端 IP）由板端主动 GET，清单 SHA 经独占 UART 钉住，每文件再次 SHA 核验。服务器有 180/300 秒自动退出，不新增自启或常驻服务。`board_*probe.py` 中 BASE/PIN 是当次冻结证据，不能拿过期端口盲重跑；重放须重新启动临时服务、冻结清单并更新审阅后的探针。

原系统 Python ORT 路径在独立子进程尝试建原 GTCRN session 时退出 -6，报 `Can't add new modules after the interpreter has been initialized`，没有改变或修补它，也不能据此归因为 opset 不支持。FFT 使用既有官方 `onnxruntime-1.17.3-cp39-cp39-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl`（5,861,150 bytes，SHA `3ff2dc012bd930578aff5232afd2905bf16620815f36783a941aafabf94b3702`）隔离解包，NumPy 仍为板原1.21.2。

ECAPA 原 torch/torchaudio/speechbrain 路径在 ARM 不具备。本代理未安装这些包或复制声纹模型/模板；记忆代理后续已准备同权重 ONNX 候选，并在本次 FFT 后接手 UART，其结果另行记账，不在本报告预填完成。未读取身份数据库或真人录音，未假定声纹阈值已标定。LLM 权重/Ollama 未动，继续留 D 盘。

## FFT 等效性与性能边界

同版 [官方 streaming STFT 实现](https://github.com/k2-fsa/sherpa-onnx/blob/v1.13.8/sherpa-onnx/csrc/online-speech-denoiser-stft-impl.h) 的 `StreamingDft` 是二次直接 DFT。候选保留 periodic sqrt-Hann（512点）、256 hop、float32 实虚交错、三个循环状态、首hop丢弃、OLA、总样本长度及 flush/reset；[Kaldi 的 hann 窗](https://github.com/csukuangfj/kaldi-native-fbank/blob/master/kaldi-native-fbank/csrc/feature-window.cc) 使用 periodic 规则，不能用对称 `np.hanning` 替代。

Windows 原 SDK 与新路径在公开 WAV 的89,834个float32输出（含flush490）完全相同，PCM16全等；VAD281帧同决策；固定700ms silence/500ms pre-roll端点产生相同91,840samples及SHA，原PCM端点ASR与SDK/FFT降噪PCM的ASR分别相同。Windows候选1.294ms/帧、原SDK1.072ms，不能声称所有平台都加速。

ARM 新路径实际分段为 FFT0.2177ms / ORT13.8639ms / IFFT+OLA0.6143ms，其余约3.4ms为VAD与封装；新瓶颈主要在模型计算。1线程整帧平均18.1359ms，2线程反为20.3006ms/P9534.0295ms。相机PID1333连续计数、CPU频率仍1.333333GHz、温度sysfs为空未取得。没有通过调频、停相机、丢帧、放阈值或异步积压掩盖平均吞吐缺口；未接生产采集线程。

此前SDK分段对照：combined1/1均30.4033ms（GTCRN26.3130/VAD3.1033/转换0.6586/list0.3285），2/1均34.9328ms；GTCRN-only1线程均19.6711ms/P9532.8210，2线程24.3530ms/P9544.5049；VAD-only1线程均4.1375ms/P9511.2566，2线程4.9273ms/P9515.9661。SDK私有DFT没有单独公开计时口，报告中NumPy独立FFT微基准明确不是SDK真实FFT耗时；新路径的阶段数字才是其实际内核计时。

## 证据与现役基线

- [ARM 依赖与空间](evidence/20261030T122408840024Z-board_dependency_probe/result.json)
- [ASR 候选隔离准备](evidence/20261030T122806388750Z-board_stage_asr/result.json)
- [同模型 ARM ASR](evidence/20261030T122857998275Z-board_asr_probe/result.json)
- [ARM 控制器/SQLite/HTTP 合成烟测](evidence/20261030T123426002668Z-board_candidate_smoke/result.json)
- [同模型 ARM frontend](evidence/20261030T123900950829Z-board_frontend_probe/result.json)
- [Windows frontend 与现役 Pipeline 同样本比较](frontend_windows_public_result.json)
- [Windows FFT PCM/VAD/端点/ASR 等效性](gtcrn_fft_windows_result.json)
- [ARM FFT PCM/分段/CPU/决策实测](evidence/20261030T130034670747Z-board_gtcrn_fft_probe/result.json)
- [SDK combined线程对照](evidence/20261030T124707387349Z-board_frontend_profile/result.json)、[VAD-only线程对照](evidence/20261030T124848356687Z-board_frontend_profile/result.json)、[GTCRN-only与原ORT检查](evidence/20261030T125527705959Z-board_frontend_profile/result.json)

所有已执行 UART 操作均释放锁并恢复 echo。早期扩展只读探针因原 UART 3800 字节行限制在命令发送前退出，失败目录 `20261030T122310779081Z-board_dependency_probe` 保留；之后采用 hash-checked `/tmp` 小脚本分段并在执行后清理，不放宽传输长度或生产路径检查。

板端实际配置、pending 与 runtime 均为 `/home/root/aura-board-vision-20261030/06391079cfddb734-r3-ubuntu/...`，boot `605eaf50-c66a-4559-bfc9-5ae177e0f305`；验证时 UI supervisor 918139 / camera 1333，IDLE、playing=false、监听/麦克风/跟随关闭、机械 FAULT/null。没有切 boot/FDT/FPGA/VART、服务入口、相机或机械参数。

实板 `board/runtime/audio/channel_jobs.py` SHA `015e13d27db25819d002c4c87087802e02e8b65ac10119bf467635871b458822` 与 Windows 当前语音源码一致；`board/vision/ui_camera_service.py` SHA `8aa94461e6b505857a199d91a0d35c78364d4621e1c7894c0d2798706ac38a8f` 同样一致。实板 `tools/board_avatar_gtk.py` SHA `874f0075741b0794a6bed4ba8aab33dfd0280e57a899d63a38ffa70f76b3cda9`，与 Windows 源 `1dcb21b...` 不同；**必须以 fresh actual r3 部署树为切换基线，不能覆盖成 Windows 旧 GUI**。

最小集成接点是现役 `ChannelConversationJobs.work`、`_invalidate`、`acknowledge` 和 `board_avatar_gtk.py` 的 transcriber 构造处。相机结构化状态为 `GET http://127.0.0.1:8790/v1/ui/status`，仅筛选 `modules.camera`、`modules.vision`、`modules.target` 的新鲜可见性字段；图片/身份 ID/模板未导出。动画当前仍有 portrait RPC，最终切换需改为板端合成并独立验收帧率。

发布门槛仍包括：ASR/前端并发负载与实时预算、ECAPA 依赖及公开样本效果、板端身份权限接点、受容量约束上下文与空闲摘要、真实 27B/OmniVoice 接口、实际播放器完整 ACK、唯一写入者迁移及来源/权限/遗忘一致性。由根代理串行集成；候选通过不绕过这些门槛。

## 后续 jobs 作业桥候选

新增 `aura/board/runtime/audio/board_dialogue_jobs.py` 的 `BoardDialogueJobs` 与 `test_board_dialogue_jobs.py`，完整能力/缺口/接口见 [jobs_adapter_handoff.json](jobs_adapter_handoff.json)。本阶段没有新的 ARM、GPU、真实 socket、GUI、portrait/人物素材或生产配置操作。

该桥保留 submit/latest waiting/_invalidate/poll/acknowledge/close 形状，以既有 `aura-channel-1` 顺序交付 start/transcript/text/control/audio/end 和 network_complete；24k mono PCM16 每包480samples。真实 OmniVoice RAM 原件已由模型代理只读确认是24k，设备sink的48k stereo不改变源PCM或receipt含义。口型通用契约仅从 `output.position()` 的秒数计算 `round(seconds*24000)`，boot/session/generation/request/capture/token变化使旧显示和ACK失效。

完整播放ACK由原玩家完成回调交回板端Store，核对原token/hash/samples；没有 Windows `/played`。普通聊天、显式记忆与历史入口通过板端 controller/policy；raw ASR 保留，称呼理解只在 root builder/明确命令解析的窄边界处理。新历史API将主题传给 `search`，不误作精确分区 `topic`。profile下“新对话”因当前Store尚无独立会话recent分区而明确拒绝，不假装只换CID即可清空上下文。未接上的身份/声纹/视觉进入、profile授权、复杂思考、历史删除确认、barge factory和提示音流程均明示未就绪，不回退Windows旧业务接口。

根代理授权的窄controller扩展为 `prepare_text/prepare_pcm(..., cancel_event=None)`；每个job共享自身Event，登记前后都检查，取消发生在scope解析/登记之前仍不能启动模型。未收到模型响应时，即使Event已set也幂等请求远端cancel。已删除5秒轮询方案；Store/网络清理只在独立有界队列上做，UI无等待或SQLite写入。确定性真实Controller+合成Store屏障和阻塞mock传输测试均已通过。

最后实际运行的 jobs/controller/client 纯mock/SQLite子集是 **63 passed / 0.51s**，发生在人物线程允许的 PREPARATION 阶段。随后新增 `search` 转发和 `jobs.idle`/ASR前抢占源代码及对应测试；PAIRED_AB_ARMING_PILOT开始后没有再启动测试，最终回归由根代理在人物窗口明确释放后统一执行。不能把新源码写入称为新API回归已通过。

最小factory应以实际r3 GUI为基线，只替换候选transcriber构造接点；既有录音/StreamingController/播放器和完整完成回调保留。示例接口如下，代码不会自行应用：

```python
jobs = BoardDialogueJobs(
    controller, settings, board_boot_id,
    asr=board_asr, conversation_path=board_selection_path,
    wall_clock=timeline.event_time,
    playback_invalidator=invalidate_current_render_owner,
    start_worker=False,
)
memory_idle = lambda: jobs.idle and controller.idle and timeline.safe_for_compaction
```

正式启用前必须显式接完当前活跃模式的board handlers、可信时钟和barge capture factory，不能宣称全量drop-in。该桥将完整 `PlaybackPlan` 分包给玩家，不等于旧增量LLM→分句TTS重叠流水线或原首PCM延迟已经保留。对应候选源码/待跑命令由handoff JSON冻结；现役录音文件也与Windows树不同，已用实板pin匹配 `listening_bounce/board_source` 的 `a194a026...` 原字节核对8帧/6ms队列消费及wake事件，但没有用旧目录覆盖现役。
