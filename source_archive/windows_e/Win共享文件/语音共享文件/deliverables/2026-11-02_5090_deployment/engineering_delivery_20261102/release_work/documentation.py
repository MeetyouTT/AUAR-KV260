from common import *
def put(n,s):
    f=ROOT/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes((s.strip()+'\n').encode())
for n in ['Apache-2.0.txt','Droid-COPYRIGHT.txt','font_manifest.json']:
    copy(P/'aura/assets/fonts'/n,ROOT/'licenses/font'/n)
copy(QA/'windows_host_unit.txt',ROOT/'data/results/windows_model_host_unit.txt')
copy(QA/'native_protocol.txt',ROOT/'data/results/native_protocol.txt')
put('readme.md',r'''
# AUAR·雪妃 | KV260 工程交付

AMD 初级组自主命题 · 工程归档 2026-11-02。作品由 KV260、USB 相机、触控显示、MCP01 音频设备、单轴机构及局域网 Windows 推理主机构成。目录名和代码中的 AURA 沿用开发工程标识。

## 在另一台 Ubuntu 20.04 上先跑

将主 RAR 解压到新目录，进入解压出的 aura。两个命令只用 Python 3.8+ 标准库，按顺序使用一个进程执行检查。原始包可放在 U 盘，验证结果写到新目录。首次整包 SHA-256 校验会顺序读一次参考 DCP。

~~~sh
python3 -B build/scripts/verify.py
python3 -B build/scripts/reproduce.py --out "$HOME/auar-check-01"
~~~

第一条逐文件验证，也检查 380 项板端业务文件、启动配置、25 项跟随控制文件、三个 DPU 模型、配套固件和两组 RPC 原记录。第二条运行转轴软件夹具、三个专题技能和独立的 PYNQ 生成测试。每一步的退出码和日志见输出目录的 summary.json。再次运行请选择新的 --out。原机 Ubuntu 20.04 复跑与交付文件复验见随包外的 verification 文件夹。

## 从哪里看工程

| 工作 | 位置 | 可以核对的内容 |
| --- | --- | --- |
| FPGA 设计 | src/fpga、build/scripts、build/reports | 两个自研 RTL 模块、基础和结果 BD、约束、DPU/IP 输入、旧增量参考 DCP、实际时序与资源报告 |
| 仿真与参考 | sim、data/reference、data/results/xsim | 四个 RTL 测试台、仿真波形、期望输出及当前转轴控制的仿真夹具 |
| KV260 业务 | src/software、board | 带原始包布局的 GUI、语音、身份、记忆及设备适配，固件、启动入口与部署清单 |
| 视觉与转轴 | src/camera、src/vision_quantization、src/motion、models | DPU 运行和调度、图像采集、跟随控制、CPU 跟踪及量化/原生接口源码；当前跟随版本在 src/motion/follow |
| 玩偶与 Windows 推理 | src/avatar、src/windows | 原生雪妃渲染 C/C++、选定语音参考、27B 与 TTS 的 Windows 服务和环境锁 |
| 数据与报告 | data、report | 最新性能原始采样、五对公开请求的数据、三份 XIR 实际解析、设计报告、图和 AI 协作记录 |
| 三个技能 | skill | A 运动命令保护、B DPU 调度与感知时效、C 语音大模型运行优化，另附 PYNQ 契约测试生成 |
| 来源与交付边界 | third_party_notices.md、board/readme.md、report/release_status.md | 第三方材料、设备专属配置、验证条件、历史缺陷和当前结果 |

## 三种复现工作

* **复查代码、仿真证据与性能。** 使用上面的低核入口。四个 RTL bench 可在装了 Vivado 的工作站按 skill/command_guard_validation/readme.md 重新运行。性能表可从三模型和两类推理的真实原始记录重算。
* **重建 FPGA。** 见 build/readme.md。Vivado/Vitis 2022.2 和原参考 DCP 对应现役平台。归档中的 board/firmware 是历史实际配套工件。工程创建、从原已布线检查点导出以及 Bootgen 对照均在打包期间独立复跑。
* **准备实物部署。** 见 board/readme.md 和 src/windows/readme.md。板侧根文件系统暂存和 Windows 模型准备均有独立入口。CPU 模型/板端 wheel 在 auar_board_audio_dependencies.zip 中，放在主 RAR 旁。27B、OmniVoice 和工具安装按固定来源准备。已有板上的私有身份、声纹模板与对话数据留在所属设备。

在现役设备上运行与在空白板卡上重新安装是不同的验证条件。已有演示应保留板上个人数据和当次开机绑定，转轴按当前位置继续。下方文档列出实测和未覆盖的部分。
''')
put('build/readme.md',r'''
# FPGA 重建

发布物针对 xck26-sfvc784-2LV-c，板定义 kv260_som 1.4 与 kv260_carrier 1.3。Vivado/Vitis 2022.2 与原 PetaLinux 5.15.36-xilinx-v2022.2、DPUCZDX8G B4096 系统配套。src/fpga/inputs 保存基础 BD/XCI，visual_servo.sv、disabled_audio.sv 和 pin.xdc 是最终自定义输入。PWM 连接 E10、LVCMOS33、DRIVE 8、SLOW。src/fpga/reference/platform.xpr 是原工程索引，路径移机后使用下面的生成入口。仓库的 vendor 子目录保留原工程用到的三组非工具内置 IP 输入，包括旧 IP 缓存中被引用的文件。

在工程根目录，针对自己的 AMD 安装根目录执行以下命令。构建输出必须位于工程之外的全新目录。Vivado 本身以及商业 IP 的工具许可按原开发环境准备。

~~~sh
export XILINX_VITIS=/opt/Xilinx/Vitis/2022.2
export VIVADO_BIN=/opt/Xilinx/Vivado/2022.2/bin/vivado
python3 -B build/scripts/fpga.py check
python3 -B build/scripts/fpga.py prepare --out "$HOME/auar-implementation-01"
python3 -B build/scripts/fpga.py implement --out "$HOME/auar-implementation-01"
~~~

prepare 创建工程、绑定接口和地址、验证 BD、生成 IP 并写入 wrapper。implement 单作业综合，使用随包的 ac5f85a1… 参考 DCP 做增量布局，布线以后检查时序及 DRC，再重新打开本轮生成的已布线 DCP，导出含 bit 的 XSA。也可以对新目录执行 fpga.py build 一次编排两个阶段。reference/incremental.dcp 是窄范围前版的布局参考；最终 wide 已布线检查点的历史 SHA 为 933c712d…，二者用途不同。build/original 保留原始开发脚本供追溯。原脚本在工程模式末步导出 XSA 时找不到手工写出的 bit，发布入口直接采用成功的“从 routed checkpoint 非工程模式导出”路径。

在已有布局布线结果上单独复跑导出时，可用 fpga.py export --checkpoint /path/to/source_routed.dcp --out /new/place。原 wide DCP 保存在开发 Ubuntu 的 ~/aura-pan-wide-20261028/implementation/source_routed.dcp，主 RAR 中的 wide.xsa 和预构建固件可直接做交付校验。全量 implement 也会重新生成此阶段的 DCP。

~~~sh
export BOOTGEN="$XILINX_VITIS/bin/bootgen"
python3 -B build/scripts/pack_firmware.py \
  --xsa "$HOME/auar-implementation-01/implementation/visual_servo_source_implemented.xsa" \
  --bit "$HOME/auar-implementation-01/implementation/export-resume/visual_servo_source.bit" \
  --out "$HOME/auar-firmware-01"
~~~

固件入口核对同次 bit 与 XSA 的配置数据，比较已冻结的 HWH 后生成 .bit.bin，并配套相同接口的 DTBO、XCLBIN 与 shell.json。单元和端口发生改变时须重新生成设备树和对应的 XRT 工件。检查读者重新实现的输出应关注关键接口、时序、路由及 DRC，见 build/reports。原 wide 实现 setup WNS 为 0.001 ns，hold WHS 为 0.000 ns，DRC error 为 0。本轮新目录复跑的结果见 build/reports/clean_directory_validation.json，原始综合、布局、布线的结果与日志日期另行保留。低核机器优先做 check 和根目录的 reproduce，完整实现需要安装工具并预留运行内存和磁盘。
''')
put('report/release_status.md',r'''
# 交付版本与实测边界

| 子系统 | 本包的依据 | 验证范围 |
| --- | --- | --- |
| KV260 业务及显示 | startup 配置 c3861fa3… 与 380 个文件 SHA，角色为御笠雪妃，原生模型绑定 | 完整性逐项核对。启动配置与一份方向配置按原变更恢复后，SHA 与板上保存值相同。未重启在线服务。 |
| 自动跟随 | 25 项原控制器，manifest 9cd35b96…，左目标 0.40、右 0.45、容差 0.03 | 现场曾确认方向正确且能跟随，后报告自动向右偶发抖动。保留当时控制参数，开始位置取当前机械位置。当前软件夹具 42 项可离线重跑。 |
| 视觉 | 业务界面、相机独立发布树、原生算子 C++、三种已部署 xmodel | 三份工件已做 XIR 实读。YOLOX 从 Ubuntu 的归档 SD 根文件系统按 SHA 找回。现场报告的移动残影/闪动未按已修复关闭，采样无错误不能替代图像质量验收。 |
| 身份和记忆 | 身份、记忆、来源撤销与语音业务源码及公开回归 | 声纹 ECAPA 在 CPU；人脸声纹联绑已由用户取消。记忆现场反馈基本正常，私库未作为样例提供。 |
| 对话及语音 | 用户现场确认玩偶回答正常完整。三分钟模型数据另见 performance_addendum.txt | 热态五次 LLM 调用和五次 TTS 调用均成功。LLM RPC 中位 1.837 s，TTS RPC 中位 0.718 s。首个非空 JSON 内容 0.469 s 不等同声学首响。 |
| 运行能力 | 性能窗口、板资源窗口和生成图表分开存档 | 主窗口约 180 s，180 个 UI 样本均监听暂停、开麦关闭、跟随停止。YOLOX / YuNet / SFace 观察服务率 9.907 / 9.862 / 0.740 Hz。不同步的资源窗口不作逐样本强配对。 |
| FPGA | 原时序、资源、布局布线报告、新的独立建工程、XSim、导出和 Bootgen | 四套 RTL 仿真通过。用原 routed DCP 重新导出后，配套 4 个设备固件的 SHA 与发布版本一致。本轮未重跑全流程综合布线。 |

三分钟全功能同时运行、陌生机器带实板的整机冷启动仍未完成。原 R7 开机恢复候选保留在开发盘，本包默认路径未替换现役程序。报告目录中的 PDF/Word 是既有设计与赛事文档版本，最新性能指标和已补齐的工程输入以本说明、performance_addendum.txt 和 build/reports 为准。需要单独提交报告时请合并最终照片、报名信息和最新实测小节。

个人私钥、声纹/人脸登记样本、个人 SQLite、真实对话录音及下载缓存均不属于此交付。src/windows 下的 soft_young.wav 是原项目选择的合成 TTS 参考音色。
''')
put('board/readme.md',r'''
# KV260 文件、固件与现场入口

## 先在普通 Linux 生成暂存树

在工程根目录执行以下命令。输出目录须是全新的目录。脚本用 Python 标准库进行校验与复制。默认路径只生成离线树，不会连接 KV260、加载固件、启动摄像头或发送转轴命令。

~~~sh
python3 -B board/scripts/stage.py --out "$HOME/auar-rootfs-01" --audio ../auar_board_audio_dependencies.zip
~~~

若仅评审源码可省略 --audio。KV260 运行环境为 PetaLinux、aarch64、Linux 5.15.36-xilinx-v2022.2、板侧 Python 3.9、VART/XIR/Vitis AI 3.0、GTK/X11、GStreamer/OpenCV、ALSA 和 MCP01，显示屏为 1024×600。另一台 x86_64 Ubuntu 20.04 用于审查、仿真、构建和根文件系统暂存，板侧 wheel 仅用于对应的 ARM Python。stage 根据 board/config/deployment_files.json 和原部署树地址归位，保留历史上用 SHA 固定的相同文件。运行状态由实际目标设备生成。

## 运行前的检查顺序

1. **平台和固件。** 保留原卡或在匹配内核、设备树和 XRT 的独立系统上安装。固件文件位于 board/firmware/aura-visual-servo-b4096-wide-v1，身份和接口来自配对清单 board/firmware_pairing.json。用 xmutil listapps 查看实际加载项；板端切换平台前按原硬件操作流程关闭执行者、断开转轴动力并核实 STOP。工程包的离线阶段不需要上述操作。不得在正在采集或控制执行器的系统上直接覆盖已加载的固件或替换目录。
2. **相机和模型。** 运行时的独立相机服务为 aura-camera-ui.service。src/camera/runtime 保留 r4 Python 命名空间，entry_chain 和 native_operator 包含后续同版驱动源码，board/config/deployment_files.json 列出历史依赖路径。三模型采用已发布的 INT8 图，其 DPU 指纹必须与平台一致。可用本地 GET /health 核实相机所有者和 detector，再基于本机 boot_id、相机 PID / start ticks、启动命令、配置和 source SHA 建立当次绑定。原版本在 src/software/tools/private_gallery_reference.py 与 board/runtime 等模块验证绑定；板上的旧 PID 和开机证明只能用于历史核对。
3. **语音和个人数据。** 从独立附件准备 Paraformer-small、GTCRN、Silero、ECAPA 模型和 CPython 3.9 ARM wheel。config/board_avatar_gtk.json 固定了目录及参数。模型端口 8797 对应 Windows 有线 192.168.50.1，板端为 192.168.50.2。先在 Windows 验证 /health，再启动业务。个人数据库由对应设备保管。在已有演示卡复用自己的私有区和 production-bootstrap.json，首次配置应走 common/board_production_bootstrap.py 的数据初始化/封存流程并核对新回执。历史数据库哈希和权限回执不能代替新设备的初始化。
4. **界面和转轴。** board/config/startup.snapshot.json 含当前 380 项业务文件锁，launcher.py 校验入口、屏幕和组件。原界面服务为 aura-avatar-ui.service。现役设备可执行 systemctl status aura-camera-ui.service aura-avatar-ui.service 与 journalctl -u aura-avatar-ui.service -n 40 检查运行状态。暂存树不能直接覆盖正运行的根目录。在设备绑定、显示/音频、个人业务初始回执完成且手动核实当前机械位置后，使用原 GUI 的跟随按钮。原项目使用 ABIv2 的 0x10282601 wide 固件；本包没有将回中、寻零或历史运动试验加入启动步骤。

## 重新编译原生软件

在与目标一致的 AArch64 开发环境运行 sh build/scripts/native_build.sh /path/to/new-output。需要开发头文件和运行库、支持 C++20 的编译器、CMake、pkg-config、OpenCV、VART/XIR、Vitis AI Library、libpng 与 GLES。脚本保留原生运动、像素、YOLO、VART 和角色渲染的构建步骤，使用 CORE 与第三方头文件的原布局。保留已编译的 AArch64 原生 VART 对象用于链接；设置 RECOMPILE_VART=1 可从随包 C++ 文件重编译。当前打包验证运行了 host 侧的 C 协议及 Python 假时钟场景；整组 AArch64 原生重编译需要目标 SDK。新编译出的库需重新建立本次发布的 SHA 绑定。

板上固定提示音及已保存的路径参见 data/reference/public_feedback.json，原生成代码见 board/reference/generate_board_static_cues.py。历史脚本含原机门禁与绝对路径；如需重生成，应在已验证的目标模型服务上对三条公开固定文本合成、写入新的 manifest 并绑定对应哈希。
''')
put('third_party_notices.md',r'''
# 来源和许可范围

工程源码来自队伍保存在 E 盘的 AURA 业务代码、Ubuntu 上的 wide FPGA、三模型调度、原生运行库与协作记录。build/reports/ubuntu_inputs.json、data/reference/additional_ubuntu_inputs.json、runtime_hashes.json、各技能的来源记录和总 checksums.sha256 可追溯到具体交付文件。历史工程的源树使用 Xilinx 命名惯例，第三方目录名、大小写与导入路径均按原件保留。

* AMD/Xilinx 的 DPU、Vivado 生成文件、XSA/固件、Xilinx IP 和板卡支持文件按各自工具与产品许可保留；工具链和整张 SD 映像由使用者按其授权准备。src/fpga/vendor 中的文件保留原始声明。
* Windows 原生角色渲染所用上游及第三方 C++ 源许可随 src/avatar/native_integration/candidate_core/LICENSE、third_party_licenses 与来源清单保存，板端仍运行 AArch64 原生渲染器。角色模型、纹理和 EMS 资源的来源见 src/avatar/asset-provenance.json。工程中未找到可代表所有角色美术资产对公众授权再分发的文件；开放仓库前由队伍确认或替换这些资源。
* ByteTrack 的许可和固定来源位于 src/software/board/vision/bytetrack。Ruckig 的许可位于 src/motion。DroidSansFallbackFull 的声明见 licenses/font。通用 PYNQ 技能带有自己的许可文件。
* YOLOX 使用 KV260 映像中的部署工件，YuNet、SFace 与项目的公开量化、编译输入对应。ASR、VAD、ECAPA、OmniVoice 和 27B 依各上游模型及代码条款。板端外部包的前端许可文件随模型提供。各工件的固定版本和哈希以 models 的清单为依据。外部软件及权重未纳入团队统一授权。
* 设计报告、AI 协作记录、外部模型与角色资源的著作归属各自保留。工程归档未包含队伍已签发的统一公开源码许可或公开仓库地址。对外提交时，由权利人选定许可范围并填正式仓库信息。本次仅在用户两台工作机上整理和验证。
'''.replace('Windows 原生角色渲染所用','原生角色渲染所用'))
put('license','''本归档保留各原项目和依赖的著作权及许可声明。各适用许可原文与来源见 third_party_notices.md 和各子目录。归档未替各权利人授予额外的公开再分发许可。''')
put('report/requirements_map.md',r'''
# AMD 自主命题资料对应关系

对应用户提供的《2026 FPGA 赛道选题指南 AMD》3.3.5 节。

| 要求 | 本次可审阅材料 |
| --- | --- |
| 工程源码及可复现构建 | src/fpga、src/software、src/camera、src/motion、src/avatar、src/windows、build/scripts；build/readme.md 解释 2022.2 版本和增量参考输入。 |
| 仿真、正确性、报告和上板证明 | sim、data/reference、data/results、build/reports、board/firmware_pairing.json。历史实板与离线复跑的条件分列。 |
| 性能指标及对照 | report/performance_addendum.txt、report/performance_metrics.csv、report/figures、data/results/performance、data/results/xir_three_models.json，各项计时区间与样本数单列。 |
| 三个从项目提炼的技能及效果 | skill/readme.md，三个独立工具有实证、反例、复跑方式和适用边界。额外 PYNQ 工具为软件模拟范围。 |
| 技术设计与 AI 协作记录 | report/amd_design_report_v2.pdf、competition_report_review.docx/.pdf、ai_collaboration、wiring 和本次 release_status.md。 |
| 公布作品 | 当前为本地工程交付。队伍发布许可、第三方角色素材的公开再分发授权、实际提交回执及公开仓库信息需以队伍最终决定为准。 |
''')
