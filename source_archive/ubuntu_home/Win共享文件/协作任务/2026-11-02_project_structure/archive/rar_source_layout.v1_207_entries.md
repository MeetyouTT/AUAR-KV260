# AUAR·雪妃：200M 内 RAR 源码复现包目录

当前口径：按用户转述的赛事方老师说明，提交**完整实际源码、重建脚本、依赖清单和精简的关键说明**。这里给出你后续重新制作工程包时采用的目录，不参考现有 RAR，也没有生成一个可运行工程或比赛压缩包。

老师原话见[补充说明](evidence/teacher_submission_guidance.txt)。此前完整项目结构仍可用于本机开发归档，**本文件是当前工程 RAR 的收集范围**。

## 1. 包里到底放什么

建议压缩包名：`auar_xuefei_source.rar`。包内只有一个根目录 `auar_xuefei/`。

- 源码收齐 FPGA、KV260、Windows 及公共协议，按最终实际使用的版本整理。
- “源码”也包含 XDC、BD 创建 Tcl、自定义 IP 配置、必要初始化文件、原生头文件和资源定义。
- 重建脚本负责生成工程、综合实现、固件导出、原生编译、模型准备/编译和部署。
- 设计结论、指标、关键失败与 AI 纠错保留精简摘要和可追溯来源，不装整本日记与全部历史日志。
- 必须的少量原始角色/字体/提示音资源按授权收录；公开大型资源按固定来源和校验值准备。

下列目录是**目标设计**。`完整实际源码`表示该模块全部实际使用的源文件都应收齐，不是只放一个说明文件。`[条件]`项仅在最终采用时建立。脚本文件名是建议名称，当前没有在本次交付中实现。

## 2. RAR 内部目录树

