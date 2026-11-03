<!-- aura-architecture-generated -->
# AURA 项目结构细化与依据复核

版本：2026-10-09 / structure-2。

## 结构结论与适用范围

七类提交目录与 M1–M8 功能划分有明确依据。七目录按交付物用途组织；M1–M8 按产品功能组织；PS/PL/Windows/Ubuntu 标明运行或构建位置；A/B/C 标明责任。这四个维度不能互相替代。

以下是经过源码核对的目标目录与职责框架。现有主仓仍是唯一正在开发的源码。提交目录中的 README/interface 是说明，不能当作已迁移源码；目标目录名也不是当前 Python 包名。实际导出与迁移完成前，运行入口仍是主仓 tools/aura_project.py。

官方要求交付源码、验证、实现、板测、Skill、报告与复现；src/ps、src/host、src/shared 等细分是依据本项目职责作出的工程选择。官方没有规定必须有 64 个模块、三项 Skill、30 项测试或这些内部性能目标。

## 开发、接口与交付规则

1. 每个模块有唯一代码主责，接口另有主写/评审者。按原总包 I01–I07 登记接口；新增源期限是 I02 的版本演进，不能与旧相对租约混用。
2. 共用类型、版本、错误码和序列化应有唯一来源。当前媒体 protocol.py 虽位于 host，已被板端消费；目录重构前保留导入兼容。
3. UI/主机只经业务接口提交建议。相机、DPU、身份库、运动寄存器、音频与会话分别有唯一所有者；状态机不因拆目录再复制一套。
4. 当前应用存在组合入口、采集线程与异步工作线程。目录表示模块边界，并不要求每个目录启动独立进程；未来进程拆分按资源预算决定。
5. 固件、系统、模型、配置、应用、标定和实测须用同一 release 清单关联。旧证据可作参考，不自动覆盖新组合。
6. 数据按标定、独立测试、黄金参考、运行资源和实验分析分类；原始板测日志在 board/results 按 run_id 归档，其他地方引用或生成只读分析。
7. 真实身份数据库、在途媒体、缓存与日常日志放在部署环境配置的可写状态目录，不作为默认源码/测试样本打包。最终状态路径尚待目标镜像冻结。
8. 目录中的证据状态描述模块已有依据，不是每个新适配文件都已上板。BOARD 引用原有限板测；PC、软件测试与最终板验收保持各自范围。

## 源码迁移与发布的实际门槛

当前导入使用 common、board、host、tools 命名空间；common/config.py 和 avatar_assets.py 还依赖源码相对层级定位配置、模型和素材。先解决包入口和资源路径，再导出目标布局；不能只把文件按目录移动。

最终源码导出必须给出：唯一源文件→目标路径清单、SHA256、第三方来源/许可、明确选择的生产与参考入口、匹配的依赖锁。将导出包解到独立目录，在不依赖原工作区/相邻目录的条件下验证导入、配置和资源、模拟链；随后在目标平台验证真实模型、设备与构建。现在的结构校验尚未完成这些最终设备验收。

旧硬件构建脚本使用本机绝对路径、IP cache 与既有 routed DCP。src/platform 留输入，build/scripts 留可复建步骤，board/firmware 留匹配输出；正式“从零复现”需要参数化后实际执行。

Qt/Tk 是已有 PC 代码来源，RGB565 导出也是既有资源路径；板端最终渲染后端按原总包 §4.9 在实际镜像选定。旧许可矩阵中的 LVGL/旧版本陈述不构成当前冻结结论。

机构继续等待 3D 模型。源码/合同迁移、真实项目模型与媒体、PL 新期限、板端 UI、G0–G5 和完整复现均有独立验收入口。


## 已发现并处理的结构问题

