# AUAR·雪妃：重新整理项目的目录设计

按“先给一份结构，后续重新制作”的要求，从功能与官方条款出发设计，不沿用现有 RAR，也不搬动现役文件。

**唯一当前提交结构：[方案A修订结果](rar_source_layout.md)。** `src/`对应原`aura/`运行根，`board/host/common/ui/config/models/assets/data/hardware/tests/tools`保持原相对位置；取消先前的kv260/windows分层包布局，恢复真实主配置和四个RTL测试台。149项设计路径代表收集范围，不是真实源文件总数。100MB为未压缩收集预算，最终RAR仍需实际测量。当前按用户要求不构建，脚本尚未完整实跑，本次没有制作工程RAR。

主Skill保留现有 `pynq-contract-testgen` 的[通用PYNQ离线初版](../2026-11-02_pynq_skill/readme.md)，包含完整原始证据；真实PYNQ与跨板未验证。其他三个工程主题包按实际成熟度选交。旧版已存入archive，当前收集只使用方案A。

素材按源码复现口径收录：不做WebP转码或降帧，不装全量旧avatar帧及可再生RGB565；保留实际生成/加载源码、资源定义和最小可用样例的收集位置。原版形象需要另备的输入及其取得方式必须说明，不能用样例通过冒称原画面复现。15MB为最小资源预算，非历史素材实测体积。

[完整项目主档结构](project_structure.md)保留为开发归档参考，含逐项用途、KV260/Windows运行布局及独立上传材料；不表示507项内容都装进当前源码RAR。

实际取舍直接看[哪些交、哪些不装进工程包](submission_scope.md)：区分工程 RAR、单独上传材料、外部依赖和本机保留内容。

当前配套文件：

- [纯文本目录树](rar_source_tree.txt)：方案A完整树，便于Windows查看或复制。
- [逐项收集清单](rar_source_manifest.csv)：UTF-8 BOM编码，可用Excel打开。
- [源码提交要求映射](rar_source_requirements.csv)：条款对应当前方案A路径。
- [配置与运行根说明](runtime_config_readme.md)：供后续src/config/readme.md参考。
- [预算](rar_source_budget.csv)与[目录静态检查](rar_source_validation.json)：不表示工程实跑通过。
- [实际源文件核对](evidence/scheme_a_source_audit.json)：只读源码/配置与测试台来源SHA，无程序执行。
- [依据索引](source_index.json)：指南、上传要求、项目资料与提取范围。

清单区分真实应收文件和目标脚本入口；不表示已组成完整工程。此轮只修正文档和索引，没有新增业务配置、执行工程测试、构建、部署、模型推理或板卡操作。

Windows 对应入口：`E:\Win共享文件\协作任务\2026-11-02_project_structure\readme.md`，实际到达状态以微力同步及 Windows 本人回执为准。
