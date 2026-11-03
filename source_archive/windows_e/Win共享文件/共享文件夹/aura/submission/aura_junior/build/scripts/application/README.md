<!-- aura-architecture-generated -->
# build/scripts/application

<!-- aura-structure-details -->
## 复核后的目录职责

主责：C 编排，三人核对；运行/使用位置：开发机。

内容：依赖准备、按清单导出、保留包导入与资源查找、隔离复现。

边界：目标目录是职责位置，不能把当前 Python 文件机械搬过去就声称可运行。

依据：C1、C9、C14，见 report/structure_detail.md 的依据登记。

现有来源：

- `scripts/package_project.py`
- `requirements.txt`
- `requirements-live.txt`

目标目录已建立；本轮没有将实际源文件迁移到此处。