| 问题 | 证据 | 结构修正 / 尚待实现 |
|---|---|---|
| F01 共享定义缺少归属 | common 与 host/model_service/protocol.py 被多端消费，原目录图没有共享层。 | 增加 src/shared/contracts 与 utilities，保存单一定义和原 I01–I07 登记；STRUCTURE_CORRECTED_CODE_REFACTOR_PENDING |
| F02 目录名不能判断部署位置 | host/model_service/client.py 是运行在 AuraRuntime 所在端的客户端。 | 明确归属 PS 客户端；Windows 服务端与双端协议另列；STRUCTURE_CORRECTED_CODE_REFACTOR_PENDING |
| F03 旧音频目录混合三类职责 | Qwen 合成、旧 ASR、SAPI/Sherpa 合成与本地播放都在 board/runtime/audio 下。 | 按主机推理、板端真实设备、历史参考划分；不机械整体搬迁；STRUCTURE_CORRECTED_CODE_REFACTOR_PENDING |
| F04 软件监督放错交付位置 | AuraRuntime 直接 import SimulationGuard，单独放到 sim 会遗漏运行依赖。 | 模型位置改为 src/ps/motion/simulation_guard；sim/software 放测试；STRUCTURE_CORRECTED |
| F05 DPU 平台与自研 RTL 混称 | 已有 DPU 是官方 IP/平台集成；图中有限板测来源不是自研 DPU RTL。 | DPU 集成位置改为 src/platform/dpu_integration；自研 motion RTL 单列；STRUCTURE_CORRECTED |
| F06 接口编号与原总包冲突 | 前一版把数据流说明记作 I01–I09，与总包 I01–I07 含义冲突。 | 恢复 I01–I07；原九类数据流说明改名为 D01–D09 并给映射；STRUCTURE_CORRECTED |
| F07 构建、输入和工件未分清 | XDC/BD/DT 输入、工具脚本、最终固件和报告用途不同；旧脚本有绝对路径。 | 分别归 src/platform、build/scripts、board/firmware、build/reports；复现结论待实际重建；STRUCTURE_CORRECTED_BUILD_PORTABILITY_PENDING |
| F08 资源和运行数据缺少分类 | ui/ 多为 JSON，UI 源码在 board/interaction；素材/模型/标定/个人库不能仅按后缀归组。 | 新增 data/assets、data/models/source/compiled、data/test；运行身份库/临时媒体为外部可写状态；STRUCTURE_CORRECTED |
| F09 新目录不能证明搬迁后可运行 | common/config.py 与 avatar_assets.py 按源码相对层级定位根目录；导入仍使用 board/common/host。 | 现有源码唯一开发；目录说明记录目标区域；真正重排源码前先解决包/资源路径，再隔离验收；MIGRATION_NOT_EXECUTED |
| F10 历史说明不能替代最终平台选择 | 旧 LICENSE_MATRIX.md 声称板端 LVGL，当前存在 Qt 代码而最终板端渲染尚未冻结。 | 标为历史依据；按总包 §4.9 在实际镜像选定后端后再更新依赖/许可与资源预算；FINAL_UI_BACKEND_AND_LICENSE_AUDIT_PENDING |

## 完整目标目录树

每个叶位置仍明确标注来源与未完成内容；下列模块目录不等于已实现功能。

```text
aura_junior/
├── src/
│   ├── config/
│   ├── host/
│   │   ├── asd/
│   │   ├── asr/
│   │   ├── media_transport/
│   │   ├── service/
│   │   ├── tts/
│   │   └── vlm/
│   ├── platform/
│   │   ├── constraints/
│   │   ├── dpu_integration/
│   │   └── system/
│   ├── ps/
│   │   ├── audio/
│   │   │   ├── mcp01_capture/
│   │   │   └── mcp01_playback/
│   │   ├── extensions/
│   │   │   ├── observation_memory/
│   │   │   ├── streaming_audio/
│   │   │   └── vision_context/
│   │   ├── fusion/
│   │   │   ├── av_windows/
│   │   │   ├── freshness/
│   │   │   ├── pl_time_mapping/
│   │   │   ├── scheduler/
│   │   │   ├── speaker_context/
│   │   │   └── target_manager/
│   │   ├── identity/
│   │   │   ├── cpu_reference/
│   │   │   ├── dpu_embedding/
│   │   │   ├── quality_alignment/
│   │   │   └── store/
│   │   ├── motion/
│   │   │   ├── hw_access/
│   │   │   ├── service/
│   │   │   └── simulation_guard/
│   │   ├── runtime/
│   │   │   ├── model_client/
│   │   │   ├── session/
│   │   │   └── state_machine/
│   │   └── vision/
│   │       ├── capture/
│   │       ├── cpu_reference/
│   │       ├── media_windows/
│   │       ├── person_dpu/
│   │       └── tracking/
│   ├── rtl/
│   │   ├── extensions/
│   │   │   └── hls_acceleration/
│   │   ├── motion_guard/
│   │   │   ├── axi_commit/
│   │   │   ├── output_gate/
│   │   │   └── source_deadline/
│   │   └── vsrv_reference/
│   ├── shared/
│   │   ├── contracts/
│   │   │   ├── interaction/
│   │   │   ├── motion/
│   │   │   └── platform/
│   │   └── utilities/
│   ├── third_party/
│   └── ui/
│       ├── avatar/
│       ├── enrollment_memory/
│       └── views/
├── sim/
│   ├── rtl/
│   └── software/
├── build/
│   ├── reports/
│   └── scripts/
│       ├── application/
│       ├── hardware/
│       └── models/
├── board/
│   ├── calibration/
│   │   └── mechanics/
│   ├── firmware/
│   │   └── platform/
│   ├── results/
│   └── scripts/
│       ├── device_diagnostics/
│       └── display/
├── data/
│   ├── assets/
│   ├── calibration/
│   ├── metrics/
│   │   └── experiments/
│   │       ├── g0/
│   │       ├── g1/
│   │       ├── g2/
│   │       ├── g3/
│   │       ├── g4/
│   │       └── g5/
│   ├── models/
│   │   ├── compiled/
│   │   └── source/
│   ├── reference/
│   └── test/
├── skill/
│   ├── async-result-validation/
│   ├── command-guard-validation/
│   └── perception-freshness-benchmark/
└── report/
    ├── contracts/
    ├── design_report/
    ├── llm_collaboration/
    ├── release/
    └── reproduction/
```

