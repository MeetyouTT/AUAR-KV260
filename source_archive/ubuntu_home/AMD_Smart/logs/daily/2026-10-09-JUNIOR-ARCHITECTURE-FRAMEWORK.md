# 完整自主选题初级组框图与提交目录

日期：2026-10-09。主仓：`/home/ghmd/Win共享文件/共享文件夹/aura`。工作核验目录：`/home/ghmd/aura-submission-framework-20261009`。

## 任务与阅读依据

用户明确要求按整个初级组自主选题及正式提交框图，组织现在所有成果，未做内容也建出框架。此前交付的运行时软件框架只是本任务中的一个子集。本次完成全作品功能、软硬件划分、接口、验证、报告与发布结构；没有把尚未完成的功能标成实现。

先读 ZIP `项目/README.md`，读取原官方指南第 3.3 节、PDF 第 22–25 页，并核对第 28 页决赛英文海报条件；读取原无声源定位完整方案、42 工作包总负责人原件与原提交矩阵。结合 10 月 8 日完整 M1–M8 计划、10 月 7 日 Skill 规划、论文对照与最新板测/PC/软件日志更新状态。12 份原件来源及 SHA256 存于主仓 `report/architecture/provenance.json`。

官方企业仓库入口 `https://gitee.com/Vickyiii/fpgachina26-amd` 已定位；指南 blob 未成功读取，未推定后续上传字段、时间、篇幅或统一性能阈值。沿用现有 2022.2 路线，最终报告须说明原因并证明实际可复现。PYNQ 是推荐路线及可选通用 Skill 加分方向，本次没有强制迁移。双 I2S/DOA 仍为已取消范围。

## 已完成的框架交付

入口：[完整框图与状态页](/home/ghmd/Win共享文件/共享文件夹/aura/report/architecture/index.html)、[八页 PDF](/home/ghmd/Win共享文件/共享文件夹/aura/report/architecture/framework_diagrams.pdf)、[提交框架](/home/ghmd/Win共享文件/共享文件夹/aura/submission/aura_junior/README.md)。

1. `architecture.json` 统一描述 M1–M8 与后续扩展中的 64 个模块，包含部署位置、负责人、输入输出、当前状态、现有来源、待实现内容与关联内部验收。
2. 八张图：总体功能、PS/PL、视觉身份、源期限/准入/监督、媒体/ASD/UI、提交证据、G0–G5/验收、后续扩展。每图提供 DOT、Mermaid、SVG、PNG、PDF。总图保留三个闭环，分图展示细节。
3. 六种状态：已有有限板测、已有 PC 成果、软件联调通过、接口或部分实现、待实现或待实验、等待机构。所有节点同时有文字状态，图完整不表示整机已完成。
4. 42 工作包（A/B/C 各 14）、T01–T30、r01–r17 与模块建立对应；T13/T14 保留删除说明，其余内部验收均未标为最终整机通过。
5. `submission/aura_junior` 建出 `src/sim/build/board/data/skill/report` 七个推荐目录、64 个模块的 README 与接口描述，共 191 个框架文件。该目录内另含全套框图和 PDF，可直接供报告整理；源码开发位置保持原状。
6. 设计报告、九类接口、AI 可见协作/纠错、从零复现、三个比赛 Skill 说明、构建步骤和优化结果表均有模板。G0–G5 数值全部留空；三包尚待补齐独立使用、失败来源与验证，不是新安装的 Codex 技能。
7. 主仓 README 和旧 `docs/PROJECT_FRAMEWORK.md` 加入全作品框图入口。主仓 1482 个文件名/大小形成清单，107 条模块源码/证据引用存在性核验通过；外部 Ubuntu 原件未假装被内嵌。

## 实际验证

执行：

```bash
python3 -s scripts/render_submission_architecture.py --bundle
python3 -s /home/ghmd/aura-submission-framework-20261009/check_final_artifacts.py
```

生成验证：[export_validation.json](/home/ghmd/Win共享文件/共享文件夹/aura/report/architecture/export_validation.json)。独立校验：[validation_final.json](/home/ghmd/aura-submission-framework-20261009/validation_final.json)。

- 64 个模块均覆盖于图并建立独立目录，64 个模块描述与对应 ID 一致。
- 42 个标题、30 项内部验收原文、17 项正式提交映射与 ZIP 原件一致，负责人各 14 项；来源 12 项 SHA256 一致。
- SVG 节点数量匹配、PNG/PDF 格式检查通过；合并 PDF 为 8 页，各图标题均可提取；提交目录内 40 个图文件和合并 PDF 与主图册一致。
- 离线 HTML 内嵌 8 个 SVG、64 条模块行，ID 无重复，203 个本地链接存在，没有外部脚本依赖；提交入口、设计报告和图册 Markdown 链接存在。
- CSV 列数和 JSON 解析通过，6 组未执行实验的指标为空，英文提交路径检查通过。
- 已本地查看各类图的布局。Graphviz 2.43 在 `newrank` 与跨分组不可见表头链组合下发生 `returncode=-11`；移除该表头链后全部导出通过，模块/数据流未删改。没有升级系统依赖。

框架材料包：[aura-junior-architecture-20261009T081237Z-756152.zip](/home/ghmd/Win共享文件/共享文件夹/aura/artifacts/releases/aura-junior-architecture-20261009T081237Z-756152.zip)。大小 11,027,782 bytes，255 个载荷文件及 1 个清单逐项 SHA256/大小核验通过，包内载荷与最终磁盘文件一致。

SHA256：`a6b3263e7b443bc35baebcc625ac1d85a185abf8e83ed238921905b97e45788b`。

该包是框图、矩阵、说明和提交目录框架，**不是最终完整源码/固件工程包**。已有 121 文件的软件源包保留历史；本次 README 和框图新增不能用旧源包哈希代表。

## 既有实测与尚待实现

既有官方单 CU B4096、CPU YuNet/IoU 相机、SFace 静态参考、相对租约 VSRV、有限共存、HDMI，以及 Windows 汐蓝声线/动画按原证据引用。本次没有复跑板卡或 Windows 模型。此前 41 项运行时框架测试仍属 PC 软件证据，本次未重复运行。

项目真实 DPU 检测/身份、ByteTrack 实际接入、标定数据/推理成本、新 PL 绝对源期限及时间映射/ABI、MCP01 媒体链、跨机传输、Light-ASD、授权操作 UI、最终同板系统、G0–G5、完整 Skill、非作者复现及最终报告/视频/条件海报均待完成，但都已在图与目录中有位置。

机构与舵机标定继续等待 3D 模型。没有访问板卡、加载固件、启动真实模型、舵机动作、GUI 服务或发布操作。下一阶段从对应模块与验收位置填入真实实现、输入、构建和结果；框架目录里的描述不能替代正式工程包源码。
