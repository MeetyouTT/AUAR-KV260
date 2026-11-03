<!-- aura-architecture-generated -->
# src/shared

<!-- aura-structure-details -->
## 复核后的目录职责

主责：A/B/C；运行/使用位置：PS/Windows/开发机共用。

内容：纯数据类型、格式校验、公共配置加载、时钟接口。

边界：不打开设备、不启动模型线程，不依赖具体 UI 或厂商运行库。

依据：P2、C1，见 report/structure_detail.md 的依据登记。

现有来源：

- `common`

目标目录已建立；本轮没有将实际源文件迁移到此处。
