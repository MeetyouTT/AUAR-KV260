# 本地大模型与 KV260 语音接入

日期：2026-10-18。Windows `192.168.50.1`，KV260 `192.168.50.2`，有线 `/24`，原 Wi-Fi 保留。

## 最新实录播报已通过

用户亲自操作板端录音5秒／80000样本，说“你好，我今天有点累，陪我聊两句”，识别返回“你好我今天有点累陪我聊两句”。Qwen3回答“嗯～累就躺着吧，我陪你聊点轻松的～”，OmniVoice16生成3.07秒新音频，并由板端实际播放。用户明确反馈：“已经听到自动回答”。

从板端录音完成后的软件提交到实际开口 **1.609秒**；不包含用户录音的5秒，也不等于按键到声学输出的外部仪器测量。ASR156ms、LLM359ms、TTS约610ms；25个实际播放采样中23个检测到非零口型，音频时钟推进，播完回到IDLE，无错误。新录音capture与转写归属一致，WAV的SHA与真实生成记录一致；本次对应生成记录 `cache_hit=false`、生成约0.607秒，确认不是复用已有回复。相机PID976及原boot保持，真实截图已查看。

证据：`live_turn_verification.json`、`user_confirmed_board_state.json`、`live_acceptance.json`、`board_live_voice.png`、`verification_summary.json`；对应语音在 `model_host/audio/2fae40dc8d26ec611e34caa3bb2714ca3fb82e46ce45f7b33e4544ea534174cb.wav`。这是单轮实录播报通过；本轮未把多轮长期稳定、真实播放中取消、冷启动或整机验收算作已完成。

成功实录后的源码、配置和证据另存 `board_dialogue_live_verified_source.zip`，指纹清单为 `live_source_snapshot.json`；早先未完成实录的 `board_dialogue_source.zip` 保留历史，不作为最新结果。归档包含生成回复WAV及公开授权脚本，未包含SSH私钥或模型权重。

## 当前链路

板端 MCP01 按键录音 → 电脑 Paraformer → Qwen3 4B 快速多轮回答 → 已接受的 OmniVoice 16 步 → 板端校验并下载 WAV → 原 GStreamer/MCP01 播放及音频样本时钟口型。手动停止一句，尚无自动 VAD 或全双工。

`8791` 保留已通的纯 ASR 服务；`8792` 为明确区分的完整语音服务。两者只监听本机有线地址。板卡已实际成功读取两个健康接口；本轮管理员防火墙窗口被取消，未添加新规则，未关闭防火墙。不能把脚本存在视作规则已安装。

## 已有证据

- `live_asr_verification.json`：用户操作的新录音，9.5 秒／152000 样本，返回实际 Paraformer 转写约250ms，capture归属一致。建议台词中的“汐蓝/蓝鲸”与实际返回“西南/南京”不同；原始发声未人工裁定，不能称作专名识别正确。
- `host_chain_verification.json`：历史真实 MCP01 WAV→真实 ASR/Qwen/OmniVoice 的电脑端测试。首轮模型回复47.231秒含冷启动，不作为稳定响应时间。
- `http_voice_verification.json`：相同历史音频通过完整模型 HTTP 接口，耗时1.297秒，WAV格式／长度／SHA256校验通过。
- `board_client_probe.json`：已部署板端客户端实际访问电脑模型、取回 WAV 并导入口型播放任务，1.669秒；这个探针未实际录新音或播放。
- `voice_regression.log`：30项软件测试通过，覆盖音频哈希/格式、16步与模型身份、旧板端缓存类兼容、错归属、取消丢弃、ASR独立模式、完整HTTP及录音互斥。fixture测试不当作真实模型证据。
- `active_release_verification.json`：7份运行源码、58项启动组件核对通过，界面active，相机PID976保持。
- `live_turn_verification.json`：最后一轮用户新录音、模型回答、实际播放时钟及口型采样；若尚未出现该文件，或状态不是PASS，不能称作本轮完整实录播报已验收。对应截图 `board_live_voice.png` 和用户听音反馈另外保存。