## 目录职责、责任与依据

| 目录 | 负责人 / 位置 | 放什么 | 边界 | 依据 |
|---|---|---|---|---|
| src | A/B/C / 源码 | 实际采用的设计源码与固定合同 | 生成工件、板测结果与性能结论放到对应交付目录 | O1, O4 |
| src/shared | A/B/C / PS/Windows/开发机共用 | 纯数据类型、格式校验、公共配置加载、时钟接口 | 不打开设备、不启动模型线程，不依赖具体 UI 或厂商运行库 | P2, C1 |
| src/shared/contracts | A/B/C 按 I01–I07 / 跨模块 | 合同登记、模式、单位、代次与兼容性 | 一份定义；各消费者引用或生成，避免三份独立寄存器表 | P2, C1, C3 |
| src/shared/contracts/platform | A / I01 | 平台/版本/能力/证据引用合同 | 具体部署实例及匹配固件在 board/firmware；未知保持未冻结 | P2, C8 |
| src/shared/contracts/motion | A 主写，B 评审 / I02 | 寄存器、命令、状态、时钟/回绕和恢复行为的唯一规格 | 本轮不预填未核实地址、位宽、引脚与绝对期限 ABI | P2, P3, C8 |
| src/shared/contracts/interaction | C 主写，B 评审 / I05 | 文字与媒体版本、请求/取消/段序/PCM/图像归属 | 文字 1.0 与 aura-runtime-1 分别登记；跨机媒体编码尚未冻结 | P2, C3 |
| src/shared/utilities | A/B/C / PS/Windows/开发机共用 | 纯时钟抽象、数据校验、配置解析 | 共用工具不成为业务大杂烩；目标、身份、取消状态由业务所有者管理 | C1 |
| src/ps | B/C；A 提供硬件访问层 / KV260 ARM/Linux | 板端采集、感知业务、状态、执行请求与本地反馈 | 该目录表示 PS 职责；Python 进程与 PL 电路分别验收 | P1, P2 |
| src/ps/vision | B / KV260 PS + DPU 调用 | 唯一相机、检测前后处理、跟踪、快照与脸片段 | 人体检测、CPU 人脸参考、跟踪预测分别标明；不拥有身份库/运动寄存器 | P2, C2 |
| src/ps/identity | B / KV260 PS + 可选 DPU 子图 | 人脸质量/对齐/特征、模板库、登记/删除与修订号 | 姓名与轨迹分开；UI 经 API 操作库；模型/阈值实测后冻结 | P2 |
| src/ps/fusion | B；C 提供说话人窗口结果 / KV260 PS | 唯一当前目标、有效期、单 CU 准入和说话人复核 | 不运行 Windows ASD 模型；旧窗口坐标不直接变成运动命令 | P2, P3, C2 |
| src/ps/motion | B；A 提供驱动和 ABI / KV260 PS | 唯一运动服务、命令校验与硬件访问适配 | 正式模式只有运动服务提交；软件模拟监督属于可执行适配，仿真目录保存测试 | P2, C2, C8 |
| src/ps/motion/hw_access | A，B 调用 / KV260 PS | IP/ABI 核验、原子提交、状态快照、STOP 与恢复访问库 | 不承担目标选择；维护诊断与正式写入互斥 | P2, C8 |
| src/ps/motion/simulation_guard | B/A / PC 联调 / PS 软件参考 | 软件合同模型及模拟运动后端 | 当前运行时直接依赖；不把它当作 PL 独立到期的证据 | C2, C8 |
| src/ps/audio | C；A 解决驱动/USB / KV260 PS | MCP01 唯一采录/播放、样本时间、真实停声与半双工 | 模型合成与设备播放分层；旧 tts.py 混合职责需拆分 | P2, C5 |
| src/ps/runtime | C 编排，A/B 提供业务探针 / KV260 PS；模拟在 PC | 组合入口、生命周期、会话、事件总线、日志与取消 | 组合入口可以连接模块，单个业务模块不反向控制全局启动 | P2, C2 |
| src/ps/runtime/model_client | C / KV260 PS；模拟在 PC | 板端异步客户端、有界在途/等待/结果队列 | 不是 Windows 推理服务；模型执行、媒体传输后端分别实现 | C2, C4 |
| src/host | C / Windows 模型主机 | 常驻模型、准备探针、ASR→VLM→TTS 和 ASD | 不写运动寄存器、不决定是否播放旧结果、不直接改板端身份库 | P1, P2 |
| src/host/service | C / Windows 模型主机 | 服务生命周期、模型流水线、协议分派和阶段耗时 | pipeline/backends 的 fixture 只是软件联调，实际模型和服务端媒体传输待接 | C3, C6 |
| src/host/media_transport | C / Windows 服务端 | 媒体接收、编码解码、回复与重连的服务端适配 | 板端客户端在 src/ps/runtime/model_client；公用协议在 src/shared/contracts/interaction | P2, C3, C4 |
| src/host/asr | C / Windows 模型主机 | 中文识别后端与准备/失败报告 | 旧 board/runtime/audio/asr.py 是候选实现来源，最终服务接入待验 | P2, C5 |
| src/host/vlm | C / Windows 模型主机 | 本轮图像问答、角色与对话上下文 | 只消费有来源的图像；自然语言输出没有运动执行权限 | P2, C6 |
| src/host/tts | C / Windows 模型主机 | 选定 Qwen3-TTS 声线、文本到真实音频 | 当前服务有演示/UI 耦合；迁移时保留声线原件并提取纯合成适配 | P2, C5, C7 |
| src/host/asd | C，B 复核对象 / Windows 模型主机 | Light-ASD 同窗视听推理与质量/分数 | 真实模型和同步未完成；只给建议，不生成舵机坐标 | P1, P2 |
| src/ui | C / KV260 PS；PC 为开发基线 | 状态投影、汐蓝播放器、字幕与授权操作页面 | 单独管理显示状态；不直接打开相机/声卡、改库或写寄存器；板端渲染后端待实测冻结 | P2, C9 |
| src/rtl | A / KV260 PL | 自研运动监督、AXI 接口、PWM、到期/停止/恢复电路 | 官方 DPU 的来源和集成单列；旧相对租约与拟议绝对源期限分开 | P2, P3, C8 |
| src/platform | A / Ubuntu 构建 → KV260 PS/PL | 块设计、IP 集成、XDC、时钟复位、设备树/驱动配置源 | 输入工程与构建脚本、生成工件分别存放 | O1, P2, C10 |
| src/platform/dpu_integration | A / KV260 PL 集成 | 官方 DPU 配置、版本、来源、架构指纹及集成输入 | 不声称拥有/交付 AMD DPU 的自研 RTL；以实际授权工具/IP 获取流程复建 | P2, C8, C10 |
| src/platform/constraints | A / Vivado 输入 | 实际 pin/clock/reset XDC 与约束来源 | 不根据示例填写最终引脚；与最终统一平台同次验证 | P2, C10 |
| src/platform/system | A / Linux/设备树/驱动源配置 | 内核/DT/驱动/系统配方与固定版本补丁 | 最终镜像在 board/firmware；系统源码来源和许可获取流程须固定 | P2 |
| src/config | A/B/C 按字段 / 应用/构建配置输入 | 模拟/CPU参考/KV260 配置、模型与工具清单、实验定义 | 示例配置与实测参数有 verified 状态；密码令牌、运行日志和身份库不作为配置源 | C1, C11 |
| src/third_party | A/B/C 各自引入者 / 依赖登记 | 来源、固定版本、修改范围、许可原文和获取方式 | 旧许可矩阵含历史路线与版本；最终不能直接沿用全部已核实标记 | O1, C12 |
| sim | A/B/C / 开发机/软件测试 | 测试激励、运行脚本、预期/实际、失败样例与波形 | 测试通过范围按 PC、RTL 仿真分别记录，不能替代板测 | O1 |
| sim/rtl | A / RTL 仿真 | AXI/COMMIT、到期/停止、重放、复位、恢复的自检查用例 | 对新源期限核新增用例；既有相对租约 testbench 仅验证旧核 | P2, P3 |
| sim/software | B/C；A 审合同 / PC | 纯软件单元/合同/集成测试与 fixture | 源码中的 SimulationGuard 在 src/ps/motion；这里放验证它的用例 | C2, C13 |
| build | A；B 模型，C 应用依赖 / Ubuntu/开发机 | 复建入口、固定工具与产生的工程报告 | 依赖构建输入版本；不将旧绝对路径脚本标成干净环境已复现 | O1, C10 |
| build/scripts/hardware | A / Ubuntu | 平台/RTL/系统构建流程 | 外部旧脚本使用主机绝对路径与缓存，发布前需要参数化及实跑 | C10 |
| build/scripts/models | B；C 模型环境 / Ubuntu/模型环境 | 权重校验、校准、量化、DPU 编译与比较 | 记录输入/工具/arch/hash；不能拿分类参考替代项目人体/身份模型 | P1, P2 |
| build/scripts/application | C 编排，三人核对 / 开发机 | 依赖准备、按清单导出、保留包导入与资源查找、隔离复现 | 目标目录是职责位置，不能把当前 Python 文件机械搬过去就声称可运行 | C1, C9, C14 |
| build/reports | A/B/C / 构建输出 | 资源、时序、DRC/CDC、量化/编译报告 | 原始报告绑定构建 ID；报告中的结论引用原始文件 | O1, C10 |
| board | A/B/C / KV260 实机交付 | 匹配的工件、部署运行、自检、真实输出及恢复 | 与开发主仓 board/ 的源码含义不同，目录对照必须说明 | O1, P2 |
| board/firmware | A / KV260 | 同一 release 的 bitstream/overlay/系统/平台实例清单 | 只纳入匹配版本，说明来源与哈希；无新工件时保留待补 | O1, C8 |
| board/scripts | C 总入口，A/B 提探针 / KV260 | 部署、启动、自检、停止、维护与恢复 | 物理访问采用冻结入口；当前框架默认禁能 | P2 |
| board/results | 三人按测试归档 / KV260 实測 | 平台/功能/异常/冷启动/长测记录与仪器证据 | 按 run_id/release 归档原始结果；data/metrics 保留分析或引用，不维护两份可修改原始日志 | O1, P2 |
| board/calibration/mechanics | A/B / 3D 模型到位后的实物 | 轴向、角度/PWM、限位、供电与停止输入标定记录 | 当前 WAIT；图像归一化偏差不当作已标定角度 | P3, C11 |
| data | B/C；A 提供硬件参考 / 数据与资源 | 标定/测试/参考、模型/素材与可追溯分析 | 数据来源、用途、权限、哈希和是否合成分别记录 | O1, P1 |
| data/calibration | B/A；C 视听同步 / 标定输入与输出 | 误差界、成本、身份阈值、声画映射的标定集和结果 | 与独立测试划分分开；控制时效和长媒体窗口不能混成同一期限 | P2, P3 |
| data/test | B/C / 独立测试 | 固定输入集、标注、测试划分及版本 | 不使用同一批数据既调参数又报告独立测试效果 | P3 |
| data/reference | A/B/C / 黄金参考 | CPU/浮点参考、合成 fixture 和预期输出 | 每项带适用算法/版本；合成演示与真实样本分别标记 | O1, C13 |
| data/models | B/C / 推理资源 | 模型卡、来源、固定版本、SHA、获取方式和兼容性 | 权重与编译产物分目录；实际分发按许可/大小决定 | P1, C11 |
| data/models/source | B/C / 原始权重 | 获准使用的 ONNX/原始模型或固定获取清单 | 不把目录名/模型名当作真实可用权重 | C11 |
| data/models/compiled | B / KV260 DPU 模型 | 最终项目 xmodel、arch、指纹、编译日志引用 | 当前项目人体/身份 xmodel 待完成；CPU 权重另列 | P1, C11 |
| data/assets | C / 界面运行资源 | 汐蓝帧、UI 清单、已选声线参考与资源版本 | 素材同一权威版本，UI 源码引用；资源路径重组要经过迁移验收 | C7, C9 |
| data/metrics | A/B/C / 实验分析 | G0–G5、延迟、误差、覆盖、身份等待与分析入口 | 记录真实 run_id；空值代表未测，合成数字不填进板测对比 | P3, C11 |
| skill | A/B/C / 陌生使用者复用 | 命令监督、感知时效、异步取消三个候选包 | 每包应有适用/步骤/失败/效果/边界/复用记录；三个数量是项目安排 | O2, P4 |
| report | 全队 / 评审与复现 | 设计报告、框图、接口、需求/证据索引、AI 协作与复现 | 解释原始数据，不能凭模板/图册宣称优化或整机完成 | O3 |
| report/contracts | 按 I01–I07 主责 / 接口说明 | 原七份合同登记、字段/单位/状态/兼容性及修订记录 | 接口描述不是已经冻结的运行时 schema 或硬件 ABI | P2, C1, C3 |
| report/release | A 汇总，各人确认 / 统一交付 | 源码、系统、模型、配置、数据、报告的同一 release 清单与 SHA | 当前工程框架包与最终完整交付分别标记 | P2, C14 |
| report/reproduction | C 编排，A/B 补步骤 / 第三方复现 | 从零构建/部署/运行/停止和非作者实际记录 | 有脚本与实际执行成功分别记录；源包通过不表示整机通过 | O3, C10, C14 |

