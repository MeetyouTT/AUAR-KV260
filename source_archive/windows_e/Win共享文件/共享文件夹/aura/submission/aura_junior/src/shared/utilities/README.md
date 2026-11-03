<!-- aura-architecture-generated -->
# src/shared/utilities

<!-- aura-structure-details -->
## 复核后的目录职责

主责：A/B/C；运行/使用位置：PS/Windows/开发机共用。

内容：纯时钟抽象、数据校验、配置解析。

边界：共用工具不成为业务大杂烩；目标、身份、取消状态由业务所有者管理。

依据：C1，见 report/structure_detail.md 的依据登记。

现有来源：

- `common/clock.py`
- `common/config.py`

目标目录已建立；本轮没有将实际源文件迁移到此处。
