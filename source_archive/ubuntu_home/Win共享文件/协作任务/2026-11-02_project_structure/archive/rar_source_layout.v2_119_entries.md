# AUAR·雪妃：200M 内 RAR 源码复现包目录（v2）

**当前唯一提交目录，以本文件为准。** 采用用户最后提供的 v2：完整实际源码＋重建脚本＋必要输入＋精简关键说明。旧版已归档，不与当前版本并行执行。

包名建议为 `auar_xuefei_source.rar`，RAR 内只有一个 `auar_xuefei/` 根目录。本文是目录与验收要求，不表示业务文件已收齐、脚本已跑通或已生成 RAR。按用户要求，目前不进行工程构建。

## 1. 标签与范围

“本方案保留”是本队选择的交付内容，不等于官方指定了这些文件名。“条件项”仅在实际采用时保留。指南要求提交 Skill；PYNQ 这一具体方向和额外加分属于可选方向，本方案选择保留现有 PYNQ 包。

子目录若标“完整实际源码”，必须收齐最终使用的源文件，不创建空目录充数。保留现有包名、导入关系、诊断模块和真实配置命名；归档分组不要求重构代码。必要头文件、初始化数据和 IP 定义不能因为树中未逐个列出而省略。

## 2. 最终目录

```text
auar_xuefei/
├── README.md                              # 简介/器件/工具、架构、接口、复现顺序、目录对照及边界
├── license                                # 队伍原创内容的正式开源许可
├── third_party_notices.md                  # 代码/IP/模型/资源来源、许可及固定外部输入
├── checksums.sha256                        # 可选：实际包内文件校验，不包含自身
│
├── src/                                   # 全部实际实现，保留现有源码包布局
│   ├── fpga/
│   │   ├── rtl/                            # 实际自研RTL、参数、package及必要头文件
│   │   ├── bd/
│   │   │   ├── create_bd.tcl               # PS、DPU、互联、自研IP和连线的建图入口
│   │   │   └── address_map.json            # 地址、窗口、中断与ABI
│   │   ├── constraints/
│   │   │   ├── pins.xdc                    # 引脚、电平、驱动和边沿
│   │   │   └── clocks.xdc                  # 实际时钟约束；已有时序例外和其他XDC也须保留
│   │   ├── overlay/
│   │   │   ├── aura-visual-servo.dtsi      # 实际设备树overlay源
│   │   │   └── readme.md                   # 固件命名、接口与base DTB匹配要求
│   │   ├── ip/
│   │   │   ├── custom/                    # [条件] 实际自研封装IP源码及元数据
│   │   │   └── ip_config.tcl               # IP版本、参数、来源和生成步骤；只由建图链调用一次
│   │   └── xrt_metadata/                  # [条件] 选择从JSON/XML生成XCLBIN时的完整元数据输入
│   ├── common/                            # 共享协议单一源码；沿用真实包名与模块名
│   ├── kv260/
│   │   ├── requirements.lock.txt           # ARM环境实际依赖锁
│   │   ├── aura/                          # 实际板端源码包；包名若不同，保留原名
│   │   └── native/                        # 实际C/C++、头文件及原有makefile/CMake等构建定义
│   └── windows/
│       ├── requirements.lock.txt           # Windows环境实际依赖锁
│       ├── aura/                          # 实际模型服务源码包；保留原名和诊断模块
│       ├── ollama/
│       │   └── modelfile                   # 模型导入参数，权重位置由本机配置给出
│       └── scripts/
│           ├── start.ps1                   # 本项目服务启动及共享模块导入路径
│           └── stop.ps1                    # 本项目所属进程收尾
│
├── config/                                # 脱敏模板，字段和目标运行文件名按真实加载器
│   ├── readme.md                           # 原模板→实际目标文件映射；真实优先级和路径解析
│   ├── board_avatar_gtk.example.json
│   ├── board_camera_ui.example.json
│   ├── board_identity.example.json
│   ├── board_dialogue_model.example.json
│   ├── board_ui_services.example.json
│   ├── servo_calibration.example.json
│   ├── pan_follow.shadow.example.json
│   ├── timeline_memory.example.json
│   ├── anonymous_identity.example.json
│   ├── voice_latency.example.json
│   ├── model_manifest.example.json
│   ├── windows.model_inference.example.json
│   ├── windows.model_storage.example.json
│   └── toolchain_lock.example.json         # [条件] 程序确实需要时，从build/env.json统一生成
│
├── sim/
│   └── rtl/
│       ├── tb_registers.sv                 # 用现有真实测试台；以下名字是职责示意
│       ├── tb_pwm.sv
│       ├── tb_command_guard.sv
│       ├── vectors/                       # 此处固定为RTL向量位置，run.tcl按相对路径访问
│       └── run.tcl                        # 真实仿真入口，失败须返回非零
│
├── build/
│   ├── reproduce.py                        # 统一参数/日志/退出码的入口，调用Vivado等真实工具
│   ├── build.tcl                           # 建图→综合→实现→报告→BIT/XSA，不依赖历史DCP
│   ├── export_firmware.py                  # 生成并核对BIT.BIN、DTBO、XCLBIN、shell.json
│   ├── prepare_models.py                   # 取得/校验/改写/校准/量化/编译入口
│   ├── build_native.sh                     # 调用包内真实原生构建定义
│   └── env.json                            # 工具/补丁/平台/ABI/指纹/频率及固定输入
│
├── board/
│   ├── systemd/
│   │   ├── aura-camera.service
│   │   ├── aura-business.service
│   │   └── dropins/                       # [条件] 最终有效追加参数及加载顺序
│   ├── udev/
│   │   └── 99-aura-devices.rules            # [条件] 已采用的设备规则
│   ├── system/
│   │   ├── image_manifest.json             # 镜像/内核/XRT/VART/Python/base DTB的来源和校验
│   │   └── patches/                       # [条件] 实际系统、驱动、设备树修改
│   ├── deploy.json                         # 源→目标、权限、配置、解释器、服务、就绪和回滚
│   └── install.sh                          # 按deploy.json执行，安装失败须停止
│
├── models/
│   ├── readme.md                           # 各模型取得到部署的完整步骤与实际限制
│   ├── manifest.csv                        # 固定来源/revision/文件/SHA/许可/接口/预处理/目标
│   ├── adapt/                             # 原有导出、等价改写、校准、量化与编译适配源码
│   └── calibration/                       # 数据来源/划分、quant_info、arch及编译配置
│
├── assets/                                # 最终使用且有权交付的必要原始资源
│   ├── character/
│   ├── fonts/
│   └── audio/
│       ├── reference/
│       └── cues/
│
├── data/
│   ├── metrics.csv                         # 数值、单位、版本、条件、优化对照及证据来源
│   ├── samples/                           # 软件测试的小型公开/合成输入，不与RTL向量重复归档
│   └── expected/                          # 参考输出、人工转写和容差
│
├── tests/
│   ├── protocol/
│   ├── kv260/
│   │   └── bench_identity_stop.py          # [条件] 实际采用的验收脚本及其包内依赖
│   ├── windows/
│   └── integration/
│
├── skill/
│   ├── README.md                           # 各项范围、用法、实际效果、失败来源和边界
│   └── pynq-contract-testgen/              # 现有完整离线包，保留全部源/例子/证据/许可
│       ├── readme.md
│       ├── workflow.md
│       ├── contract_format.md
│       ├── case_studies.md
│       ├── license
│       ├── scripts/                       # generate.py、reproduce.py、package.py
│       ├── templates/                     # PYNQ驱动与测试模板
│       ├── examples/
│       │   ├── adder/                     # 合同、合成HWH、模拟、独立参考和向量
│       │   └── crc32/
│       ├── tests/
│       └── evidence/                      # 原有离线结果、日志及真实纠错说明
│
├── third_party/                           # [条件] 文中引用的必要上游源码/补丁/原许可
│   ├── source/                            # 必需且允许交付的第三方源，含IP引用的真实头文件
│   ├── patches/                           # 队伍对固定上游版本的实际修改
│   └── licenses/                          # 原始许可文本
│
└── report/
    ├── design_report.md                    # 正文源稿，覆盖AMD七项；正式PDF另交
    ├── validation_summary.md               # 实际输入/方法/结果/失败/局限及关键工具报告摘录
    └── ai_collaboration.md                 # 真实提示、回答、纠错和验证摘录
```

