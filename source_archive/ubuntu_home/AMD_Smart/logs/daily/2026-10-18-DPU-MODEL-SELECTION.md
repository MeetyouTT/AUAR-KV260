# 当前模型适合DPU加速的排序

按用户询问评估，延续此前暂停量化/部署的指示。已阅读ZIP入口、最新项目导航、身份设计/兼容日志、模型与相机配置、语音AGENTS、现有模型图摘要、历史CPU板测，并查阅Vitis AI3.0目标算子表及模型开发/集成官方文档、Light-ASD原论文。

建议：已有YOLOX-Nano保留，SFace作为下一项优先适配，YuNet其次；Light-ASD先保留Windows，Paraformer/OmniVoice/27B继续电脑端。ByteTrack、SQLite、匹配和UI为CPU任务。原CPU固定图中对齐+特征304.31ms、检测91.66ms支持优先评估SFace；不据此承诺当前并发性能或加速比。

SFace改写仅浮点/Inspector初检通过，未INT8或完整xmodel；YuNet尚未目标检查，动态图及后处理需单独处理；Light-ASD论文有3D卷积及GRU，现有目标不直接支持Conv3D，不能把参数少视为迁移容易。

新增共享[DPU模型选择建议](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-18_identity_dpu/DPU模型选择建议.md)，本轮无生产源码/模型/配置/板端变更，无推理、编译或部署。验证为来源和本地文档链接核对，不运行产品测试。
