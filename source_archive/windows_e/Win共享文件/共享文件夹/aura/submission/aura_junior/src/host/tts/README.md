<!-- aura-architecture-generated -->
# 汐蓝选定声线：Qwen3-TTS

模块：M6 / `tts`；负责人：C；目标位置：Windows 模型主机。

当前证据层级：**已有 PC 成果**。

输入：回答文本 / 已选声线。
输出：明确格式 PCM。

现有源码/证据来源：

- `tools/selected_voice_service.py`
- `board/runtime/audio/selected_voice.py`

待补：Windows 声线/音强口型已有记录；真实管线和 KV260 播放待接。

关联内部验收：T18、T19。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。

<!-- aura-structure-details -->
## 复核后的目录职责

主责：C；运行/使用位置：Windows 模型主机。

内容：选定 Qwen3-TTS 声线、文本到真实音频。

边界：当前服务有演示/UI 耦合；迁移时保留声线原件并提取纯合成适配。

依据：P2、C5、C7，见 report/structure_detail.md 的依据登记。

现有来源：

- `board/runtime/audio/selected_voice.py`
- `tools/selected_voice_service.py`

目标目录已建立；本轮没有将实际源文件迁移到此处。
