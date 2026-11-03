AUAR 雪妃 AMD设计报告 V2

主报告：auar_xuefei_amd_design_report_v2.pdf
可编辑正文：amd_design_report_v2.html（与figures目录保持相对位置）
七项映射：requirements/coverage.json
来源索引：source_index.json；数值来源：data/metrics.json

附件
attachments/evidence：阶段原始报告、JSON、少量源码和新保存状态摘录。
attachments/ai_collaboration：历史工程复盘、可见问答及文档生成纠错实录。
attachments/validation：本次Windows离线原始日志和输出。
attachments/wiring：资料核对版接线PDF、PNG、SVG和逐线表。
skill/pynq-contract-testgen：既有离线Skill原字节副本、两个示例和说明。
reproduction：从新目录核对证据与复跑Skill的入口。

从零执行包内离线部分
准备Python 3.8或更高版本。在本目录运行：
python -B reproduction/reproduce_offline.py --out ../auar_verify_01
输出目录必须是新目录。预期summary.json为PASS；15项单元、加法36例和CRC37例通过。
board_verified和full_system_reproduced保持false。

交付范围
这是AMD七项设计报告及附件，不是全部工程源码RAR或已完成实机复现的发布包。
完整重建仍需参考DCP/IP仓库和最终配套release；操作步骤、输入与待验事项见第7章。
准确历史AI模型版本、核心开发逐轮问答和个人分工按真实留存继续归档。
人脸与声纹独立工作；已取消的跨模态关联不作为新增任务。
图纸保留实物待核标签，阶段性能不代替新版联合性能。
