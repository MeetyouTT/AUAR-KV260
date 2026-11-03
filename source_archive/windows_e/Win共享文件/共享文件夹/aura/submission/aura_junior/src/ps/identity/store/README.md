<!-- aura-architecture-generated -->
# SQLite 模板 / 匹配 / 删除失效

模块：M3 / `identity`；负责人：B；目标位置：KV260 PS。

当前证据层级：**软件联调通过**。

输入：特征 / 登记与删除操作。
输出：KNOWN / UNKNOWN / AMBIGUOUS。

现有源码/证据来源：

- `board/identity/store.py`
- `board/runtime/application.py`

待补：数据库逻辑已测；真人阈值、重返、实时板端持久化待验。

关联内部验收：T20、T21、T22、T23。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。
