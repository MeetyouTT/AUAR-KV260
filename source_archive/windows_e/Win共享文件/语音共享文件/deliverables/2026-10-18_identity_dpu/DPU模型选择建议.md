# 当前项目的DPU模型选择

日期：本地2026-10-18。按用户要求评估，继续暂停量化、部署和运行配置变更。本轮只核对本地模型/图结构、保存板测和Vitis AI3.0官方文档。

后续更新：用户授权继续后，SFace INT8工程候选完成编译、独立DPU及同进程固定图短测；真实身份精度和正式业务仍待验。以下是当时选型依据，最新工程状态见[实施证据](README.md)。

## 建议排序

针对当前KV260、单个B4096、指纹0x101000056010407及Vitis AI3.0，优先保留YOLOX-Nano，下一项重点适配SFace，随后评估YuNet。不是按模型文件大小排名，也不将编译器能解析的算子数当成目标DPU都能执行。

| 模型或算法 | 建议 | 当前证据及限制 |
| --- | --- | --- |
| YOLOX-Nano人体检测 | 继续放DPU | 已有匹配xmodel、真实相机及板测，最近保存快照约9.95Hz；维护检测时效 |
| SFace人脸特征 | 下一项优先适配 | 历史CPU固定图对齐+特征约304.31ms，是该轮身份链主要耗时。原模型27PReLU与1FC不兼容；第二版等价改写通过浮点及Inspector初检。尚未INT8量化、完整编译、精度或混跑验收，收益待测 |
| YuNet人脸检测/五点 | 第二阶段评估卷积部分 | 已有CPU参考，本地图含43Conv/18Relu/5MaxPool，也有Shape/Gather/Reshape/Slice/Softmax等。尚未做本模型目标Inspector/编译；应固定输入并确认子图边界，解码/NMS等仍由CPU处理 |
| Light-ASD主动说话人 | 暂不做完整网络DPU迁移 | 规划在Windows，当前未集成；论文含3D卷积和GRU，现有DPUCZDX8G不直接支持Conv3D，需拆分/改写并验证，不能由“轻量”推出易部署 |
| Paraformer ASR | 保留Windows | 当前已有真实主机链路，没有本目标xmodel或经验证的迁移实现；本阶段投入视觉DPU更直接，也符合用户此前语音留电脑的决定 |
| OmniVoice TTS | 保留Windows | 当前声线/16步及流式播放已有实录成果；不将语音合成整网作为本DPU下一项适配目标 |
| 当前27B对话模型 | 保留Windows GPU | 当前本机模型标签aura-qwen3.8-27b-abliterated:iq4_xs；参数/内存及生成式执行路径与当前B4096部署路线不匹配，不具备直接编译上板条件 |
| ByteTrack、匹配、SQLite、UI | CPU | 当前ByteTrack是NumPy跟踪算法；这些不是待迁移DPU的独立神经网络 |

ResNet18已有DPU分类基准，但不是当前业务必需模型，不增加为常驻任务。MobileFaceNet等属于未固定的历史身份候选；不把未取得/未核验的权重当成已可替换。若SFace量化精度、速度或成本不达标，再评估已有DPU部署参考的其他人脸特征网络。

## 为什么先SFace再YuNet

2026-10-06静态参考图5次预热板测中，检测中位91.66ms、对齐+特征中位304.31ms、整链395.91ms。这是旧CPU参考条件，不是当前相机并发负载或DPU加速比；也不能把三个独立中位数强求相加。它支持优先评估特征网络，但不能保证改写后的DPU候选必然更快。PReLU改写引入额外运算，仍需INT8精度与实测。

即使SFace上DPU，YuNet、对齐、搬运及匹配仍占时间。最终比较仅YOLO与YOLO+身份在相同输入下的检测频率、帧龄、身份等待、CPU及DDR，才能决定身份频率和是否再迁移YuNet。

## 官方依据与本地依据

- [Vitis AI3.0目标算子表](https://docs.amd.com/r/3.0-English/ug1414-vitis-ai/Currently-Supported-Operators)：具体卷积、激活、缓冲和Conv3D支持按DPU目标区分，不能用其他Versal/Alveo支持套用到本板。
- [Vitis AI3.0模型开发流程](https://xilinx.github.io/Vitis-AI/3.0/html/docs/workflow-model-development.html)：Inspector是初检；后续仍需INT8校准、独立评测、目标架构编译和部署。
- [DPU系统集成](https://xilinx.github.io/Vitis-AI/3.0/html/docs/workflow-system-integration.html)：兼容网络复用固定DPU通常不需更换位流，但运行时内存和执行资源仍需评估。
- [Light-ASD原论文](https://arxiv.org/abs/2303.04439)：时空卷积与GRU结构是本次认为整网迁移成本高的依据；未对本地ASD候选实际编译。
- [CPU参考实板报告](/home/ghmd/kv260-adaptation-check-20261006/ADAPTATION_REPORT.md)。
- [SFace兼容检查及最近保存板态](../../../协作任务/2026-10-18_双机联调/DPU身份模型_兼容性结果与下一步_20261018.md)。

建议目标分工：DPU承担YOLO与适配成功的SFace，后续按收益加入YuNet；ARM承担采集、跟踪、对齐、匹配、数据库及界面；Windows承担ASR、对话、TTS和首版ASD。该分工是建议，SFace/YuNet/ASD的未完成状态以上表为准。
