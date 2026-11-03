<!-- aura-architecture-generated -->
# src/ps/motion

<!-- aura-structure-details -->
## 复核后的目录职责

主责：B；A 提供驱动和 ABI；运行/使用位置：KV260 PS。

内容：唯一运动服务、命令校验与硬件访问适配。

边界：正式模式只有运动服务提交；软件模拟监督属于可执行适配，仿真目录保存测试。

依据：P2、C2、C8，见 report/structure_detail.md 的依据登记。

现有来源：

- `board/motion`

目标目录已建立；本轮没有将实际源文件迁移到此处。
