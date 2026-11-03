# AUAR·雪妃：RAR源码复现包定稿结构（方案A）

**唯一当前提交结构：方案A，`src/` 对应原 `aura/` 运行根。** 保留实际 `board/host/common/ui/tools/scripts/config/models/assets/data/hardware/tests` 等相对位置，不再拆成 `src/kv260/aura`、`src/windows/aura`。旧目录文档已归档，本文件及配套树/CSV为当前收集依据。

建议包名：`auar_xuefei_source.rar`，RAR内唯一根目录为 `auar_xuefei/`。目录名只负责归档；最终源码版本须按真实发布清单回收，不能把较早的通用开发树当成整机最终版本。

本文是修订后的目录和验收说明，未收集正式工程包、未制作RAR、未启动Vivado综合实现或设备部署。脚本可执行性、完整重建及实板运行仍未验证。按用户要求，本轮仅修改文档。

## 1. 组织原则

- `src/` 是运行根。`common/config.py` 的 `PROJECT_ROOT = Path(__file__).resolve().parents[1]` 保持不改；`board`、`host`、`common` 是同级导入包。
- `src/config`、`src/models`、`src/assets`、`src/ui`、`src/data`、`src/hardware` 等被代码按运行根寻址的内容必须保留原相对位置。
- 顶层 `board/` 是部署定义，`src/board/` 是运行源码；顶层 `data/` 是投稿指标和精选证据，不能替代 `src/data/`；顶层 `skill/` 是赛事Skill，不能替代运行根原有 `src/skills/`。
- “本方案保留”表示本队选择，“条件项”表示实际采用才收。文件名不是官方强制列表；没有的目录不创建空占位。
- 不为目录整齐重构代码、重命名模块或搬移诊断功能；必要的其他文件与依赖按代码引用继续收齐。

## 2. 完整目录

