<!-- aura-architecture-generated -->
# src/ps/runtime/model_client

<!-- aura-structure-details -->
## 复核后的目录职责

主责：C；运行/使用位置：KV260 PS；模拟在 PC。

内容：板端异步客户端、有界在途/等待/结果队列。

边界：不是 Windows 推理服务；模型执行、媒体传输后端分别实现。

依据：C2、C4，见 report/structure_detail.md 的依据登记。

现有来源：

- `host/model_service/client.py`
- `board/runtime/dialogue_client`

目标目录已建立；本轮没有将实际源文件迁移到此处。