首次180秒采样窗口没有收到新录音，当时结果为 `WAITING_FOR_USER_RECORDING`，原状态保存在 `final_board_state.json`；这是此前验证时点。随后恢复后台模型并完成新录音自动回答，以上方“最新实录播报已通过”及最新证据为准。底栏仍沿用统一相机服务的主机能力标签，独立语音的实际状态以交流页及本目录证据为准，统一能力状态后续仍需收拢。

上述耗时均为本机小样本，历史探针可能复用生成音频；板端兼容字段 `cache_hit` 不用于证明TTS重新合成。真实新录音的开口时间以最后实测为准，不用探针数字承诺稳定性能。

## 启动与接手

Ollama已安装 `qwen3:4b-instruct-2507-q4_K_M`；语音继续采用共享 `aura/models/tts/OmniVoice/` 固定revision和“柔亮俏皮”完整参考。16步、seed8701、float16/SDPA及全部已接受参数保留。真实失败显示错误，不返回mock台词；当前没有VLM看图回答。

在项目根执行（重启Windows后需要重新启动这些进程）：

```powershell
& .\deliverables\2026-10-18_board_dialogue\start_background_models.ps1
```

启动器仅启动缺失服务，兼容健康服务会复用；模型预热通过才报告READY。后台进程和日志在本目录记录，没有新增计划任务或Windows开机服务。Ollama仍沿用现有安装及服务配置。

后续复查发现，上一轮直接从工具终端启动的两个模型服务已退出，具体退出原因未由原日志确定。现新增 `start_background_models.ps1`，用隐藏WMI独立父进程调用 `launch_models.py`，降低与终端生命周期绑定的风险；本机复启后真实ASR和完整语音预热通过。该脚本从原stage_config读取语音Python路径，换主机需先核对路径，也可在独立终端显式运行底层 `launch_models.py --voice-python '<实际环境>'`。这不是Windows开机自启，持续运行能力还需后续观察。

板端实际运行目录：`/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009`。

当前独立启动目录：`/home/root/aura-ui-startup-20261009/releases/voice-b980a9dd2ebb917a-r2`，`aura-avatar-ui.service` 指向该目录。最后生效源码以 `board_deployment.json`、兼容修复记录及 `active_release_verification.json` 为准；复制回本地的真实配置/启动器/单元在 `active_board_release/`。原10-17启动目录未覆盖。

完整对话配置为运行目录根的 `avatar_conversation_settings.json`：enabled=true、host=192.168.50.1、port=8792、timeout_ms=120000。原 `avatar_transcription_settings.json` 的纯ASR配置保留。禁用完整对话并重启玩偶界面可回到原ASR入口；首次切换应先确认没有录音或播放任务。

板端仅消费经过时长/格式/哈希检查的24kHz单声道PCM16 WAV，不加载CUDA模型。下载缓存按WAV内容SHA命名，与旧Qwen和PC合成身份缓存分离。沿用原FSM、音频时钟和待机/口型，不新增身体动态。

## 取消、版本与访问边界

现有boot/session/request/generation/capture/sample/hash字段原样校验；重录、取消和过期结果不会重新启动音频。后台最多一个在途请求和一条最新待发录音，界面线程不等待网络。主机按boot/session保留最近四轮；界面重启生成新session，记忆重新开始。模型推理无法即时中断，已开始的计算可以结束，但旧结果在板端丢弃。

本轮只重启玩偶界面，保留相机与DPU服务、网络、机械运动和FPGA配置。首轮预检因SSH PATH缺少`/sbin`自动回退；随后使用正确预检环境。旧板缓存类缺少normalizer接口已加兼容并有专项测试。所有部署前源文件、旧单元及配置在 `/home/root/aura-voice-dialogue-20261018/` 的对应发布备份目录中，首轮回退记录也保留。

板卡root已追加本机公钥，原密钥保留。私钥在本机Codex工作目录，未写入共享项目；`board_access.pub`与授权脚本只有公钥。其他主机需生成自己的密钥并由用户授权，不复制本机私钥。

单模块通过不表示板端身份、视觉说话人、机械随动、全量统一框架、冷启动或长稳完成。当前板卡墙钟与真实日期不符；协议使用各机相对时长和boot/session归属，不用两机绝对时钟判断过期。
