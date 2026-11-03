# 验证范围与证据

| 检查 | 实际结果 | 限制 |
|---|---|---|
| 既有行为与新恢复组合 | 198项通过，`software-regressions-newboot.log` | Docker内假VART，不算真实推理 |
| KV260基础隔离 | 171项通过，`board-isolated-r1-result.json` | 不导入真实VART，无DPU作业 |
| KV260新增恢复注入 | 26项通过，`board-final-isolated-result.json` | 真实runner/适配器/调度器代码，native为fake；不等于真人恢复 |
| 独立注入 | 16项包含于组合与板26项，不额外相加 | 初版1项fixture未转Python float失败已保留；修订后通过 |
| 发布纯函数 | 5项通过，`deployment-tests-newboot.log` | 只验证命令覆盖/命名空间等；不代替实板流程 |
| 阶段解析及opcode | 4项通过，`phase-parser-tests.log` | 精确ELF仅本机，不进入共享包 |
| 保守准入候选 | 6项通过，`admission-floor-tests.log` | 仅本地候选，未部署，无吞吐收益结论 |
| 当前boot恢复功能启用 | 60.306秒流程通过，`promotion-result.json` | 0个新增SFace请求；实际恢复尚未验证，未注入生产故障 |
| 第一阶段观测 | 180.033秒/702完整cycle、无fault/gap/主周期新增，`phase-result.json` | 全部为一个YuNet调用线程；SFace新增0，非三模型持续负载 |

第一阶段native p50/p95/p99/max为2.180/4.312/8.032/14.776ms，RestoreThread对应0.011/0.376/2.200/5.134ms。文本时间量化1µs。controller CPU0.2878%单核，成本包括自身setup/health读取/聚合/清理，不包括子systemctl和末尾序列化；目标断点开销另有上一轮fixture实测。没有从30ms/guard计时扣除观察成本。没有捕获故障不能证明旧故障来自任何一段或已被消除。

所有probe的清理须由报告与最终只读audit共同确认；运行中轮次不能提前写cleanup通过。第二个有界窗口结果以`phase-600-result.json`为准，若文件不存在表示尚未完成/收回。

当前保护快照仅来自同boot的已核验源/进程与实际状态。为接续加载保存了非原子的idle health快照，含停止GUI后、停止相机前的计数；不是原进程退出时刻的原子最终账本。相机重启导致其他业务计数新开窗口，不能把继承的schedule计数、freshness计数、detected_frames等当成同一个区间。

旧boot的故障、外部新boot以及本轮受控相机切换分别记录。原unit SHA297…保持、GUI运行源不变；本轮的`/run`覆盖只在当前开机生效，下次冷启动恢复原入口。没有执行冷启动或改PL/运动服务，没有代填Windows接收/真人准确率/整机长稳。
