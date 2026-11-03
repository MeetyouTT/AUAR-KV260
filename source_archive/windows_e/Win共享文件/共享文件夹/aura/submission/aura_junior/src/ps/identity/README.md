<!-- aura-architecture-generated -->
# src/ps/identity

<!-- aura-structure-details -->
## 复核后的目录职责

主责：B；运行/使用位置：KV260 PS + 可选 DPU 子图。

内容：人脸质量/对齐/特征、模板库、登记/删除与修订号。

边界：姓名与轨迹分开；UI 经 API 操作库；模型/阈值实测后冻结。

依据：P2，见 report/structure_detail.md 的依据登记。

现有来源：

- `board/identity`

目标目录已建立；本轮没有将实际源文件迁移到此处。