## 原 I01–I07 接口登记

| 编号 | 原文件约定 | 主写 / 评审 | 当前状态 |
|---|---|---|---|
| I01 平台清单 | contracts/platform_manifest.json | A；B/C 补实际值 | 已存在参考清单；最终统一平台实例/模型/系统/器件待冻结 |
| I02 运动寄存器与行为 | contracts/motion_regs.yaml | A 主写，B 评审 | 旧相对租约 ABI 与软件模型已有；新绝对源期限 ABI/位宽/时钟映射待冻结 |
| I03 相机与轨迹 | contracts/camera_track.schema.json | B 主写，C 评审 | 软件类型已有；真实采集时义、池生命周期和对外序列化待冻结 |
| I04 身份与授权 | contracts/identity.schema.json | B 主写，C 评审 | 匹配/删除软件逻辑已有；登记操作、质量和阈值实测待接 |
| I05 交互与媒体 | contracts/interaction.schema.json | C 主写，B 评审 | 文字 1.0 与媒体 aura-runtime-1 分开；真实跨机媒体编码与设备交付待验 |
| I06 说话人建议 | contracts/asd_focus.schema.json | C 主写，B 评审 | 窗口结果门已有；真实同步/Light-ASD、竞争保持和完整 schema 待完成 |
| I07 运行状态 | contracts/runtime_status.schema.json | C 汇总，A/B 定义状态 | 事件/UI 状态已有；统一平台/进程/设备状态合同与实屏待验 |