```text
auar_xuefei/
├── README.md                              # 一页总入口：简介、环境、复现命令、正常结果和目录对照
├── license                                # 队伍原创内容的正式许可全文
├── third_party_notices.md                  # 代码、IP、模型、字体与角色资源的来源和许可
├── release.json                            # 源码版本、协议、目标平台、模型版本和关键SHA
├── package_manifest.csv                    # 实际装包文件及用途、大小、SHA；按真实内容生成
├── checksums.sha256                        # 包内文件校验；不把本校验文件自身列入
│
├── src/                                   # 全部实际使用的实现源码
│   ├── fpga/
│   │   ├── readme.md                       # PL模块、接口、工具版本和源码输入说明
│   │   ├── rtl/                            # 完整自研RTL；保留最终使用的实现
│   │   ├── include/                        # [条件] RTL头文件、参数与寄存器定义
│   │   ├── bd/
│   │   │   ├── create_bd.tcl               # 从零创建PS、DPU、互联、自研IP与连线
│   │   │   └── address_map.json            # 地址、中断、接口和ABI
│   │   ├── constraints/
│   │   │   ├── pins.xdc                    # 实际引脚、电平、驱动和速率
│   │   │   ├── clocks.xdc                  # 时钟及外部时序要求
│   │   │   └── exceptions.xdc              # [条件] 有依据的时序例外
│   │   ├── ip/
│   │   │   ├── custom/                     # [条件] 自定义IP源文件、封装元数据和Tcl
│   │   │   ├── ip_config.tcl               # 实际采用的IP版本、参数和生成步骤
│   │   │   └── dependencies.json           # 工具自带/外部IP的固定版本与取得方法
│   │   └── init/                          # [条件] 真正参与设计的MEM/COE等初始化输入
│   ├── common/
│   │   ├── pyproject.toml
│   │   └── aura_contracts/                 # 完整双端协议、结构、期限、错误和播放ACK源码
│   ├── kv260/
│   │   ├── readme.md
│   │   ├── pyproject.toml
│   │   ├── requirements.lock.txt           # ARM Python及实际依赖版本
│   │   ├── aura_board/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                     # 板端业务入口
│   │   │   ├── app/                        # 完整生命周期、业务状态机与事件源码
│   │   │   ├── camera/                     # 完整采集、缓冲、服务入口和恢复源码
│   │   │   ├── vision/                     # 完整YOLOX/YuNet/SFace、VART、调度及跟踪源码
│   │   │   ├── identity/                   # 完整人脸身份、登记、匹配、删除及拒识源码
│   │   │   ├── motion/                     # 完整目标选择、跟随、源时效、驱动和停止源码
│   │   │   ├── audio/                      # 完整MCP01、前端、VAD、ASR、播放和ACK源码
│   │   │   ├── dialogue/                   # 完整轮次、模型客户端、上下文与取消源码
│   │   │   ├── memory/                     # 完整摘要、检索、保留、来源和遗忘源码
│   │   │   ├── storage/                    # 建表、迁移、首次初始化和存储源码
│   │   │   ├── ui/                         # 完整GUI、视觉预览、字幕和设置源码
│   │   │   ├── avatar/                     # 完整角色、表情、口型与原生调用源码
│   │   │   └── diagnostics/                # 健康、指标、错误和公开日志导出源码
│   │   └── native/
│   │       ├── makefile                    # 或最终采用的原生构建定义
│   │       ├── dpu_bridge/                 # 实际自研C/C++源码与头文件
│   │       ├── motion_mmio/                # 实际自研C/C++源码与头文件
│   │       ├── pixel_bridge/               # 实际自研C/C++源码与头文件
│   │       └── avatar_renderer/            # 实际自研适配源码；外部依赖见third_party
│   └── windows/
│       ├── readme.md
│       ├── pyproject.toml
│       ├── requirements.lock.txt           # 最终Windows环境的实际依赖锁
│       ├── aura_host/
│       │   ├── __init__.py
│       │   ├── main.py
│       │   ├── server/                     # 完整API、路由、队列、实例和取消源码
│       │   ├── llm/                        # 完整27B/Ollama调用、提示与输出适配源码
│       │   ├── tts/                        # 完整OmniVoice、参考音色和PCM输出源码
│       │   ├── runtime/                    # 完整模型加载、GPU策略和进程管理源码
│       │   └── diagnostics/                # 完整计时、资源和健康源码
│       ├── scripts/
│       │   ├── setup.ps1                   # 后续实现：环境与依赖准备
│       │   ├── start.ps1                   # 后续实现：启动本项目服务
│       │   ├── stop.ps1                    # 后续实现：停止本项目所属进程
│       │   └── status.ps1                  # 后续实现：读取实际健康状态
│       └── ollama/
│           └── modelfile                   # 实际模型导入参数，权重位置通过配置指定
│
├── build/                                 # 只交重建定义，不交生成工程和构建输出
│   ├── readme.md                           # 构建前提、步骤、正常输出与失败说明
│   ├── scripts/
│   │   ├── check_environment.py            # 后续实现：核对工具、依赖和输入
│   │   ├── prepare_dependencies.py         # 后续实现：取得并校验固定公开依赖
│   │   ├── create_project.tcl              # 后续实现：在新输出目录创建工程
│   │   ├── build_fpga.tcl                  # 后续实现：综合、实现、报告、位流
│   │   ├── export_firmware.py              # 后续实现：生成并核对同次固件组合
│   │   ├── build_native.sh                 # 后续实现：ARM原生库构建
│   │   ├── reproduce.py                    # 后续实现：编排离线、硬件构建及验证模式
│   │   └── verify_package.py               # 后续实现：装包文件、SHA和输入检查
│   └── manifests/
│       ├── toolchain.json                  # 实际工具、补丁、容器和依赖版本
│       ├── platform.json                   # 器件、板卡、DPU指纹、频率与ABI
│       └── dependency_sources.json         # SDK、系统镜像、IP及参考源码的固定来源
│
├── board/                                 # 板端部署定义；固件与SO由脚本生成
│   ├── readme.md
│   ├── system/
│   │   ├── image_manifest.json             # 系统镜像、内核、XRT/VART、Python和固定来源
│   │   ├── packages.txt                    # 系统依赖及实际版本
│   │   └── patches/                       # [条件] 自定义系统、驱动和设备树的真实修改
│   ├── systemd/
│   │   ├── aura-camera.service             # 最终相机服务本体
│   │   ├── aura-business.service           # 最终GUI/业务服务本体
│   │   └── dropins/                       # [条件] 最终有效追加配置与加载顺序
│   ├── udev/                              # [条件] 实际采用的设备规则
│   ├── manifests/
│   │   ├── deployment.json                # 源码/资源/构建输出到目标路径的映射
│   │   └── startup.json                   # 服务、依赖、资源与初始化顺序
│   └── scripts/
│       ├── stage_rootfs.py                 # 后续实现：在空白目录生成部署树
│       ├── install.sh                      # 后续实现：安装已生成的程序与工件
│       ├── preflight.py                    # 后续实现：平台、模型、设备与绑定检查
│       ├── start.sh                        # 后续实现：按依赖顺序启动
│       ├── stop.sh                         # 后续实现：退出和执行者收尾
│       └── status.sh                       # 后续实现：读取状态
│
├── config/                                # 实际参数模板；不含个人库和本机密钥
│   ├── readme.md                           # 字段、单位、默认值与覆盖顺序
│   ├── common.example.json                 # 协议、网络、期限与日志
│   ├── camera.example.json                 # 相机格式、分辨率与帧率
│   ├── vision.example.json                 # 模型、调度与后处理
│   ├── identity.example.json               # 登记、阈值及设备数据目录
│   ├── motion.example.json                 # ABI、实测方向/行程、期限及控制参数
│   ├── audio.example.json                  # MCP01、ASR、前端和播放
│   ├── memory.example.json                 # 摘要、检索与保留策略
│   ├── character.example.json              # 角色、动作、提示音和渲染
│   └── windows.example.json                # 推理端点、解释器、GPU及共享目录外的权重路径
│
├── models/                                # 模型取得/适配/编译定义；不装大权重或xmodel
│   ├── readme.md                           # 模型位置、固定来源、准备和校验步骤
│   ├── manifest.csv                        # 模型、任务、后端、revision、文件、SHA和许可
│   ├── recipes/
│   │   ├── yolox.json                      # 实际采用模型的固定取得/提取及校验办法
│   │   ├── yunet.json                      # 浮点输入、预处理、校准、量化和编译配置
│   │   ├── sface.json                      # 浮点输入、对齐、校准、量化和编译配置
│   │   ├── audio_frontend.json             # 实际ASR/VAD/降噪/声纹依赖与CPU后端
│   │   ├── llm.json                        # 27B来源、revision、量化文件、参数及SHA
│   │   └── tts.json                        # OmniVoice与tokenizer的完整必要文件定义
│   ├── calibration/
│   │   ├── data_manifest.csv               # 公开校准集、划分、取得方式和固定输入
│   │   └── quantization_config.json        # 实际量化参数与编译目标
│   └── scripts/
│       ├── prepare_models.py               # 后续实现：下载/提取到指定模型专用目录
│       ├── verify_models.py                # 后续实现：逐文件校验
│       ├── quantize.py                     # 后续实现：实际采用的量化/适配源码
│       └── compile.py                      # 后续实现：生成与DPU匹配的编译模型
│
├── assets/                                # 必要原始资源；只保留最终使用的一套
│   ├── readme.md                           # 资源位置、用途、来源与许可
│   ├── manifest.csv                        # 资源文件、SHA与授权；大公开资源注明固定取得方法
│   ├── character/                         # 有权提交的角色模型、纹理、表情和动作原件
│   ├── fonts/                             # 实际字体及原许可
│   └── audio/
│       ├── reference/                     # 有权分发的选定参考音色与文本
│       └── cues/                          # 必要固定提示音，或其可验证的生成输入和脚本
│
├── sim/                                   # 测试台、输入和独立参考，不装大波形
│   ├── readme.md
│   ├── rtl/                               # 完整实际RTL测试台
│   ├── vectors/                           # 小型固定向量、随机种子与参数
│   ├── golden/                            # 可说明来源的参考结果或黄金模型
│   └── run.tcl                            # 后续采用的实际仿真入口
│
├── tests/                                 # 可复用的软件测试源码
│   ├── readme.md
│   ├── protocol/                          # 请求、取消、期限和播放ACK
│   ├── kv260/                             # 板端实际软件测试
│   ├── windows/                           # Windows实际软件测试
│   ├── integration/                       # 双端往返、断线、记忆和视觉运动接口
│   └── fixtures/                          # 小型公开/合成样例，不使用个人私库
│
├── data/                                  # 最小复现输入和关键结论数据
│   ├── readme.md
│   ├── public_data_manifest.csv            # 大公开数据的版本、划分、取得与校验
│   ├── small_samples/                     # 少量必要公开图像/音频/向量
│   ├── reference/                         # 期望输出、人工参考与容差
│   └── metrics.csv                        # 与报告结论对应的数值、条件和来源
│
├── skill/                                 # 实际提炼的可复用内容；数量按实际
│   ├── README.md                           # 范围、入口、效果、失效条件与来源
│   ├── command_guard_validation/           # 建议主题：执行监督；说明/流程/脚本/小样
│   ├── dpu_workflow_validation/            # 建议主题：模型适配、调度及时效
│   ├── voice_runtime_optimization/         # 建议主题：LLM/TTS、计时与记忆一致性
│   └── pynq_contract_testgen/              # 已有通用PYNQ离线初版，面向契约和调用/测试生成
│       ├── readme.md                       # 用法、适用范围及未验证边界
│       ├── workflow.md                     # 合同、HWH检查、生成、参考比对和复用流程
│       ├── contract_format.md              # AXI4-Lite uint32寄存器合同格式
│       ├── case_studies.md                 # 元数据缺项、迟到完成及两种布局的真实案例
│       ├── scripts/                       # 原有生成器、离线复现与打包脚本源码
│       ├── templates/                     # PYNQ驱动和测试脚本模板
│       ├── examples/
│       │   ├── adder/                     # 加法合同、合成HWH测试输入、模拟及参考
│       │   └── crc32/                     # CRC合同、合成HWH测试输入、模拟及参考
│       ├── tests/                         # 原有15项单元测试源码
│       ├── evidence/                      # 精简已有离线结果；不得写成已真板/跨板通过
│       └── license                        # 原有许可全文
│
├── report/                                # 提炼关键内容；正式报告PDF按后台独立交
│   ├── engineering_summary.md              # 架构、创新、设计取舍、结果与边界
│   ├── validation_summary.md               # 每项测试的输入、方法、结果、失败和局限
│   ├── optimization_summary.csv            # 同条件基线/优化后性能和资源对照
│   ├── tool_reports/                      # 精选综合/时序/资源报告或关键原文片段及来源
│   ├── ai_collaboration.md                 # 真实提示、关键回答、错误、修正与验证的摘录
│   ├── evidence_index.csv                  # 指标/结论到原记录、版本、命令与SHA的映射
│   └── requirements_matrix.csv             # 条款与包内材料的对应
│
├── docs/                                  # 精简而可完整执行的复现说明
│   ├── architecture.md                     # FPGA/板端/Windows职责与数据流
│   ├── interfaces.md                       # API、寄存器、时钟、期限和错误
│   ├── environment.md                      # 工具版本、2022.2选择理由与双端安装
│   ├── reproduction.md                     # 取得源码到构建、模型、部署及验证的完整顺序
│   ├── hardware.md                         # 器件型号、接线、供电、行程与标定
│   ├── measurement.md                      # 指标定义、测量方法、样本与统计
│   └── known_issues.md                     # 实际未完成项和重现条件
│
├── hardware/                              # 少量必要实物设计输入与参数
│   ├── bom.csv                             # 实际型号、数量和用途
│   ├── wiring.svg                          # 实际控制/供电与外设连接
│   ├── calibration.csv                     # 实测方向、脉宽、位置、范围和方法
│   └── source/                            # [条件] 实际自制电路/机构的小型原始设计
│
└── third_party/                           # 依赖来源、原许可与项目实际修改
    ├── readme.md
    ├── manifest.csv                        # 固定上游、commit、许可、SHA和取得步骤
    ├── patches/                           # [条件] 队伍对上游源码的真实修改
    ├── source/                            # [条件] 无法由固定公开来源取得的必要可分发源码
    └── licenses/                          # 实际依赖的原始许可
```