```text
auar_xuefei/
├── README.md                              # 简介/器件/版本、架构、接口、复现步骤、目录对照和边界
├── license                                # 队伍原创内容的正式开源许可
├── third_party_notices.md                  # 代码、IP、模型、资源和固定输入的来源/版本/许可
├── checksums.sha256                        # 可选：实际装包文件SHA，不包含自身
│
├── src/                                   # 原aura运行根；完整保留最终实际源文件和相对位置
│   ├── board/                             # 完整板端源码，不新造aura_board包名
│   │   ├── fusion/
│   │   ├── identity/
│   │   ├── interaction/
│   │   ├── motion/
│   │   ├── runtime/
│   │   ├── vision/
│   │   └── visual_timeline.py
│   ├── host/                              # 完整实际Windows/主机源码，其他现役入口也须收齐
│   │   ├── __init__.py
│   │   └── model_service/
│   ├── common/                            # 完整实际共享层，保留全部引用模块及版本约定
│   │   ├── config.py                      # 运行根和配置校验器原样保留
│   │   ├── contracts.py
│   │   └── schemas/                       # 实际协议schema原样保留
│   ├── ui/                                # 真实布局/令牌/manifest数据，不与interaction代码混淆
│   │   ├── avatar_board_manifest.json
│   │   ├── board_touch_layout.json
│   │   ├── ui_layout_spec.json
│   │   ├── ui_state.schema.json
│   │   └── ui_tokens.json
│   ├── tools/                             # 完整实际GUI、相机、语音、模型等入口和辅助源码
│   │   ├── aura_project.py                # 既有框架doctor/demo/replay等；不代表最终整机READY
│   │   ├── aura_host.py
│   │   ├── run_project.sh
│   │   ├── run_project.bat
│   │   ├── start.ps1                      # [条件] Windows启动入口，可保留其实际原位置/名字
│   │   └── stop.ps1                       # [条件] Windows停止入口，可保留其实际原位置/名字
│   ├── scripts/
│   │   └── package_project.py             # 原框架打包工具源码；不直接当最终整机收集白名单
│   ├── config/
│   │   ├── readme.md                      # 两套加载体系、真实文件名、字段及生成/安装映射
│   │   ├── runtime.sim.json               # 无敏感字段的完整有效仿真配置，默认文件名不改
│   │   ├── runtime.experiment.sim.json     # [条件] 实际使用的实验仿真配置
│   │   ├── runtime.reference.example.json  # [条件] 从有效原配置脱敏，使用前生成真实运行文件
│   │   ├── runtime.kv260.example.json      # 从有效原配置脱敏；旧框架profile不等于正式业务配置
│   │   ├── model_manifest.json            # doctor固定读取的清单，原名保留；不是权重文件
│   │   ├── source_import_manifest.json    # 脱敏来源/导入清单，保留实际结构
│   │   ├── servo_calibration.example.json  # 校准模板，生成时保持原程序期望的名字
│   │   ├── toolchain_lock.json            # 与build/env.json统一来源，不独立手工维护两份版本
│   │   ├── board_avatar_gtk.example.json
│   │   ├── board_camera_ui.example.json
│   │   ├── board_identity.example.json
│   │   ├── board_dialogue_model.example.json
│   │   ├── board_ui_services.example.json
│   │   ├── pan_follow.shadow.example.json
│   │   ├── timeline_memory.example.json
│   │   ├── anonymous_identity.example.json
│   │   ├── voice_latency.example.json
│   │   ├── model_inference.example.json    # Windows模板，最终安装为真实加载器期望的文件
│   │   ├── model_storage.example.json      # 权重位置由本机填写，LLM不下载到共享源码目录
│   │   └── experiments.json               # [条件] 实际使用且已脱敏的实验定义
│   ├── models/
│   │   ├── readme.md                      # 取得、校验、适配、量化、编译及使用顺序
│   │   ├── vision/
│   │   │   ├── yunet_2022mar.onnx         # [条件] 有权分发且选定profile使用的固定原始模型
│   │   │   └── sface_2021dec.onnx         # [条件] 实际采用时随包或提供固定取得方法
│   │   ├── adapt/                        # 实际导出/改写/校准/量化/编译源码，不重写已有流程
│   │   └── calibration/                  # 校准集定义、划分、量化信息、arch及编译配置
│   ├── assets/                           # 最小必要测试资源与资源约定，不装全量旧帧和可再生缓存
│   ├── data/                             # 运行时数据必须位于PROJECT_ROOT下
│   │   ├── calibration_manifest.json
│   │   ├── test_manifest.json
│   │   └── golden/
│   │       └── framework_frames.jsonl
│   ├── hardware/                         # 原有模块/资料，必要引用原样保留
│   ├── tests/                            # 原软件/系统测试，保留各测试及fixtures的相对位置
│   │   ├── __init__.py
│   │   ├── framework/
│   │   ├── data/
│   │   ├── fixtures/
│   │   └── bench_identity_stop.py        # [条件] 收回的实际硬件验收源码，其他依赖同时收齐
│   ├── skills/                           # [条件] 业务实际引用的技能目录，区别于顶层赛事skill
│   ├── docs/                             # [条件] 源码/原工具实际引用的必要说明
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── requirements-live.txt
│   ├── requirements.windows.lock.txt      # [条件] Windows实际依赖锁，沿用既有真名亦可
│   ├── requirements.kv260.lock.txt        # [条件] ARM实际依赖锁，不能混用x86 wheel
│   ├── fpga/                             # 额外FPGA实现输入，不影响现有Python导入
│   │   ├── rtl/
│   │   │   ├── visual_servo.sv
│   │   │   └── disabled_audio.sv          # 若真实BD仍引用此兼容模块，则属于必要源码
│   │   ├── bd/
│   │   │   ├── create_bd.tcl
│   │   │   └── address_map.json
│   │   ├── constraints/                  # 保留实际XDC名称和调用顺序，不为树拆分重命名
│   │   ├── overlay/
│   │   │   ├── aura-visual-servo.dtsi     # 目标overlay源；尚待实现并验证语义/合并
│   │   │   └── readme.md
│   │   ├── ip/
│   │   │   ├── custom/                   # [条件] 实际自研IP完整源和封装元数据
│   │   │   └── ip_config.tcl
│   │   └── xrt_metadata/                 # [条件] 选元数据重建XCLBIN路线时保留完整输入
│   ├── native/                           # [条件] 源树外收回的原生源码/构建定义；已在tools等处则原位
│   └── third_party/                      # [条件] 必要上游源码、项目补丁和原始许可
│
├── sim/
│   └── rtl/
│       ├── tb_nominal.sv                  # 四份真实测试台，不用早期示意名称
│       ├── tb_wide.sv
│       ├── tb_pulse_guard.sv
│       ├── tb_servo.sv
│       ├── vectors/                      # [条件] 实际测试台需要的向量，保持真实相对路径
│       └── run.tcl                       # 目标仿真入口，本轮结果写源码包之外
│
├── build/
│   ├── reproduce.py                      # 薄编排：复用实际CLI和工具，不另造业务运行时
│   ├── build.tcl                         # 目标硬件构建入口；不依赖历史DCP/旧工作目录
│   ├── export_firmware.py                # 目标固件导出、报告检查、配对和元数据校验入口
│   ├── prepare_models.py                 # 目标模型准备入口，调用包内真实适配源码
│   ├── build_native.sh                   # 目标ARM原生构建，沿用实际makefile/CMake等定义
│   └── env.json                          # 工具/补丁/器件/指纹/ABI/频率/依赖和固定输入
│
├── board/                                # 部署定义，不是Python的board包
│   ├── systemd/
│   │   ├── aura-camera.service            # 使用真实最终服务名称和有效参数
│   │   ├── aura-business.service
│   │   └── dropins/                      # [条件] 最终有效追加配置及加载顺序
│   ├── udev/                             # [条件] 实际设备规则
│   ├── system/
│   │   ├── image_manifest.json            # 系统镜像/内核/XRT/VART/Python及base DTB的来源校验
│   │   └── patches/                      # [条件] 实际系统、驱动与设备树修改
│   ├── deploy.json                       # 保持src运行根整体关系，映射文件/权限/配置/服务/就绪
│   └── install.sh                        # 目标安装入口，模板生成后保持代码真实文件名
│
├── data/                                 # 投稿指标和精选证据，不替代src/data
│   ├── metrics.csv                       # 数值/单位/版本/条件/对照/来源及SHA
│   └── expected/                         # [条件] 额外比对结果，不重复搬走运行根golden
│
├── skill/
│   ├── README.md                         # 范围、用法、效果、失败来源和边界
│   └── pynq-contract-testgen/             # 现有完整离线包，全部源/例子/证据/许可原样保留
│       ├── readme.md
│       ├── workflow.md
│       ├── contract_format.md
│       ├── case_studies.md
│       ├── license
│       ├── scripts/
│       ├── templates/
│       ├── examples/
│       │   ├── adder/
│       │   └── crc32/
│       ├── tests/
│       └── evidence/
│
└── report/
    ├── design_report.md                  # 七类内容及完整复现说明，正式PDF按后台另交
    ├── validation_summary.md             # 必须含真实测试命令/退出码/集合及资源时序摘要；未跑标NOT_RUN
    └── ai_collaboration.md               # 真实提示、回答、纠错及验证摘录
```

