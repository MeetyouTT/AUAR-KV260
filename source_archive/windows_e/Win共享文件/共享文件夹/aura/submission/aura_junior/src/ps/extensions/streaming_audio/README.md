<!-- aura-architecture-generated -->
# 可选：KWS / VAD / AEC / 流式全双工

模块：EXT / `audio_ext`；负责人：C 后续；目标位置：PS + Windows。

当前证据层级：**接口或部分实现**。

输入：真实音频 / 自播音 / 取消。
输出：语音唤醒或流式交互。

现有源码/证据来源：

- `board/runtime/audio/kws.py`
- `board/runtime/audio/vad.py`

待补：旧 KWS/VAD 代码已有；本期先按键半双工，AEC/全双工待评估。

关联内部验收：后续扩展单独定义。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。
