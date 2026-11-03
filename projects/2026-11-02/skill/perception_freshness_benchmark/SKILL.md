---
name: perception-freshness-benchmark
description: 对 KV260 单 B4096 多模型调度的离线计数器和逐请求日志进行时效核验，或比较已编译视觉模型的 XIR 元数据与冻结接口。
---

累计日志使用 `scripts/analyze_counters.py`。对业务率使用同一相机健康接口的结束单调时钟差，对阶段均值使用阶段累计总时长增量除以阶段计数增量。
若需要 P95/P99 排队或消费年龄，请提供同一开机、同一时钟域并带源端和消费端时刻的逐请求日志，执行 `scripts/analyze_schedule.py`。无该日志则标为未测。拒绝的任务仍占总到达分母。
离线比较 YOLOX、YuNet、SFace 的目标指纹、输入量化接口或工件身份，运行 `scripts/validate_metadata.py`。声纹 ECAPA 留在 ARM CPU。三份部署 XMODEL 的哈希与 XIR 元数据以及原始实测分别见 [README](readme.md)。保存原始证据与版本边界。