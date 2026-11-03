# AURA 大模型协作记录

按2026年AMD选题指南自主选题赛道3.3节整理，日期2026-11-03。

- report/amd_llm_collaboration_record.docx：可编辑正文。
- report/amd_llm_collaboration_record.md：同内容文本稿。
- evidence/conversation_excerpts.md：三组可见历史消息的可读附件。
- evidence/conversation_messages.json：原消息ID、会话、时间、角色与可见文本。
- evidence/source_index.json：25项本地来源的路径、SHA256及快照对应关系。
- evidence/sources/：24项小型文本来源原字节快照。
- evidence/chin_before_after.png：已有工程中的修复对照原图。

本次先清点E:\项目约137311个文件条目，再重点阅读赛题、方案、协作记录、源码及相关运行证据。清点包含临时目录、环境与历史副本，并不表示逐个通读全部二进制或缓存。未读取或复制LLM权重；未改动原文档、业务源码、设备和模型服务。

第2至4节为真实消息摘录，第5至7节为工程复盘。历史模型版本未由聊天读取结果提供；运行端27B不代替开发助手型号。精确人员署名和开发模型版本请按实际账户记录填写。Ubuntu历史构建文件只保留索引来源身份，本轮未重新构建或复测。

本包中生成的md提示词模板明确标注为新模板。PYNQ真实硬件、跨板与非作者复用未验证，不能将离线验证改写为这些结果。单元测试15项和模拟用例73项分别统计。

本包只提交记录及小型证据，不包含模型权重、虚拟环境或数据库。对外提交时保留report与evidence的相对目录，核对最终队伍信息与工程版本。
