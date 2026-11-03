<!-- aura-architecture-generated -->
# src/host/service

<!-- aura-structure-details -->
## 复核后的目录职责

主责：C；运行/使用位置：Windows 模型主机。

内容：服务生命周期、模型流水线、协议分派和阶段耗时。

边界：pipeline/backends 的 fixture 只是软件联调，实际模型和服务端媒体传输待接。

依据：C3、C6，见 report/structure_detail.md 的依据登记。

现有来源：

- `host/model_service/pipeline.py`
- `host/model_service/backends.py`
- `tools/dialogue_host_ollama.py`

目标目录已建立；本轮没有将实际源文件迁移到此处。
