<!-- aura-architecture-generated -->
# src/host/media_transport

<!-- aura-structure-details -->
## 复核后的目录职责

主责：C；运行/使用位置：Windows 服务端。

内容：媒体接收、编码解码、回复与重连的服务端适配。

边界：板端客户端在 src/ps/runtime/model_client；公用协议在 src/shared/contracts/interaction。

依据：P2、C3、C4，见 report/structure_detail.md 的依据登记。

现有来源：

- `host/model_service/protocol.py`

目标目录已建立；本轮没有将实际源文件迁移到此处。
