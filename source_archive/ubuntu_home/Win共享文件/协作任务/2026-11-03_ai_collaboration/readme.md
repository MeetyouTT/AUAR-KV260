# AUAR·雪妃｜AI 辅助设计与大模型协作记录

已整理为 **15 页 PDF 主稿＋23 页 PDF 原文节录**，附可编辑 Word/Markdown，覆盖十个工程案例，含 22 个交互片段、67 条原始消息及 74 项工程/规则来源索引。

- [Word 可编辑主稿](ai_collaboration_record.docx)
- [PDF 主稿](ai_collaboration_record.pdf)
- [Markdown 主稿](ai_collaboration_record.md)
- [PDF 原文节录](conversation_records.pdf)
- [Markdown 原文节录](conversation_records.md)
- [完整入选问答 JSONL](conversations_full.jsonl)
- [问答定位与 SHA](conversation_index.csv)
- [十案例与证据映射](case_matrix.csv)
- [来源索引 JSON](source_index.json)／[CSV](source_index.csv)
- [复用工作流模板](workflow_templates.md)
- [本次核验结果](checks/validation.json)

共享目录另提供 `ai_collaboration_bundle.zip`，解压内容中不再嵌套该压缩包。

正文以工程任务、AI 辅助形成的文件、实际验证、失败纠错及人工决策为主，保留对 DPU 长尾、跟随降频、同模型 CPU 后端和真实运行根的明确纠错。

本次遍历本机 Codex 线程元数据及可见用户/最终回复，重点核对入选问答和对应工程证据。Windows 内部语音、GPU 和记忆开发的完整对话未全部同步；相关成果使用工程文件与结果支撑，并明确记录缺口。所选历史问答不是全部聊天导出，模型元数据也不代替逐轮精确版本。

证据快照分为原文件指纹与脱敏/节录副本指纹；`H01—H38` 是旧五案例索引中逐项复核的实际源码、工件或结果，本包提供路径/指纹，完整原件按工程提交范围取用。本包不含认证配置、内部推理、私人数据库、音频、人脸或完整本机历史数据库。

较新的 9a4f 源码构建结果已纳入，历史 DCP、历史板测和新候选的状态分别说明。没有新增工程、模型或设备实验。本次验证为原文/文件指纹核对、历史关键指标复算、DOCX XML/关系检查、PDF 文字和版面检查；Word 未在 Microsoft Office 中实开，Windows 同步收件未代验。

提交前需队伍补签姓名与实际个人分工，并确认最终同版业务验收和未回收的 Windows 原始对话。本文是已整理的参赛附件主稿，不自行认定官方验收或得分。

## 本包自检

在解压后的目录运行：

```bash
python3 checks/verify_package.py
```

该命令只核对资料包文件、已导出消息及证据快照 SHA，不连接设备、不调用模型、不读取原机历史数据库。原数据库定位与逐字核对结果在 `checks/validation.json`。

整理日期：北京时间 2026-11-04，Ubuntu 本机日期 2026-11-03。原始 UTC 与阅读用北京时间同时保留。
