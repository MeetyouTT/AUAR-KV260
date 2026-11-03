# AURA 初级组构建、运行与验证脚本实施清单

日期：2026-10-10。本文件是基于现有代码和证据的实施方案，**不是已通过的整机复现报告**。

核查范围：原官方指南、ZIP README、完整无声源定位方案及总负责人执行手册、当前 M1–M8/64 模块/42 工作包、主仓入口、外部硬件脚本，以及截至 2026-10-09 的板测日志。2026-10-09 用户更新为 A 负责视觉与 FPGA；下文保留 A01–C14 工作包编号用于追溯，不重新分配人员。

## 1. 官方要求与版本选择

原件为 `/home/ghmd/下载/项目.zip` 内 `项目/参赛资料/全国大学生嵌入式芯片与系统设计竞赛'2026FPGA赛道选题指南-AMD.pdf`。

- §3.3.3.1，PDF 第 23 页、印刷第 20 页：推荐 Vivado/Vitis 2026.1 或 2025.2，其他版本需要在报告中说明并保证脚本可复现。原文没有要求“2025 年以前的软件另交一种版本识别脚本”。
- §3.3.5.1，PDF 第 24 页、印刷第 21 页：所有作品均要交完整工程源码、验证结果、综合实现报告、上板工程/运行脚本/实测与参考比对、可复现构建脚本。
- §3.3.4/§3.3.5.3：他人能够从零复现，并有完整操作步骤。脚本存在与脚本在干净环境执行成功应分别记录。
- 官方推荐 `src/sim/build/board/data/skill/report` 七目录；采用其他结构时在 README 中给对照。最终交付路径使用英文。

本地已有官方 PDF 副本：[`official_guide.pdf`](/home/ghmd/aura-submission-framework-20261009/official_guide.pdf)，本轮逐字节核对与 ZIP 原件一致。企业仓库正文本轮在线抓取超时，未据此确认后续规则变化。

