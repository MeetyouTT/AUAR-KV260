<!-- aura-architecture-generated -->
# 标定 / 独立测试 / 黄金参考

模块：M8 / `datasets`；负责人：B / C；目标位置：数据与开发机。

当前证据层级：**接口或部分实现**。

输入：真实场景 / 独立标注 / 版本。
输出：分离数据集 / 参考输出。

现有源码/证据来源：

- `data/golden/framework_frames.jsonl`
- `data/calibration_manifest.json`
- `data/test_manifest.json`

待补：合成小样已有；真人视频、身份/ASD/语音与标注集待采集。

关联内部验收：T03、T04、T15、T16、T17、T21。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。

<!-- aura-structure-details -->
## 复核后的目录职责

主责：A/B/C；运行/使用位置：黄金参考。

内容：CPU/浮点参考、合成 fixture 和预期输出。

边界：每项带适用算法/版本；合成演示与真实样本分别标记。

依据：O1、C13，见 report/structure_detail.md 的依据登记。

现有来源：

- `data/golden`

目标目录已建立；本轮没有将实际源文件迁移到此处。