## 3. 运行根、导入和配置规则

### README必须说明的内容

1. 作品与实际器件型号；Vivado/Vitis 2022.2及配套Vitis AI/DPU版本，解释选择2022.2的实际配套依据，不只列版本名。
2. 一张真实架构图、软硬件划分，以及主要接口的端点/地址窗口/时钟/期限/错误。
3. 输入准备、模型/资源准备、软件自检、RTL验证、硬件构建、固件导出/部署的执行顺序；命令以最后真实脚本的参数为准，未完成步骤如实标记。
4. 与官方推荐结构的对照：软件测试在src/tests、运行数据在src/data，顶层data是投稿指标；src/board是源码，顶层board是部署定义。
5. 模型和角色素材哪些随包、哪些需要另行准备；样例能验证什么，是否包含原版形象；已知问题及所有未验证边界。

README可以精简并引用包内报告，但不能因限制一页而省掉执行所需的输入、参数和路径说明。

采用方案A后，`common/config.py` 所在位置为 `src/common/config.py`，其 `parents[1]` 正好是 `src/`。因此 `project_path("config/runtime.sim.json")`、`project_path("models/...")` 和 `project_path("data/...")` 都落在 `src/` 内；不能再把这些输入搬到RAR顶层。

已检查的 `tools/aura_project.py` 会把自己的运行根加入 `sys.path`，不必机械地改四个入口。其他实际入口逐个检查工作目录、解释器和导入位置；通信版本验证放在真实协议边界，不能用路径设置代替握手测试。

