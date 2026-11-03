# 汐蓝：OmniVoice 16 步麦克风实时对话

**2026-10-11 用户已确认当前语音效果合格，作为后续工作基线保存。** 其他主机先读 `../2026-10-11_voice_accepted/HANDOVER.md`。完整语音／对话模型已保存到共享项目，源码、配置、参考和验证记录另有冻结包及 SHA256 清单；先等同步完成，再重建该机环境。以下速度与测试记录保留原始口径，语音主观验收状态以本段及 `acceptance.json` 为准。

用户已选择 16 步，并要求通过真实大语言模型连续聊天检验活人感。本入口为本机实际运行链路：浏览器麦克风 → 16kHz PCM16 → sherpa-onnx 中文 ASR → Ollama Qwen3 4B Instruct Q4_K_M 多轮对话 → OmniVoice 16 步 → Qt 音频设备与现有玩偶动画。

## 2026-10-11 实时提速结果（当前默认）

默认对话模型已改为官方 `qwen3:4b-instruct-2507-q4_K_M`，文件约 2.50GB，驻留 GPU 约 2.73GB，实测上下文 2048。新增 `--fast`：精简汐蓝口语提示、最多 120 输出 token、通常一两句不超过 48 字、JSON Schema 约束、关闭思考、保留最近四轮、30 分钟驻留、启动前预热。对话回复直接开口，avatar_action 为空；直接台词面板的手动动作保留。模型／环境冷启动仍需等页面显示就绪。

真实计算预热修正后，录音夹具 ASR→模型→新语音→实际设备开口两轮实测 **1.250s／1.094s**；另两轮文字对话完整开口 **1.594s／1.031s**，两轮均未命中语音缓存，并正确记住新名字“月光鲸”。旧配置同一录音链路 **28.437s／16.984s** 保留在 `chain_verification_original.json`，14B 快速配置 **3.969s／3.031s** 在 `chain_verification_fast14b.json`。小样本、台词长度、负载和模型均有变化，不能当作固定响应承诺；录音时间不包含在这些数值内。

同提示三轮对比：4B 预热后模型回复约 0.65s，14B 快速配置约 1.4s；本机另一个 3B 虽约 0.5s，却错误记忆“蓝鲸”，未采用。4B 通过两组专名记忆检查，但它在另一轮追问中把自己的话当作用户的话，并随口提到未知天气，说明复杂理解和事实可靠性仍有不足；速度通过不代表整体对话质量优于 14B。可用 `launch.py --llm-model huihui_ai/qwen3-abliterated:14b` 回到 14B 快速配置（需先停止现有本任务主机）。

验收文件：`chain_verification.json`、`warm_turns_verification.json`、`fast4b_benchmark.json`、`fast14b_benchmark.json`、`local3b_benchmark.json`、`fast4b_host.log`；26 项相关回归通过，见 `regression_fast.log`。连接失败会关闭旧连接，下次发送可重新连接。

官方依据：[4B Q4_K_M 模型](https://ollama.com/library/qwen3:4b-instruct-2507-q4_K_M)、[Ollama Chat API 的结构化输出、驻留与计时字段](https://docs.ollama.com/api/chat)。原 14B 模型保留，旧配置记录以下作为历史。

## 开聊

本机入口：http://127.0.0.1:8775/ 。声音与识别就绪后，按住“按住说话”、说完松开。首次需允许页面使用麦克风；如果在授权过程中已经松开，授权后再按一次。每段 0.2–20 秒。建议耳机减少回声，页面“打断”可立即停止播放；后台识别或模型的迟到结果不会重新启动被取消的语音。可用文字输入作对照。

这是按键结束一句的轮次对话，尚未实现自动语音活动结束判定或全双工抢话。界面通过浏览器使用，Qt 在后台保留真实音频设备和音频样本时钟口型。说话仍复用现有待机动画，不增加身体动态。

## 初版历史验证与限制（速度已被上方提速记录更新）

- 同一 WebSocket 连接的两轮真实模型测试：先告知“小实验叫蓝鲸”，再追问名字，模型正确接住上文。首轮模型加载约 63.91 秒，后一轮模型回复约 3.12 秒，仅为这两轮记录。
- 另用已生成的录音夹具经实际 ASR、真实 Ollama、16 步合成与实际 Qt 设备播放：首轮从提交到开口约 28.44 秒，追问约 16.98 秒，播放中打断通过。证据：`chain_verification.json`、`latest_verification.json` 和 `evidence/`。这些实测包含 ASR／模型／语音／动作／设备准备，不含用户录音时间，也不是板端性能。负载变化明显，不能承诺固定响应时间；检查时 GPU 已用约 15.1/16.3GB。
- 自动化记录仅覆盖录音夹具，不能替代物理麦克风测试。用户随后已确认当前语音效果合格，见本页顶部验收记录。
- 引擎隔离、全角标点传递、真实模型失败不回落固定回复、音频时钟／取消／暂停等相关回归共 25 项通过。测试环境退出时出现 pyreadline3 析构警告，测试退出码 0；未更改旧 Qwen 环境。

## 实现与边界

固定“柔亮俏皮”完整参考及其准确转写，OmniVoice 官方模型 revision `c5fdb5ccb189668d56333f77ba2629f4cd7535f4`，参数与试听相同：16 步、speed 1.0、guidance_scale 2.0、float16、SDPA、seed 8701。驻留子进程在开聊前加载并预热，缓存身份包含引擎、模型、参考、文本和参数。缓存独立在本目录 `cache/`，不会复用旧 Qwen 缓存。全角标点从 LLM 到 OmniVoice 保留，旧 Qwen 的历史归一化及缓存键不变。

对话模型采用现有汐蓝人设与最近 4 轮记忆；模型失败明确断开并报错，不用固定 mock 台词冒充实际回复。记忆在主机进程中按连接保存，断线重新连接时重新开始。麦克风波形仅在当前本机识别，不保存原始录音；识别文本、回复、生成语音和验收日志会保存在本共享目录。

## 启动与多机接手

本机双击 `run_dialogue.bat`，依赖已有 Ollama 服务与 `qwen3:4b-instruct-2507-q4_K_M` 模型。完整模型现已保存到项目内，无需其他机器重新下载；先按 `../2026-10-11_voice_accepted/HANDOVER.md` 导入 Ollama 权重。默认 OmniVoice 路径为 `${PROJECT_ROOT}/aura/models/tts/OmniVoice`，随项目目录解析。`stage_config.json` 的语音 Python 仍是原机器示例；其他机器必须重建环境并覆盖 Python 路径，可运行：

```powershell
& '<Python>' -B '.\launch.py' --ui-python '<有 PySide6/numpy/Pillow 的 Python>' --voice-python '<有 OmniVoice/CUDA/sherpa-onnx 的 Python>' --model-path '<完整 OmniVoice 目录>'
```

启动器把机器覆盖项写到本目录 `machine_config.json`；共享同步后仍要按当前机器核对路径。端口 8766 是独立真实对话主机，8775 是独占本机浏览器入口。已有端口会复用；若切换模型或机器参数，需要先停止对应本任务后台进程，再重启。原 8773 演示、已接受的声线、旧 Qwen 缓存与剧本保留。

OmniVoice 代码 Apache-2.0，权重 CC-BY-NC，授权记录见前一轮试听 README。
