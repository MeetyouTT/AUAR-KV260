# 板端复验结果的主机聚合

全部真实证据回收至 ROOT/board_evidence，且 ROOT/board_evidence_manifest.json 和
ROOT/board_evidence.tar.gz 已落地后，执行：

```bash
python3 -B /home/ghmd/kv260-runtime-live-20261003-retry1/agent_review/analyze_live.py
```

默认 ROOT 为当前 retry1 目录，输出 ROOT/analysis。已有输出目录会拒绝，避免覆盖。
需要再次审阅时使用 `--output` 指定另一个新的目录；审阅其他 run 使用 `--root`。
程序只读原始证据，不访问板卡，不修改运行包或历史 run。

输出：

- `summary.json`：整体验证、原基线恢复、逐项输入哈希、DPU/完整 Top-5、阶段与次数、
  时长/推理数、样本统计、增量核日志、完整候选日志及未通过检查。
- `commands.json`：原始命令、退出码与 stdout/stderr 哈希验证的索引。
- `samples.csv`：按 uptime 排序的 phase、PID/starttime、watch、RSS、MemAvailable、
  Slab 和 SUnreclaim；内存单位为 kB。
- `metrics.csv`：所有候选样本及各阶段的 first/last/min/max。

`overall_pass` 只有完整阶段、控制器 complete、30 轮原始 remove/load/query/分类、
至少 1800 秒与全部声明推理/样本、无目标错误并且原基线恢复证据都符合才为真。
`baseline_restored` 单独核对恢复证据，可以在主实验失败时为真。
缺失阶段或样本表示无法确认，不当作零 watch、零增长或试验通过。

核日志统计按完整带 timestamp 的行去重，避免重复快照或审阅记录计数重复。
增量会与原始 dmesg 的末尾连续重叠复核，原驱动已知错误仅允许在其退出阶段。
长期样本按实际 uptime 计算跨度及最大间隔，不使用板端可能未校准的 UTC 时钟计算时长。
候选日志必须完整且与 SIGINT 刷新后的 sha/bytes/ERROR 列表一致。

退出码 0 表示整体证据通过；1 表示证据中存在缺失或失败，详细内容仍写入新输出目录。
有限观察不能证明所有内存泄漏不存在；此推理循环不作为 FPS 成绩。

本程序已用原第一次失败的真实数据集作反例：整体失败、基线恢复为真。
其它离线 fixture 包括输出防覆盖、人工统计值和被损坏的证据副本；均不当作新的板测。