从RAR根目录使用既有CLI时，相对配置参数是相对于运行根的。后续复核命令示例（本轮未执行）：

```bash
python3 src/tools/aura_project.py --config config/runtime.sim.json doctor
python3 src/tools/aura_project.py --config config/runtime.sim.json demo --out /tmp/auar_framework_demo_01
```

不能把参数写成 `--config src/config/runtime.sim.json`，否则运行根会再拼接一层 `src/`。`--out` 必须选尚不存在的新目录。

配置分两套：

- 主配置走 `load_config/validate_config`，顶层十个键精确匹配，并继续检查嵌套字段：`schema_version/release_id/environment/vision/freshness/scheduler/motion/identity/dialogue/logging`。不能只按十个键写空骨架，应从完整有效配置脱敏。
- GUI、相机、模型服务等子系统配置按各自真实加载器处理，不能假设统一支持相同覆盖规则。
- 无敏感内容的仿真配置、doctor固定读取的 `model_manifest.json` 按原名收录；其他模板由安装流程映射到真实文件名和位置，不统一改成 `*.local.json`。
- 配置中权重位置必须可准备；LLM权重和Ollama库仍在共享目录之外。个人数据、模板、密钥和本机私有值不入公开包。

可直接采用[配置与运行根说明](runtime_config_readme.md)作为后续 `src/config/readme.md` 的内容基础；它是说明文档，不是已生成的业务配置。

## 4. 现有CLI和旧打包器的边界

现有 `aura_project.py` 可以复用为框架doctor/demo/replay等入口，但其配置校验禁止物理运动，doctor的能力字段也包含历史框架状态。模拟doctor返回0只说明该选定框架配置的自检条件满足，不代表当前三模型、MCP01、GUI、Windows推理和转轴已完成整机验收。

`scripts/package_project.py` 明确输出 `FRAMEWORK_SOURCE_BUNDLE_NOT_DEVICE_RELEASE`，其旧白名单不是整机最终交付清单。完整源码应按最终发布清单回收；独立相机入口、实际Windows服务、原生适配和交付中的较新修订都要纳入，不直接从通用开发树随意选版本。

`build/reproduce.py` 只编排真实软件入口、RTL测试和硬件工具。README中的命令和参数必须与最后实际实现的CLI一致；不能把当前草稿当已完整实跑的复现脚本。

## 5. RTL与固件链修正

四份真实测试台为 `tb_nominal/tb_wide/tb_pulse_guard/tb_servo`。后续仿真入口应重新执行测试，产生源码版本、输入、工具、退出码和结果集合。新 `result.json` 写在本轮包外输出目录，由构建入口读取；不通过携带历史PASS文件来满足新构建前置断言。

**结果文件接口约定（目标设计，尚未实现或实跑）：** 编排入口接收 `--out <OUT>`；RTL阶段把结果写入 `<OUT>/rtl/result.json`，硬件入口通过显式参数 `--rtl-results <OUT>/rtl/result.json` 接收。其他实际参数可在实现时统一，但必须在同一封版中保持调用方、被调方及README一致。缺文件、测试集合缺项、退出码失败或源码指纹不匹配时拒绝继续；不能默认回读作者的validation目录或历史结果。

**验证摘要必须保留：** 实际执行的四个tb命令、工具版本、源码标识、逐项退出码和通过/失败/未执行集合；综合实现的实际资源、时钟、setup/hold、DRC与关键性能摘要，并登记来源。未执行填写NOT_RUN，历史数据标原版本，不补造本轮通过。这些关键文字/数值很小，不要求装进整套工程或全量日志。

历史结果可以摘录到验证报告，但不得被当作新源码已通过。构建失败、缺项、空输出、测试未执行均须返回非零，并区分PASS/FAIL/NOT_RUN。

后续仍需实际解决并验证：