## 3. 按实际代码填入，不能照树重构

- `src/kv260/aura/`、`src/windows/aura/` 表示现有源码包；若实际名称不同，原样保留并在README说明映射。包内应收齐相机、视觉/调度、身份、运动、音频、对话、记忆、存储、界面、角色和诊断等实际模块。
- `src/common/` 的协议模块保留一个权威输入。启动/安装脚本明确导入位置或按同一清单复制，不手工维护互相漂移的两份代码。
- 配置文件的 `.example.json` 是模板，安装后文件名和位置以真实加载器为准，不能统一改成 `.local.json`；覆盖顺序必须实际实现。
- 模型运行时预后处理和VART封装在原源码位置保留一份；`models/adapt/` 收离线导出/改写/量化/编译流程，避免为了目录重复复制同一实现。
- 其他三个工程主题Skill可以按实际成熟度增加，数量不是赛事硬指标。当前优先完整保留现有PYNQ包，不删除其小型证据。

## 4. 重建脚本验收边界

这份目录不等于已完成脚本实现。后续需分别验证：

1. **输入齐全。** 自研源码、IP定义、实际约束、必要头文件和初始化数据都在包内或来自固定可取得依赖；检查范围包括Tcl、XML、XCI和C/C++引用。
2. **没有历史工作目录依赖。** 不读取旧工程的DCP、DTBO、BIT.BIN、XCLBIN或辅助Python脚本。本轮工具自己生成并读取的DCP允许使用。
3. **模型流程完整。** 固定来源和校验、必要改写、校准、量化、编译都有实际入口，生成物不混入源码包。
4. **固件接口一致。** 本次BIT与XSA配对，DTBO与匹配base DTB合并检查，XCLBIN的地址/拓扑/连接/时钟与硬件一致。
5. **部署可复现。** `deploy.json` 与脚本行为一致，原有效服务参数不丢失，配置/权限/解释器/资源和就绪检查都有落实。
6. **真实失败会退出。** 工具失败、输入缺失、产物为空或接口不匹配，必须返回非零；日志中区分PASS、FAIL和NOT_RUN。
7. **独立新目录重跑。** 实际完成工具构建与输出检查后，才能填写该环境下通过；Windows与实板运行另行验收。

