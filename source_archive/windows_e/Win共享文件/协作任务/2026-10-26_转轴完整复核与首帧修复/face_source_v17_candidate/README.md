# source-v17：保持检测输出等价的直接BGR输入

已于2026-10-26部署到KV260，同boot camera720342；固定实锚NCC/LK跟踪数学、算法版本14、协议11、250ms图/500ms锚不变。只适配native YuNet/fix7/320px实例，将原uint8 resize→float32 NCHW blob→INT8改为同resize→固定LUT→NHWC INT8；guard对象、native owner/调度、模型、输出变换、解码/NMS和CPU保护回退保持。

69项主机源/跟踪回归、额外7项独立异常/并发检查通过。板端20帧同输入、双方同Fake native输出，完整检测准备/解码/NMS逐字节相同；wall中位66.568→26.377ms。此为CPU适配对照，不是DPU或实体转轴延迟。真实服务24轮NoFace分段观测确认direct编码存在、无float blob，DPU_YUNET_INT8/workerfault0；不是真人随动验收。

本目录runtime manifest SHA `84d7359f18a5a98aa5dabba967c4ededf5e35d0c43153166fc6998729a30219c`，11 pins。旧source-v16作为回退保留。生产动态状态和全部证据见共享[完整复核回执](/home/ghmd/Win共享文件/协作任务/2026-10-26_转轴完整复核与首帧修复/README.md)。主机测试使用现有OpenCV环境以及已核验runtime参考源码；Windows接收/运行未代验。
