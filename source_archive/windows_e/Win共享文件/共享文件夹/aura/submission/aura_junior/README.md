<!-- aura-architecture-generated -->
# AURA·汐蓝自主选题初级组提交框架

此目录按官方推荐的 `src/sim/build/board/data/skill/report` 建立，覆盖 M1–M8、全部 42 工作包和 T01–T30，含当前未做模块。状态是 **FRAMEWORK_NOT_FINAL_COMPETITION_RELEASE**。

先看 [目录细分与依据](report/structure_detail.html) 和 [完整结构说明](report/structure_detail.md)，包含目录职责、共享资源所有者、原 I01–I07、现有源码及静态依赖。

本目录内的完整框图：[报告与框图](report/README.md) · [八页 PDF](report/framework_diagrams.pdf)。主开发仓的交互入口：[图册与状态页](../../report/architecture/index.html)。目录和源码映射见本目录 `manifest.json`、`report/module_matrix.csv` 与 `report/source_references.json`。

开发目录与目标交付职责对照（不按旧文件夹名称机械搬迁）：

| 目标位置 | 现有开发来源 / 边界 |
|---|---|
| src/shared | common；host/model_service/protocol.py 等双端合同 |
| src/rtl | hardware/rtl 中旧 VSRV 参考；新运动监督待实现 |
| src/platform | 原 FPGA 工程的官方 DPU 集成、BD/XDC、系统配置输入 |
| src/ps | board 中板端业务；host/model_service/client.py 实际也是板端客户端 |
| src/host | host 中模型流水线；board/runtime/audio/selected_voice.py 等主机模型代码 |
| src/ui | board/interaction 与选定 PC 基线；ui JSON/素材归 data/assets |
| src/config / src/third_party | config 与固定依赖/来源/许可；最终版本待逐项核对 |
| sim | tests 与原 RTL testbench；软件监督实现本身在 src/ps/motion |
| build | 构建与打包脚本、工具锁和实现报告；原绝对路径脚本仍需参数化 |
| board | 匹配部署工件、运行脚本和板测证据；不是主仓 board 源码的直接副本 |
| data | 标定/独立测试/黄金参考、模型、素材、分析；原始板测按 run_id 引用 |
| skill | 三个当前预留技能目录及已有验证代码 |
| report | 框图、接口登记、矩阵、报告、协作和复现记录 |

本次没有搬走或覆盖既有工程；源码引用分为主仓相对位置和 Ubuntu 外部来源。最终发布时回收经核验源码与许可允许的资源，固定版本和哈希；不依赖开发者个人绝对路径。

现有 Python 导入与配置/素材路径依赖原包结构；src/ps 等是目标职责位置。真正重排源文件前必须解决包入口与资源定位，并执行隔离复现，不能把目录框架称为可运行的最终源码副本。

三包是比赛 Skill 的说明/接口位置，完整脚本、真实失败、验证效果和非作者复用尚待补齐；未创建 Codex 自动执行技能。PYNQ 适配为可选，不改变既定 Linux/DPU 路线。机构标定等待 3D 模型。
