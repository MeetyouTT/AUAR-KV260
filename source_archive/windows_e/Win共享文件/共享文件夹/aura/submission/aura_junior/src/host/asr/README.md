<!-- aura-architecture-generated -->
# 常驻中文 ASR / 准备探针

模块：M6 / `asr`；负责人：C；目标位置：Windows 模型主机。

当前证据层级：**接口或部分实现**。

输入：真实 PCM。
输出：中文转写与阶段耗时。

现有源码/证据来源：

- `board/runtime/audio/asr.py`
- `host/model_service/backends.py`

待补：旧后端代码与 fixture 已有；当前项目真实输入的模型验收待做。

关联内部验收：T16、T18。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。

<!-- aura-structure-details -->
## 复核后的目录职责

主责：C；运行/使用位置：Windows 模型主机。

内容：中文识别后端与准备/失败报告。

边界：旧 board/runtime/audio/asr.py 是候选实现来源，最终服务接入待验。

依据：P2、C5，见 report/structure_detail.md 的依据登记。

现有来源：

- `board/runtime/audio/asr.py`
- `host/model_service/backends.py`

目标目录已建立；本轮没有将实际源文件迁移到此处。