已发现但尚未验证解决的问题：旧构建链依赖历史DCP和旧bundle；DPU组件中存在旧绝对头文件路径；`875ca912…` XCLBIN带本项目M3构建元数据，不能未经追溯就登记为官方base shell；固定base DTB需要可重复取得的方法。用户已要求先不构建，以上仍为待办。

## 5. 体积和独立上传材料

按未压缩收集量100MB规划：实现源码30MB，构建/必要上游源码10MB，部署和配置5MB，模型配方/小数据5MB，必要原始素材30MB，仿真/测试5MB，Skill/报告及根文件15MB。分类额度可调整，最终以RAR实际大小小于200,000,000字节为准，目前尚未封包或测得工程RAR大小。

不装入：生成工程、历史DCP、BIT/XSA/DTBO/XCLBIN、预编译SO/对象文件/生成xmodel、大权重、虚拟环境、缓存、个人数据库、密钥及全量历史日记。PYNQ合成HWH是生成器原始测试输入，可随例子保留，不能当实板部署元数据。

正式报告PDF、MP4演示、高清照片、签署授权书及按通知准备的海报按后台栏目独立交；开源链接登记到README。大语言模型权重继续放共享目录之外。

## 6. 当前入口与状态

- [纯文本目录树](rar_source_tree.txt)
- [逐项收集清单](rar_source_manifest.csv)
- [源码交付要求映射](rar_source_requirements.csv)
- [体积预算](rar_source_budget.csv)
- [目录静态检查](rar_source_validation.json)
- [用户提供的老师补充口径](evidence/teacher_submission_guidance.txt)
- [现有PYNQ离线包说明](../2026-11-02_pynq_skill/readme.md)

当前只更新目录文档与索引，没有进行新的工程构建、模型推理、部署或RAR压缩。先前准备的独立源码副本与脚本草稿未被标为构建通过。