## 3. 体积预算

改用老师明确的源码复现口径后，不再给 DCP、XSA、预编译固件或大权重预留包内空间。

下面按**收集目录的未压缩逻辑字节数**设预算，总目标 100MB，给 200M 的 RAR 限制留充足余量。这是后续收集额度，不是已测得的工程体积，也不依赖猜测某个压缩比。

| 类别 | 对应内容 | 未压缩预算 |
| --- | --- | ---: |
| 实现源码 | `src/`全部自研实现与必要原生源码 | 30MB |
| 构建及必要第三方源码 | `build/`、`third_party/` | 10MB |
| 板端部署与参数 | `board/`、`config/` | 5MB |
| 模型定义与小型数据 | `models/`、`data/`，均无大权重 | 5MB |
| 必要原始素材 | `assets/`，只选最终实际资源 | 30MB |
| 仿真和测试源码 | `sim/`、`tests/` | 5MB |
| 精简说明和关键记录 | `skill/`、`report/`、`docs/`、`hardware/`及根文件 | 15MB |
| 合计 | 收集目标，可在类别间调整 | **100MB** |

若某类超预算，先查看是否混入构建输出、旧版本或重复数据；不得删减实际使用的自研代码或必要设计输入。最终硬条件仍为 **RAR 实际大小小于 200,000,000 字节**，并能完整解压、逐文件校验。