## 共享资源与状态所有者

| 资源 | 唯一所有者 | 其他模块怎样使用 | 必须保持的条件 |
|---|---|---|---|
| 相机和帧池 | B / camera_service | 检测、UI、VLM、ASD 通过帧引用/副本读取 | 重连换 camera_epoch；来源时间语义真实 |
| DPU 提交 | B / 单 CU 调度 | 检测/身份统一准入，A 提供匹配平台 | 在途任务不可假设抢占；成本必须测量 |
| 目标与轨迹代次 | B / target_manager | C 只提交手动/说话人建议 | 重新出现换代；不以身份姓名替代轨迹 |
| 身份数据库 | B / identity_service | C 经授权 API 登记/删除 | 修订号更新，旧缓存/在途结果失效 |
| 运动寄存器 | B / motion_service；A 提供访问库 | UI/主机消费状态或建议对象 | 维护与正式服务互斥；新源期限/恢复合同待冻结 |
| 音频采录播放 | C / 音频服务 | 媒体/ASD 使用有时标的样本接口 | 取消先废止代次并真实停声；采样格式来自设备 |
| 会话和取消代次 | C / 板端会话 | Windows 回显请求归属与板端期限 | 旧结果不恢复字幕/音频/动画 |
| 模型流水线 | C / Windows 服务 | 接收明确媒体，返回文字/PCM/分数 | 不得操作板端运动或数据库 |
| 显示与动画 | C / UI | 订阅单一事件总线/状态快照 | 口型跟实际播放；不再开一套设备或业务状态机 |
| PL/系统发布 | A / 平台入口 | B/C 使用相同 release 和指纹 | 不是三人分别加载三个 bitstream |

