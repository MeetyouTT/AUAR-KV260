# 板端开头丢字修复（2026-10-18）

状态：正式补丁已上板，用户实录对话反馈“开头完整清楚”。此前原始WAV清晰、板端开头含糊；进一步对照确认同一声流连续播两遍时第一遍缺开头、第二遍完整，支持输出冷启动路径导致起音受影响。未对MCP01内部功放/DSP进行仪器测量，不将具体内部机制写成已证实。

## 对照与修复

- 板端下载WAV的SHA256与主机相同。MCP01实际支持48kHz双声道PCM16；原24kHz单声道离线转换后左右相同，回抽样相关性0.999206，RMS增益0.999747。
- 增加300ms静音未有明确改善；500ms重播后用户反馈“第一个字听不清”；1000ms反馈“完整清楚”。
- 正式 `aura/tools/gstreamer_audio_engine.py` 每次播放前验证原文件SHA，临时WAV前置1秒零样本，后续原始PCM逐样本保留。原模型输出、缓存、参考声线和16步参数均不修改。
- 音频内容时钟扣除1秒预启动，预启动期间ready=false、口型保持关闭；暂停/恢复保留同一音频流，取消、EOS和错误都释放设备并清理临时文件。

该方案使实际开口比原链路增加约1秒。修复后两轮软件提交至语音内容启动约2.479/2.573秒，仅为本机小样本。进一步缩短预启动须重新做起音听音对照，不能仅按软件EOS判定可用。

## 验证

本机14项播放器测试通过；在板端独立候选目录再运行同样14项，也全部通过。包含原始PCM保持、1秒前置的内容时钟、暂停、取消、过期代次、EOS和临时文件回收。启动器60项组件SHA核验通过，正式UI已恢复active；相机PID976保持，板卡未重启。

正式实录后观察到33个播放采样、26个非零口型采样，录音capture归属一致；12个启动阶段采样均未提前标为播放、口型保持关闭。对应新WAV SHA在主机再次核对。用户明确反馈“开头完整清楚”。不扩大为长期多轮、真实打断、物理声学仪器或冷启动验收。

## 证据与回退

- `acceptance.json`：最新验收和限制。
- `fixed_live_turn.json`：正式实录、实际音频时钟、口型与capture。
- `startup_fix_deployment.json`、`active_release_verification.json`：实际部署与全部启动组件核验。
- `playback_tests.log`：本机14项；部署JSON中保留板端14项测试输出。
- `board_playback_ab.json`、`continuous_output_probe.json`、`silent_1000ms_probe.json`、`conversion_diagnosis.json`、`alsa_direct.json`：同PCM对照与数据检查。
- 板端部署前源码、测试、启动配置及设置备份：`/home/root/aura-audio-clarity-20261018/startup-fix-db81c4e510eb/`。回退前确认空闲，恢复其engine/test/config并重启 `aura-avatar-ui.service`；相机服务保持。

更早的 `initial_diagnosis.json` 为初步候选，不再据此归因为TTS。`probe_board_playback.py` 的300ms探针会使用当前播放器；若复现实验，必须显式关闭正式播放器默认1秒前置，或直接播放保存的原始ALSA对照文件，避免叠加静音。