建议沿用当前 2022.2 组合，在设计报告说明：既有 KV260 PetaLinux/DPU 工程与 Vitis AI 3.0 按此工具链建立，固定兼容组合有利于重建与对照。AMD 的 [Vitis AI 3.0 兼容表](https://xilinx.github.io/Vitis-AI/3.0/html/docs/reference/version_compatibility.html) 列出 Vivado/Vitis/PetaLinux 2022.2、DPUCZDX8G 4.1、Vitis AI 3.0。这只支持组合选择，实际工程的 IP、指纹、模型和固件仍需分别核验。

本轮实际版本查询：Vivado 2022.2 / SW Build 3671981；v++ 2022.2 / SW Build 3671529。没有重新验证 PetaLinux 安装、许可证或 IP 组件。

## 2. 当前可以复用什么

| 工作主线 | 已有入口或证据 | 正式脚本仍需补齐 |
| --- | --- | --- |
| M1 平台与设备 | 官方卡、DFX、驱动/显示历史板测；参考平台构建入口 | 固定芯片/板卡、系统输入、补丁、SDK、设备身份和版本；新环境准备 |
| M2 人体感知与跟踪 | CPU YuNet/IoU 相机参考；ByteTrack 适配；DPU 插件接口 | 项目人体 xmodel、真实 DPU 调用、前后处理和 ByteTrack 板测 |
| M3 人脸身份与记忆 | SFace 静态参考权重、SQLite 与身份软件接口 | 实际登记/重返/陌生/删除数据、阈值与完整板端验收 |
| M4 时效与共享调度 | 模拟框架、软件准入/到期/调度测试 | 实测任务成本与标定、时间映射、与最终 PL 合同接入 |
| M5 运动与 FPGA 监督 | 联合源平台实现、旧相对租约 VSRV、有限板测与上电后视觉命令证据 | 最终绝对源期限监督、ABI/外部约束、机构标定、无旧缓存复建 |
| M6 语音与看图问答 | Windows 历史声线/模型成果；MCP01 缓存播放 | 真实板端录音→主机 ASR/VLM/TTS→板端回复链及取消/断连 |
| M7 说话人建议与 UI | GTK 缓存界面、触控、设置与服务快速重启已实测 | Light-ASD、同步窗口、动态结果接入、整板开机与长期并行 |
| M8 评测与发布 | 软件打包器、框图、矩阵、七目录与 Skill 模板 | 最终完整工程包、指标比对、干净环境和非作者复现 |

关键现有文件：

- 软件统一入口：[`tools/aura_project.py`](../tools/aura_project.py)、[`tools/run_project.sh`](../tools/run_project.sh)。当前默认是模拟联调。
- 软件源包：[`scripts/package_project.py`](../scripts/package_project.py)。默认排除大型模型、固件及相邻交付目录，不能直接作为整机包。
- 缓存 UI 包：[`tools/package_board_avatar.py`](../tools/package_board_avatar.py)；实际启动见 [`BOARD_UI_STARTUP.md`](BOARD_UI_STARTUP.md)。该服务仅管理玩偶子系统。
- 参考平台：`/home/ghmd/kv260-reference-2022.2-20260930/run_reference_build.sh`。
- DPU 4.1：`/home/ghmd/kv260-dpu41-control-20261001/run_dpu41_build.sh`。
- 联合源平台：`/home/ghmd/kv260-visual-servo-20261007/scripts/implement_source_platform.py` 及相邻 Tcl。

最后三项使用本机绝对路径；联合源平台 Python 还复制旧工程 `ip_cache` 并将已有 `joint_routed.dcp` 作为增量布局参考。该 DCP 并未替代新综合，但现在的入口依赖其存在；必须补一条无需这些旧生成工件的全量构建路径，再实际测试。不能仅复制脚本便声称从零复现。

## 3. 建议的脚本结构

一个总入口按阶段调用子脚本。Ubuntu 负责构建，KV260 负责设备运行，Windows 负责模型服务；分别提供各自入口，由清单关联同一 release。下表名称是**待实现接口建议**，不表示已经存在。

| 建议入口 | 作用 | 验收输出 |
| --- | --- | --- |
| `build/reproduce.sh check` | 工具/依赖/IP/输入哈希检查 | `environment.json`，不匹配时返回非零 |
| `build/reproduce.sh hardware` | 从源码创建平台，仿真、综合、实现、封装 | 同工程 bit/xsa/hwh、所需 xclbin/dtbo/bin 和资源/时序/DRC/约束报告 |
| `build/reproduce.sh system` | 使用冻结配置和补丁构建或按声明路线准备系统 | 可重建系统输入、匹配 rootfs/内核/SDK；基础镜像来源与 SHA |
| `build/reproduce.sh models` | 按固定权重/校准集/arch 量化和编译 | xmodel、模型卡、前后处理配置、浮点/量化/板端输出比对 |
| `build/reproduce.sh application` | 固定 Python/本机库依赖、素材，导出板端与主机程序 | 独立目录可导入的应用包及依赖/资源清单 |
| `build/reproduce.sh all` | 依次执行完整构建与导出 | `release_manifest.json`、构建日志和完整包；缺一步不得总 PASS |
| `board/run.sh check` | 读取当前实际板卡/固件/设备及服务能力 | boot ID、设备身份、DPU 指纹、IP_ID/ABI/BUILD 和模型匹配结果 |
| `board/run.sh start / stop / collect` | 编排唯一相机、运动服务、交互与 UI，采集日志 | 实际健康状态、可追溯输出、正常停止记录 |
| `host/start.ps1` | 启动冻结的 Windows 模型环境并执行功能探针 | 固定音频/图像的真实 ASR/VLM/TTS/ASD 结果 |
| `board/verify.py` | 固定输入与参考比较，保存性能与异常结果 | 每项 PASS/FAIL/未验证、实测数据、测试版本 |

部署与加载由单独明确的步骤执行。构建成功后不能未经板端身份核对直接加载固件；启动自检也不自动 ARM。机构/供电/实际转动和真实听音仍有人工验收项。

硬件入口可从当前工程导出 Tcl 开始，例如使用 `write_project_tcl` / `write_bd_tcl`；导出后需检查源路径、外部 IP、约束、BD、运行配置并补齐 Vitis/PetaLinux 阶段。AMD 的 [`write_project_tcl` 文档](https://docs.amd.com/r/2022.2-English/ug835-vivado-tcl-commands/write_project_tcl) 说明其重建项目的范围及相对路径注意事项；单独导出 Tcl 不等于完整平台已可复现。

路径统一从脚本位置推导工程根目录；工具安装位置由环境变量或参数传入。构建输出放独立新目录；旧日志、旧生成工程与既有结果保留。干净构建不允许静默回退到作者的 cache/DCP 或预编译模型。

## 4. 怎样识别环境、硬件和正确结果

“版本对上”“板卡在线”“功能正确”是三种检查，各自提供证据。

| 检查对象 | 读取/比较方法 | 通过条件 |
| --- | --- | --- |
| Vivado/Vitis | `vivado -version`、`v++ --version`；记录完整输出和实际可执行文件路径 | 与本次 release 工具锁一致，不按“年份小于 2025”粗判 |
| 源码及依赖 | Git commit/子模块 commit、输入文件 SHA；无 Git 的源码快照保存逐文件 SHA | 全部固定输入可取得且未变化；容器固定 digest，不用 `latest` |
| 目标平台 | 构建端读取实际 `PART`；板端读取设备树 model/compatible、系统/内核版本 | 与冻结平台合同一致；不能用目录名认定板卡 |
| 已加载硬件 | FPGA 状态＋DPU query 指纹＋自研 IP_ID/ABI/BUILD；与匹配工件清单关联 | 同一次启动中实际 DPU 与自研 IP 均匹配；只在磁盘发现 bit 不算已加载 |
| 模型 | 权重/xmodel SHA、编译 arch、DPU 指纹、输入尺寸和前后处理 | 模型与真实 DPU 兼容；发现 `.xmodel` 扩展名不能证明正确 |
| 外设 | 稳定相机身份/实际格式、MCP01 声卡身份、屏幕/触摸标识 | 使用冻结目标；不能只写死 `/dev/video0`、声卡数字或 event 编号 |
| Windows 服务 | 协议/模型版本＋固定真实输入的功能探针 | 返回实际模型结果；端口能连通不代表模型可用 |
| 功能正确 | 固定测试输入与参考输出、逐项容差/阈值和异常行为比较 | 先冻结验收规则；每项结果附数据、版本和运行位置 |

重建产物不一定与历史 bit 逐字节相同。输入必须固定，新的产物计算自己的 SHA；复现结论结合功能、时序/资源与板测检查。发布包传输和部署时则对该次产物做精确 SHA 核验。

识别结果的建议记录字段：`release_id`、`run_id`、`boot_id`、工具版本、源码/固件/模型 SHA、输入数据 SHA、预处理配置、逐项结果、证据路径与未验证原因。官方指南没有在所核查章节给出 AURA 的统一人脸阈值或性能门槛，项目需要用独立数据制定并公开。

## 5. 42 工作包与脚本阶段的完整映射

此表覆盖全部原编号；阶段归类不表示对应工作已经实现或能完全自动化。

| 主阶段 | 原工作包 | 需提交的具体内容 |
| --- | --- | --- |
| 平台锁与人工输入 | A01、A04、A11、A12、C01 | 版本、ABI、系统/SDK、接线/机构与设备事实；人工项记录已验/未验 |
| 硬件构建与报告 | A03、A05、A06、A07、A08、A09、A13 | RTL/平台/约束、仿真、完整构建、资源时序、联合与故障证据 |
| 模型准备与功能探针 | A02、B01、B03、B04、B07、B11、C05、C09 | DPU 对照、检测/身份量化编译及预后处理、调度配置、主机模型与 ASD |
| 应用与资源导出 | A10、B02、B05、B06、B08、B09、B10、B12、C02、C03、C04、C06、C07、C08、C10、C11 | 驱动库、相机/跟踪/身份/对象、USB 音频、协议/取消、问答、UI、声画同步/建议 |
| 日常运行 | C12 | 自检、启动/停止、日志、断连恢复；单实例与启动顺序 |
| 统一验证 | B13、C13 | 独立数据、参考比对、异常/延迟/并发、原始数据与分析入口 |
| 发布与复现 | A14、B14、C14 | 工程包/模型包/交互包、版本与许可、Skill、操作手册、非作者复现 |

## 6. 本轮已提供并实际验证的起点

新增 [`scripts/check_build_environment.sh`](../scripts/check_build_environment.sh)。它读取实际版本并检查当前 AURA 2022.2 基线；**只完成工具主版本自检，不是官方要求的完整可复现构建脚本**。

在当前主机运行：

```bash
AURA_VITIS_SETTINGS=/home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh \
  bash scripts/check_build_environment.sh
```

其他使用者将环境变量替换成自己的已安装设置脚本；也可先自行加载工具环境，再运行该脚本。该变量选择的是会执行的本地厂商设置文件，应指向自己的已验证安装。

现有软件配置自检：

```bash
python3 -B -s tools/aura_project.py --config config/runtime.sim.json doctor
python3 -B -s tools/aura_project.py --config config/runtime.kv260.json doctor
```

本轮在 Ubuntu 主机实际运行：模拟配置返回 0，两份 CPU 参考权重 SHA 相符；KV260 配置返回 2，报告主机缺 NumPy/ByteTrack、缺项目人体模型、DPU entrypoint 与 arch_fingerprint 未配置。后者是**当前主机配置/文件检查**，不是板端缺库结论，也不是本轮板测。现有 doctor 的能力说明属于统一框架范围；MCP01 缓存播放器的更新实测以最新专门日志为准。

版本检测脚本另执行 shell 语法、帮助入口、实际工具链、工具缺失和版本不符检查；详细结果见当天项目日志。

没有运行完整硬件构建、连接板卡、加载固件、启动真实模型、录放音或控制运动；没有重复已有测试套件。

## 7. 建议执行顺序

1. **现在先做平台输入回收。** 固定当前可用联合源工程、上游源码/IP/补丁、工具与系统版本，并给报告补 2022.2 选择理由。将绝对路径改成参数，补不使用旧 cache/DCP 的全量模式；机构不阻塞这一项。
2. **建立一条实际完整硬件复建链。** 在全新输出目录从输入创建项目、综合实现并导出配套固件与报告。旧稳定设计和新绝对期限设计分别标注，最终源码改变后重新做对应验收。
3. **视觉与交互模块各交一个真实功能探针。** 冻结项目模型、数据、依赖与实际命令；明确 CPU/DPU/Windows 运行位置。完成的模块立即纳入总入口，未完成项明确返回未就绪。
4. **冻结统一 release，再补整机运行和参考比对。** 启动顺序按依赖能力就绪推进；先保持运动禁能，按既定验收流程验证真实设备。
5. **在新路径/干净环境，由非作者按 README 执行。** 不读取作者相邻工作目录、旧生成项目或未登记缓存；先完成构建复现，再验证板端部署/输出。把失败修正和可复用经验纳入 Skill。

若“识别”指人体/人脸：脚本只能编排已有算法。当前应先补项目 DPU 检测模型与实际调用、跟踪，再闭合授权登记→特征库→重返匹配→陌生/模糊 UNKNOWN→删除失效的板端链。当前 KV260 配置的身份后端为 disabled，不能靠把启动脚本设为可执行就自动认人。若指语音识别，则需先打通 MCP01 真实录音和 Windows ASR 功能探针，再接整个问答链。

## 依据索引

- [当前完整范围与入口](/home/ghmd/AMD_Smart/PROJECT_BOOK_INDEX.md)
- [原 42 工作包](../report/architecture/work_packages.csv)、[64 模块](../report/architecture/module_matrix.csv)、[正式要求映射](../report/architecture/requirements_matrix.csv)
- [2026-10-09 结构核查](/home/ghmd/AMD_Smart/logs/daily/2026-10-09-PROJECT-STRUCTURE-REVIEW.md)
- [联合源平台真实实现记录](/home/ghmd/kv260-visual-servo-20261007/SOURCE_PLATFORM_REPORT.md)
- [上电后视觉命令与固定往返记录](/home/ghmd/AMD_Smart/logs/daily/2026-10-08-SERVO-VISIBLE-TEST.md)
- [最新 UI 启动实测](/home/ghmd/AMD_Smart/logs/daily/2026-10-09-BOARD-UI-AUTOSTART.md)
