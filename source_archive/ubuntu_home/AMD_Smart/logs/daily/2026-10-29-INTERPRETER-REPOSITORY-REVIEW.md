# 用户指定simultaneous-interpreter仓库核查

固定main7bcfaac8339a3edf1b58ce4b26853cda85b24fd1，审查21份相关文档/代码及小型清单，均Git blob SHA匹配commit tree，无模型权重下载、执行仓库代码、构建或板测。网页子文件缓存未命中后改用GitHub API/固定commit raw获取；来源和阅读范围可复查。

结论：Zynq7010裸机项目的MFCC＋小CNN确有HLS/RTL实现；Qwen2.5-0.5B Q6在ARM上跑，文档新句22–24秒级。TTS/ASR仍云端，cloud_client发文字并收PCM，speech_playback只处理播放，不是本地TTS模型。它不能证明当前OmniVoice16能直接迁板，也不直接解决AURA当前3.6–3.9秒起答。

参考价值：按真实到包轨迹回放对照播放策略；限制每次网络处理以给采音/播放服务；后续独立语音特征硬件研究。其1.28/2秒缓冲、ESP串口和Opus优化不能直接套用有线AURA。声纹公开英文20身份分类79%/未知误接纳5.25%等为作者报告，非本次复测和中文真人验收；73ms CNN运算不含音频窗口及平滑。

用户仍不加新功能，本轮只读审查并保存项目参考，不更换模型/音色/FPGA或启用新声纹。报告及固定来源：[共享核查](/home/ghmd/Win共享文件/协作任务/2026-10-29_语音延迟修复/参考项目_simultaneous_interpreter核查.md)。本地/home/ghmd/aura-interpreter-review-20261029/保留精确源码与manifest，未代填Windows回执。
