<!-- aura-architecture-generated -->
# src/ps/audio

<!-- aura-structure-details -->
## 复核后的目录职责

主责：C；A 解决驱动/USB；运行/使用位置：KV260 PS。

内容：MCP01 唯一采录/播放、样本时间、真实停声与半双工。

边界：模型合成与设备播放分层；旧 tts.py 混合职责需拆分。

依据：P2、C5，见 report/structure_detail.md 的依据登记。

现有来源：

- `board/runtime/audio/tts.py`

目标目录已建立；本轮没有将实际源文件迁移到此处。