## 现有源码与静态依赖核对

已解析 171 个 Python 文件并记录 420 条本地静态导入。明细见 current_source_map.csv 与 static_imports.csv。解析和分类不表示所有历史工具都属于最终交付，也不表示运行通过。

这次重点核对的调用点：

| 问题 | 实际文件 / 行 | 原文片段 |
|---|---|---|
| F01 | board/runtime/media_session.py:6 | `from host.model_service.protocol import (` |
| F02 | board/runtime/application.py:17 | `from host.model_service.client import AsyncModelClient` |
| F02 | host/model_service/client.py:5 | `from board.runtime.dialogue_client.ws_client import WebSocketClient` |
| F03 | board/runtime/audio/selected_voice.py:61 | `from qwen_tts import Qwen3TTSModel` |
| F03 | board/runtime/audio/tts.py:387 | `class TtsPlayer:` |
| F03 | board/runtime/audio/tts.py:250 | `class SherpaTtsBackend(TtsBackend):` |
| F04 | board/runtime/application.py:12 | `from board.motion.guard import SimulationGuard` |
| F05 | hardware/platform/platform_manifest.json:9 | `"absolute_source_deadline_supported": false,` |
| F07 | /home/ghmd/kv260-visual-servo-20261007/scripts/implement_source_platform.py:22 | `cache=Path('/home/ghmd/kv260-m3-axilite-20261002/src/kv260/overlays/examples/benchmark/binary_container_1/ip_cache')` |
| F07 | /home/ghmd/kv260-visual-servo-20261007/scripts/implement_source_platform.py:26 | `protected=[script,Path(__file__).resolve(),ROOT/'rtl/visual_servo.sv',Path(audit['generated_bd']),Path(audit['generated_hwh']),platform/'pin.xdc']` |
| F08 | board/interaction/avatar_assets.py:24 | `AVATAR_DIR = _ROOT / "assets" / "avatar"` |
| F09 | common/config.py:7 | `PROJECT_ROOT = Path(__file__).resolve().parents[1]` |
| F09 | board/interaction/avatar_assets.py:23 | `_ROOT = Path(__file__).resolve().parents[2]` |
| F10 | docs/LICENSE_MATRIX.md:14 | `\| PySide6 (Qt for Python) \| 6.11.2 \| **LGPL-3.0 / 商业双许可** \| PC 侧 UI 原型与离屏渲染 \| 否（板端为 LVGL，不装 Qt） \| ✅ \|` |

