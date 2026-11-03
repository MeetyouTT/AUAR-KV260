<!-- aura-architecture-generated -->
# 当前图 VLM / 对话与人设

模块：M6 / `vlm`；负责人：C；目标位置：Windows 模型主机。

当前证据层级：**接口或部分实现**。

输入：当前图 / 提问 / 允许上下文。
输出：有依据回答 / 情绪与动作建议。

现有源码/证据来源：

- `tools/dialogue_host_ollama.py`
- `board/runtime/character.py`
- `host/model_service/pipeline.py`

待补：汐蓝人设与文字接口已有；真实看图模型与整机证据待验。

关联内部验收：T17、T24。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。

<!-- aura-structure-details -->
## 复核后的目录职责

主责：C；运行/使用位置：Windows 模型主机。

内容：本轮图像问答、角色与对话上下文。

边界：只消费有来源的图像；自然语言输出没有运动执行权限。

依据：P2、C6，见 report/structure_detail.md 的依据登记。

现有来源：

- `tools/dialogue_host_ollama.py`
- `board/runtime/character.py`

目标目录已建立；本轮没有将实际源文件迁移到此处。