目前没有收集真实源码或压缩实测，不能把该预算写成“最终 RAR 已小于 200M”。

## 4. 哪些东西在重建时生成

建议重建输出写到源码包外的新目录，例如 `~/auar_build_01/` 或 `D:/AURABuilds/build_01/`：

| 从包内取得 | 重建产生的内容 |
| --- | --- |
| RTL、BD创建Tcl、XDC、IP定义与构建脚本 | Vivado工程、综合实现结果、DCP、BIT/BIT.BIN、XSA/HWH及工具报告 |
| 设备树/平台接口定义与导出脚本 | DTBO、XCLBIN、shell.json等实际配套部署文件 |
| C/C++、头文件及构建定义 | AArch64共享库和对象文件 |
| 固定模型来源、转换/校准/编译配方 | 所需浮点/CPU模型、量化结果与DPU xmodel |
| 发布清单、参数模板、服务和安装脚本 | 板端部署树与本机运行配置 |
| 测试台、输入、参考和执行脚本 | 波形、原始日志、逐项结果和统计 |

27B 权重和 Ollama 模型库始终在共享目录之外准备。下载脚本必须显式接受模型目录，不能默认把权重写进源码包。

角色模型、纹理、字体、固定提示音属于运行输入，不能一概当构建缓存省掉。有权分发的小型必要原件按上树保存；使用公开资源时固定来源、版本与 SHA。缺少可取得来源的必要资源必须解决后才算复现输入齐全。

