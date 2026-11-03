# simultaneous-interpreter：与AURA语音链路的对应关系

日期：2026-10-29。用户指定仓库：https://github.com/HHHHH-UX-bot/simultaneous-interpreter 。只读审查固定main提交 `7bcfaac8339a3edf1b58ce4b26853cda85b24fd1`（提交时间2026-10-27T10:25:57Z）。获取21份相关源码/文档/小型清单，与该commit tree逐项Git blob SHA核对一致。未克隆模型、下载权重、执行仓库代码、构建、上板或修改AURA业务。

## 实际架构与证据等级

| 功能 | 仓库实现位置 | 能认定的范围 |
| --- | --- | --- |
| 字幕、触摸、音频收放 | Zynq-7010裸机，CPU0界面/业务、CPU1 USB触摸，PL音频/显示 | 源码与公开文档含对应实现及作者实板记录；本次未复测 |
| 语音识别 | 普通翻译与本地LLM模式都使用云端ASR | 不能称整条离线语音链 |
| 文字转语音 | 普通模式LiveTranslate云端返回音频，本地LLM模式由cloud_client_tts_text/commit发往云端 | 板端speech_playback是PCM队列/增益/重采样/物理FIFO，不是本地TTS神经网络 |
| 板上小LLM | tinyqwen.c：Qwen2.5-0.5B-Instruct，Q6大矩阵、Q8向量，ARM NEON，512token上下文 | 源码有真实解码器和量化矩阵计算。文档报告约401.6MB权重与新句22–24秒级完成，非FPGA加速LLM、非实时同传，不可外推27B |
| FPGA声纹 | HLS MFCC＋三层int8 CNN，AXI/BRAM装载，ARM匹配四登记位 | 有实际HLS C++和导出RTL。作者报告公开PCM数值板测对应，但其完整output原始工件未随Git上传，本轮不能独立复算全部实测 |

## 与当前文字转语音问题最相关的结论

这个仓库没有提供把OmniVoice或同等音色TTS整网在FPGA/ARM上运行的完成证据。TTS_SETTINGS明确云端生成24kHz PCM，cloud_client.c有input_text_buffer.append/commit和云端会话，speech_playback.c只消费已合成采样。它支持“板卡独立联网请求语音服务”，不支持“文字转语音已在板上计算”的解读。

本地声纹模型规模很小，不能等同ECAPA迁板。作者独立公开英文干净语料测试给出20身份分类79%、四登记位未知查询误接纳5.25%、已知查询拒绝25%；真人中文/噪声没有相同证据。MFCC约0.37ms/帧、CNN约73.25ms/窗口是50MHz计算用时，输入仍需约1.28秒音频窗口和运行时平滑，不是从开口到识别只需73ms。

## AURA可参考的部分

1. **播放按实际到包时序验证。** 对方在同一45段到包回放中报告等待中位1713→1387ms、0欠载；这个对照思路可用于AURA接收/播放候选。对方为ESP8266/Wi-Fi/UART链路，用1.28/2秒储备，320/640ms档曾欠载；不直接套用其秒级缓冲到当前有线、常驻ALSA、20ms包的AURA链路，更不把该326ms直接当AURA收益。
2. **连续采音与有界分工。** 限制单次TLS处理、上传和FIFO搬运的工作量，避免某段循环长时间饿死采音与播放。对方具体CIPSEND/IPD/波特率修复针对其ESP链路，不是AURA已有以太网瓶颈证据。
3. **语音FPGA候选只作后续参考。** MFCC、定点Mel和小CNN可用作独立研究参考；AURA的USB音频需要PS/DMA→PL接口，与对方I2S直接分叉不同。迁往KV260需要适配工具版本、AXI、采样/量化定义、驱动及和现DPU联合资源/时序，现有DPU不会自动执行其任意RTL。用户当前不加新功能，本次不安排新增声纹硬件或换板/换工具链。
4. **本地小LLM优先服务独立性而非当前提速。** 对方新句22–24秒的特定小模型成绩无法与AURA原27B暖态3.6–3.9秒起答直接作加速比：模型能力、输出、计时和硬件不同。AURA当前继续Windows原27B/TTS优化。

## 精确来源

- [README](https://github.com/HHHHH-UX-bot/simultaneous-interpreter/blob/7bcfaac8339a3edf1b58ce4b26853cda85b24fd1/README.md)、[NOW](https://github.com/HHHHH-UX-bot/simultaneous-interpreter/blob/7bcfaac8339a3edf1b58ce4b26853cda85b24fd1/docs/context/NOW.md)。NOW的10月27日SD后台加载更新优先于10月23日文档的旧JTAG/断电描述。
- [TTS_SETTINGS](https://github.com/HHHHH-UX-bot/simultaneous-interpreter/blob/7bcfaac8339a3edf1b58ce4b26853cda85b24fd1/docs/design/TTS_SETTINGS.md)、[cloud_client.c](https://github.com/HHHHH-UX-bot/simultaneous-interpreter/blob/7bcfaac8339a3edf1b58ce4b26853cda85b24fd1/software/network_ui/cloud_client.c)、[speech_playback.c](https://github.com/HHHHH-UX-bot/simultaneous-interpreter/blob/7bcfaac8339a3edf1b58ce4b26853cda85b24fd1/software/network_ui/speech_playback.c)。
- [BOARD_LLM](https://github.com/HHHHH-UX-bot/simultaneous-interpreter/blob/7bcfaac8339a3edf1b58ce4b26853cda85b24fd1/docs/design/BOARD_LLM.md)、[LOCAL_VOICE_LLM](https://github.com/HHHHH-UX-bot/simultaneous-interpreter/blob/7bcfaac8339a3edf1b58ce4b26853cda85b24fd1/docs/design/LOCAL_VOICE_LLM.md)、[tinyqwen.c](https://github.com/HHHHH-UX-bot/simultaneous-interpreter/blob/7bcfaac8339a3edf1b58ce4b26853cda85b24fd1/software/network_ui/tinyqwen.c)。
- [LOCAL_SPEAKER_CNN](https://github.com/HHHHH-UX-bot/simultaneous-interpreter/blob/7bcfaac8339a3edf1b58ce4b26853cda85b24fd1/docs/design/LOCAL_SPEAKER_CNN.md)、[CNN HLS](https://github.com/HHHHH-UX-bot/simultaneous-interpreter/blob/7bcfaac8339a3edf1b58ce4b26853cda85b24fd1/software/speaker_cnn/speaker_cnn.cpp)、[MFCC HLS](https://github.com/HHHHH-UX-bot/simultaneous-interpreter/blob/7bcfaac8339a3edf1b58ce4b26853cda85b24fd1/software/speaker_cnn/speaker_mfcc.cpp)。
- [早期播放对照](https://github.com/HHHHH-UX-bot/simultaneous-interpreter/blob/7bcfaac8339a3edf1b58ce4b26853cda85b24fd1/docs/validation/tts-latency-20261021/README.md)、[较新长句验证及保留失败](https://github.com/HHHHH-UX-bot/simultaneous-interpreter/blob/7bcfaac8339a3edf1b58ce4b26853cda85b24fd1/docs/validation/long-speech-20261022/README.md)。

本次源指纹见evidence/interpreter-source-manifest.json；只保存阅读范围，不将文档实测转写为本次复现通过。无对外联系或生产操作。
