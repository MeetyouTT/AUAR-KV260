<!-- aura-architecture-generated -->
# src/ps/runtime

<!-- aura-structure-details -->
## 复核后的目录职责

主责：C 编排，A/B 提供业务探针；运行/使用位置：KV260 PS；模拟在 PC。

内容：组合入口、生命周期、会话、事件总线、日志与取消。

边界：组合入口可以连接模块，单个业务模块不反向控制全局启动。

依据：P2、C2，见 report/structure_detail.md 的依据登记。

现有来源：

- `board/runtime/application.py`
- `board/runtime/fsm.py`
- `board/runtime/session.py`
- `board/runtime/media_session.py`
- `board/runtime/project_log.py`

目标目录已建立；本轮没有将实际源文件迁移到此处。