## 5. 日记与证据怎样提炼

不要把整个 `logs/daily/`、全部聊天记录或几十份阶段报告原样装包。每个关键案例压缩成以下要素：

1. 目标与原问题：触发输入、实际表现及版本。
2. 判断与修改：采用了什么依据，哪段实现或参数发生了变化。
3. 验证与结果：命令、输入、预期、实测数值、样本数及仍存在的失败。
4. 可追溯来源：原记录标题/时间、文件SHA与对应源码版本；Skill中能复用的方法。

AI 协作保留真实提示、关键原回答、自我纠错和验证摘录。可以省去无关聊天与重复尝试，不能把后来写的总结当成历史原问答。关键综合报告文本/片段保留实际数值与来源，不需要复制生成工程或整套工具工作目录。原始大记录留本机保存。

### 当前PYNQ包怎样收录和描述

原包是[pynq-contract-testgen](../2026-11-02_pynq_skill/skill/pynq-contract-testgen/readme.md)，提交目录映射为 `skill/pynq_contract_testgen/`，保留其完整28个源/说明/证据文件，当前不含Python缓存的逻辑大小为86,438字节。只收其源文件即可，不必在RAR内再塞一份独立ZIP。

它根据AXI4-Lite接口合同和HWH生成PYNQ调用/测试代码，包含加法和CRC两种独立布局；不依赖AURA业务。按指南3.3.2的“从接口契约生成调用代码或测试骨架”示例，属于面向通用PYNQ的Skill方向。范围限当前支持的32位无符号标量寄存器协议，不扩大为DMA或AXI-Stream工具。

