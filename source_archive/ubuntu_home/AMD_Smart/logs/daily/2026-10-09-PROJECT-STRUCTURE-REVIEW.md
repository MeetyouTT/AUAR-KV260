# 项目结构细化与依据复核

日期：2026-10-09。主仓：`/home/ghmd/Win共享文件/共享文件夹/aura`。本轮核验目录：`/home/ghmd/aura-structure-review-20261009`。

## 任务结论与依据

用户要求更具体、更清楚且有依据的项目结构。复核结论：官方推荐七类交付目录与当前 M1–M8 功能主线可以保留；共享合同、跨端代码归属、接口编号、构建输入与输出、资源定位和迁移规则需要细化。已完成目录职责、源码映射与依据登记；没有迁移业务源码或完成待实现算法。

按规则先读 ZIP 内 `项目/README.md`，核对原官方指南 PDF §3.3.5.1–3.3.5.4、完整方案、2026-10-02 三人总包 §2.1–2.3/§4/§6.1、2026-10-08 框架、最新日志和实际代码。官方入口 `https://gitee.com/Vickyiii/fpgachina26-amd` 可读；分赛道 GUIDE 正文未能在线抓取，具体条款依据用户 ZIP 中官方 PDF，未宣称核实后续上传字段或时间。

七目录是官方推荐，允许其他目录加 README 对照；PS/host/shared 等细分、64 模块、三项 Skill、30 项测试和 G0–G5 是项目设计或内部验收选择，不能当成官方规定数量或门槛。

## 实际改动

入口：[目录细分与依据](/home/ghmd/Win共享文件/共享文件夹/aura/report/architecture/structure_detail.html)、[完整说明](/home/ghmd/Win共享文件/共享文件夹/aura/report/architecture/structure_detail.md)、[提交目录](/home/ghmd/Win共享文件/共享文件夹/aura/submission/aura_junior/README.md)。

- 新增 `report/architecture/structure_spec.json` 与 `scripts/render_structure_review.py`，登记 59 项目录职责、22 项依据、10 项问题、10 类资源/状态所有者和原 I01–I07。各目录写明内容、边界、运行位置、主责与来源。
- 新增共享合同和公共工具职责层；确认 `host/model_service/client.py` 由板端运行时创建，`protocol.py` 被两端共用，`board/runtime/audio/selected_voice.py` 属于 Windows 模型实现。旧音频目录仍需按模型合成、板端设备与历史参考拆分。
- 修正三个模块目标位置：官方 DPU 集成从 `src/rtl/dpu_platform` 改为 `src/platform/dpu_integration`；运行时使用的 SimulationGuard 从 `sim/software_guard` 改为 `src/ps/motion/simulation_guard`；双端媒体合同从 `src/host/media_transport` 改为 `src/shared/contracts/interaction`。主机传输服务仍有独立职责目录。
- 恢复原总包 I01–I07 的含义、文件约定与维护责任；上一版九条数据流改用 D01–D09，不与原合同编号冲突。最终 ABI、位宽、时钟与跨机协议未冻结。
- 分开平台输入、构建脚本、实现报告和部署固件；旧硬件构建使用绝对路径、IP cache、既有 routed DCP，不标为从零复现完成。
- 分开 UI 源码、模型/素材、标定集、独立测试集、参考输出与原始板测；身份库、缓存和运行日志按部署状态目录管理，最终可写路径待镜像冻结。
- 明确当前 Python 命名空间及 `common/config.py`、`avatar_assets.py` 的相对资源路径。目标目录表示职责，不等于可直接导入的 Python 包；后续迁移须验证包入口、资源定位和隔离运行。
- 更新主仓 README、`docs/PROJECT_FRAMEWORK.md`、图册导航、提交目录 README、接口模板和生成器。旧许可矩阵仍为历史资料，未改写为当前依赖/部署结论。

三个旧模块目录仅有此前生成的 README/interface 描述；逐项核对旧框架包字节一致后移入工作目录 `previous_slots/`。旧 architecture.json、接口模板与生成/打包记录保存在 `previous/`。业务源码、硬件输入、模型、原始日志未搬迁，旧发布 ZIP 保留。

## 实际验证

执行：

```bash
python3 -s scripts/render_submission_architecture.py --bundle
python3 -s /home/ghmd/aura-structure-review-20261009/check_final_artifacts.py
```

生成检查：[structure_review_validation.json](/home/ghmd/Win共享文件/共享文件夹/aura/report/architecture/structure_review_validation.json)。独立回读：[validation_final.json](/home/ghmd/aura-structure-review-20261009/validation_final.json)。

- 59 项目录职责、64 个模块位置、原 I01–I07 编号及文件名通过核验；三个旧位置的模块描述已撤下，新位置 ID 一致。
- 171 个 Python 文件完成 AST 解析、角色分类和 SHA256 回读；420 条本地静态导入记录指向存在文件和实际 import 行。分类含历史/开发/候选工具，不表示全部用于正式交付，也不是完整动态调用图。
- 22 项依据、40 条文件哈希引用及 14 处实际代码行匹配。40 是引用条数，含同一原件的多次引用，不是 40 份不同原件。
- 原 42 工作包、30 项内部验收、17 项提交映射与 ZIP 原文一致；12 项原来源 SHA256 一致，107 条来源引用存在。
- 图册仍为 8 张/8 页，提交目录内 40 个图文件和合并 PDF 与主图册一致。主图册 204 个本地文件链接有效；两份结构页面各核对 183 个本地文件/锚点链接、59 个目录卡片与唯一 ID。JSON/CSV 检查通过，六组未执行实验的指标仍为空。
- Chrome 无头渲染检查中文与首屏布局，截图为工作目录 `structure_preview.png`。随后在 Ubuntu Chrome 打开结构页；X11 窗口 `0x380001f` 标题为 `AURA 项目结构细分与依据 - Google Chrome`。窗口存在，不宣称已自动切为当前前台。

新版框架材料包：[aura-junior-architecture-20261009T085636Z-fc752b.zip](/home/ghmd/Win共享文件/共享文件夹/aura/artifacts/releases/aura-junior-architecture-20261009T085636Z-fc752b.zip)。大小 **11,215,810 bytes**；**309 个载荷文件 + 1 个清单**逐项大小、SHA256 和当前磁盘字节一致性通过。

SHA256：`6aae7a3f9a9a6ecf1e4408c74a766939dc7b41ccd7eff6875adef40c927bfdef`。

该包只含框图、矩阵、依据说明、生成器与提交框架；业务源码和外部 Ubuntu 工程未全部内嵌，不能当成最终独立运行的源码/固件工程包。旧包和旧核验记录保留为历史版本。

## 未验证与下一步

本轮没有重跑此前 41 项运行时测试，没有连接板卡、启动真实模型、加载固件或驱动舵机；结构/静态检查不是功能验收。现有 BOARD/PC/SW 状态仍限定在原证据范围，不扩展为新适配或整机通过。

下一步按登记合同逐模块接真实实现。源码导出须明确生产/参考入口、依赖锁、来源/许可与哈希，并在隔离目录验证导入、资源和模拟链，再做目标平台验收。真实项目 DPU/跟踪、媒体/ASD、PL 新期限、板端 UI、G0–G5、完整 Skill 和从零复现仍待完成。机构及相关标定继续等待 3D 模型。
