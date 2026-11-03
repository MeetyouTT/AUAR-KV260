<!-- aura-architecture-generated -->
# Vitis AI 模型锁 / 校准 / 编译

模块：M8 / `model_build`；负责人：B；目标位置：Ubuntu 模型构建环境。

当前证据层级：**接口或部分实现**。

输入：来源权重 / arch / 校准集。
输出：xmodel / 模型卡 / 精度对照。

现有源码/证据来源：

- `config/model_manifest.json`

待补：项目检测和身份最终工件未冻结；不拿 ResNet18 当人体结果。

关联内部验收：T03、T04。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。

<!-- aura-structure-details -->
## 复核后的目录职责

主责：B；C 模型环境；运行/使用位置：Ubuntu/模型环境。

内容：权重校验、校准、量化、DPU 编译与比较。

边界：记录输入/工具/arch/hash；不能拿分类参考替代项目人体/身份模型。

依据：P1、P2，见 report/structure_detail.md 的依据登记。

现有来源：

- `config/model_manifest.json`

目标目录已建立；本轮没有将实际源文件迁移到此处。