已有记录为15项单元测试和73个生成后模拟用例通过；未验证真实PYNQ环境、真实板卡、跨板和非作者复用。合成HWH是生成器测试的原始输入，可以随例子收录，不能当作可部署的真实Vivado元数据。其他三个主题包仍按各自实际范围提交，不因使用Python或KV260就自动归为PYNQ通用Skill。

## 6. 当前脚本需要特别处理的事项

以前的构建流程曾依赖约 125.1MB 的旧参考 DCP。**按老师这次口径，目标是让脚本从已交的 RTL、BD/IP定义与约束完成重建，包内不带这个旧 DCP。**

这要求在整理真实工程时修正该依赖，并实际跑通干净目录构建与输出检查；不能只删掉 DCP 文件而保留脚本中的强制引用。完整新综合/实现尚未因这份目录说明而通过，这一项在实际封包前必须核验。

同样，不能把原生 `.so` 或模型 `.xmodel` 省掉后只留一个空的“构建脚本”。脚本应包含实际依赖、版本、输入、生成命令、输出检查与失败退出，且验证过对应步骤。

## 7. 不放进这个 RAR 的材料

- 生成工程与工件：XPR、DCP、XSA/HWH、位流、DTBO/XCLBIN、预编译SO/对象文件、生成的xmodel和大波形。
- 全量开发日记、全部现场日志、历史重复包、废弃候选和旧预渲染序列。
- Python虚拟环境、软件安装目录、Docker镜像、系统镜像及下载缓存。
- 大模型权重、Ollama模型数据、个人数据库、人脸/声纹模板、私人录音和令牌密钥。
- 正式报告PDF、演示视频、高清实物照片、签署授权书和条件海报按赛事相应栏目另交；工程RAR只保留必要说明和关键记录。

上述范围只用于导出，不要求删除原电脑上的任何文件。

## 8. 本次交付与后续验收

本次交付：[纯文本RAR目录](rar_source_tree.txt)、[包内收集清单](rar_source_manifest.csv)、[体积预算](rar_source_budget.csv)、[源码提交要求映射](rar_source_requirements.csv)、[目录校验记录](rar_source_validation.json)。文件名和所有脚本均为后续整理建议，没有创建占位业务源码。

真实打包时依次核验：完整实际源码和设计输入、外部依赖可取得、干净目录重建、关键测试及实板验证范围、英文命名和本机配置清理、RAR实际字节数、完整解压和SHA。分别记录已通过与尚未验证的部分。

本轮仅设计目录、预算与记录格式；没有制作正式工程RAR，没有恢复实现/设备任务或进行模型调用。
