<!-- aura-architecture-generated -->
# src/ps/motion/hw_access

<!-- aura-structure-details -->
## 复核后的目录职责

主责：A，B 调用；运行/使用位置：KV260 PS。

内容：IP/ABI 核验、原子提交、状态快照、STOP 与恢复访问库。

边界：不承担目标选择；维护诊断与正式写入互斥。

依据：P2、C8，见 report/structure_detail.md 的依据登记。

现有来源：

- `board/motion/vsrv_driver.py`

目标目录已建立；本轮没有将实际源文件迁移到此处。
