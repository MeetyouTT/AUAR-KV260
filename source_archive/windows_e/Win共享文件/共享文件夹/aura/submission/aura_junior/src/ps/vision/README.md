<!-- aura-architecture-generated -->
# src/ps/vision

<!-- aura-structure-details -->
## 复核后的目录职责

主责：B；运行/使用位置：KV260 PS + DPU 调用。

内容：唯一相机、检测前后处理、跟踪、快照与脸片段。

边界：人体检测、CPU 人脸参考、跟踪预测分别标明；不拥有身份库/运动寄存器。

依据：P2、C2，见 report/structure_detail.md 的依据登记。

现有来源：

- `board/vision`

目标目录已建立；本轮没有将实际源文件迁移到此处。