## 依据登记

| 编号 / 类型 | 原文位置 | 支持的判断 | 文件 |
|---|---|---|---|
| O1 / official | AMD 指南 §3.3.5.1、§3.3.5.4 | 源码、验证、构建、上板与推荐七目录；其他组织须对照 | /home/ghmd/aura-submission-framework-20261009/official_guide.pdf |
| O2 / official | AMD 指南 §3.3.5.2 | 技能包适用、方法、失效、效果、失败来源与可复用性 | /home/ghmd/aura-submission-framework-20261009/official_guide.pdf |
| O3 / official | AMD 指南 §3.3.5.3 | 原理框图、软硬件接口、优化、AI 协作与复现 | /home/ghmd/aura-submission-framework-20261009/official_guide.pdf |
| O4 / official | AMD 指南 §3.3.5.4 | 英文命名，目录结构为推荐；细分职责是本项目设计 | /home/ghmd/aura-submission-framework-20261009/official_guide.pdf |
| P1 / project_plan | 2026-10-08 当前框架 §4–5 | KV260 PS/PL、Windows 模型主机、Ubuntu 构建与 M1–M8 | /home/ghmd/Win共享文件/方案/aura_junior_project_framework_20261008.md |
| P2 / project_plan | 2026-10-02 总包 §2.3、§4、§6.1 | 共享资源唯一所有者、板端服务职责与原 I01–I07 | /home/ghmd/aura-submission-framework-20261009/references/manager_20261002.md |
| P3 / project_plan | 2026-10-08 当前框架 §6–8 | 候选源期限/调度/新 PL 监督、实验、机构等待 | /home/ghmd/Win共享文件/方案/aura_junior_project_framework_20261008.md |
| P4 / project_plan | 2026-10-07 技能包方案 | 三项技能包是项目选择，最终需实际复用验证 | /home/ghmd/Win共享文件/方案/aura_skill_package_plan_and_delivery_20261007.md |
| C1 / code | 公共类型和路径计算 | 当前运行时依赖 common 与仓根资源路径 | common/contracts.py; common/config.py; common/clock.py |
| C2 / code | 组合入口与资源调用 | AuraRuntime 组合检测、目标、身份、模拟监督、会话和客户端 | board/runtime/application.py |
| C3 / code | 媒体协议使用点 | PS media_session 与 host pipeline 共用 protocol.py | board/runtime/media_session.py; host/model_service/protocol.py; host/model_service/pipeline.py |
| C4 / code | 板端客户端的实际导入 | client.py 导入板端 WebSocket 客户端；由 AuraRuntime 创建 | host/model_service/client.py; board/runtime/application.py |
| C5 / code | 模型与播放混合的旧音频目录 | selected_voice 是 Qwen/Torch 合成；tts.py 同时含合成与播放类 | board/runtime/audio/selected_voice.py; board/runtime/audio/asr.py; board/runtime/audio/tts.py |
| C6 / code | 主机流水线与候选后端 | 流水线框架已有，RealBackendPlaceholder 明确占位 | host/model_service/pipeline.py; host/model_service/backends.py |
| C7 / code | 当前选定声线服务依赖 | 选定声线服务依赖演示/脸部工具；纯模型适配待整理 | tools/selected_voice_service.py; tools/facial_layers.py |
| C8 / code_and_reference | 旧平台能力与 VSRV | 只有相对租约；新绝对源期限未实现 | hardware/platform/platform_manifest.json; hardware/README.md; hardware/rtl/visual_servo.sv; board/motion/guard.py |
| C9 / code | UI 代码和素材路径 | UI 源码在 board/interaction；ui 为配置；素材由仓根路径加载 | board/interaction/avatar_assets.py; board/interaction/qt_app.py; ui/ui_state.schema.json |
| C10 / build_reference | 既有构建脚本 | 依赖原工程、绝对路径、IP cache 和 routed DCP | /home/ghmd/kv260-visual-servo-20261007/scripts/implement_source_platform.py; /home/ghmd/kv260-visual-servo-20261007/SOURCE_PLATFORM_REPORT.md |
| C11 / configuration | 配置和待冻结清单 | runtime.*、模型、工具、机械标定与 G0–G5 声明 | config/model_manifest.json; config/toolchain_lock.json; config/servo_calibration.json; config/experiments.json |
| C12 / historical_document | 历史许可矩阵 | 9 月旧方案中含 LVGL、旧素材/模型/版本；最终需重核 | docs/LICENSE_MATRIX.md |
| C13 / software_evidence | 此前框架验证 | 41 项软件验证及合成样例，未替代真实系统 | tests/framework; metrics/raw/framework-validation-20261009/validation.json |
| C14 / packaging_code | 现有软件源包工具 | 按既有包路径打包；正式分层导出与整机包待验 | scripts/package_project.py |

官方企业入口：https://gitee.com/Vickyiii/fpgachina26-amd 。本次能读取入口，分赛道正文仍无法抓取；详细要求引用用户 ZIP 原官方 PDF。未声称核实更晚上传字段或截止时间。

本次只核对源码/资料并更新结构、图册与目录说明，没有重跑真实模型、硬件或此前 41 项软件测试。