1. 去除历史DCP、旧bundle和旧辅助脚本的输入依赖；工具本轮生成并使用的DCP正常保留在输出目录。
2. DPU IP组件的旧绝对头文件引用改成可定位输入，并核对原始内容、配置与指纹。
3. overlay源、固件名、时钟/地址及设备树结构匹配；DTBO与指定base DTB完成合并/语义检查，同源文本比对不能单独证明板级兼容。
4. 为dtc、fdtput、fdtoverlay等实际使用工具固定来源和版本，base DTB必须有可重复取得的方法。
5. 为XCLBIN选择并验证固定取得或元数据重建路线。现役875ca912…文件含本项目M3构建记录，不能直接宣称它是官方base shell；没有闭环前不能因“KV260用不到”而删掉此环节。
6. 保留并适配报告解析、位流/XSA配对和独立检查逻辑，全部从本次输出读取，不动态导入作者旧工作目录。
7. 安装映射、配置生成、服务有效参数、资源定位和就绪检查与新运行根一致。Windows与实板运行分别验收。

## 6. Skill、体积和收集规则

本方案主Skill为现有 `pynq-contract-testgen`，整包保留其28个源/说明/证据文件，不在RAR内再套ZIP。已有记录为15项单元测试和73个生成后软件模拟用例通过；真实PYNQ、实板、跨板和非作者复用未验证。两机若统计大小不同，以同一封版的逐文件SHA清单对齐，不把某个KB数字当作验收依据。

### 素材采用源码复现口径，不为缩包改画面

本包不按历史 `assets/avatar` 整目录收集，也不因其体积改用WebP、降低帧率或改变原加载器。源码包主要保留生成/加载代码、格式/状态/尺寸/时序定义、资源来源及少量有权分发的可用测试样例。与最终正式入口无关的旧候选帧库不入包；当前真实运行依赖的资源不能仅因日期旧而排除。

已只读确认：`scripts/board_export.py` 从已有PNG生成 `frames.rgb565`、资源manifest及C头文件；`prepare_avatar_frames.py`处理原视频/原帧，部分流程还依赖外部matting工程。因此可再生成的RGB565、重复导出和全量预渲染缓存不入包；生成原输入的来源、依赖与参数仍需说明。

**收录口径：历史全量角色帧和frames.rgb565不随工程源码包携带；保留实际使用的生成/加载源码及资源定义。需要原版画面时，按说明准备其原视频/源帧或角色原件；默认样例只用于验证对应工程机制，不冒称已复现原版形象。** 本轮没有转码、抽帧、生成样例或验证渲染，也不声称原素材已具备公开取得来源。

源脚本不能凭空生成缺失的私人PNG/MP4。若选择不交原素材，也没有可取得来源，就应在README写明原形象复现范围受限；不能把老师的“源码＋脚本”解释成所有必要输入都可缺失。权重、素材、系统镜像同样以清楚的输入约定和准备方法支撑复现。

建议未压缩收集预算仍为100MB：实际业务/硬件源码20MB，构建和必要上游源码8MB，配置/部署2MB，模型输入/适配/小数据45MB，最小资源与样例预算15MB，测试/仿真5MB，Skill/报告及根文件5MB。15MB不是现有avatar目录的测得体积；不以该预算代表历史帧库。各类可调整。模型额度考虑可分发的约37MB SFace输入；是否随包按实际用途与许可决定。100MB是规划，不是已测体积；原目录总字节也不能直接等同RAR大小，最终RAR须实测小于200,000,000字节。

不收历史重复、缓存、虚拟环境、旧生成工程、预编译SO、BIT/XSA、生成xmodel、大权重和个人数据。必要输入、原许可、小型Skill证据必须保留；不能一律按 `.pyi` 或 `.log` 后缀排除。现有大目录按明确清单选择，不能整棵复制旧模型库或所有预渲染素材。

正式PDF、MP4演示、高清实物照片、签署授权书和条件海报按后台栏目另交；工程内保留源稿和关键说明。

## 7. 当前文件与验证范围

- [纯文本目录树](rar_source_tree.txt)
- [逐项收集清单](rar_source_manifest.csv)
- [源码交付要求映射](rar_source_requirements.csv)
- [体积预算](rar_source_budget.csv)
- [目录静态检查](rar_source_validation.json)
- [配置与运行根说明](runtime_config_readme.md)
- [用户提供的老师口径](evidence/teacher_submission_guidance.txt)
- [现有PYNQ离线包说明](../2026-11-02_pynq_skill/readme.md)

静态检查只覆盖目录、路径、命名、映射、预算和文档链接；不等于工程构建或运行通过。本轮没有新建业务源码、执行综合实现、模型调用、设备访问或RAR压缩。
