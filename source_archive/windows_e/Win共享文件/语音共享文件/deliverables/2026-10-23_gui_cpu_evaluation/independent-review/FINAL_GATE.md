# GUI CPU候选最终独立验收结论

**结论：CPU收益未达预声明10%门槛，拒绝部署，停止GUI试运行准备。** 画质/metadata通过不能替代CPU门槛；不把门槛降到5%，不以wall时间替代CPU时间，不把headless结果当整机提升。

本子任务已直接读取`exact-v2-result.json`，按两轮总CPU重新计算：

| 变体 | ABBA轮次 | 实测帧数 | 总process CPU | 每帧平均process CPU |
|---|---|---:|---:|---:|
| 现役基线 | 第0、3轮 | 64 | 2857.724818 ms | 44.651950 ms |
| 新exact候选 | 第1、2轮 | 64 | 2701.569070 ms | 42.212017 ms |

降低比例`1 - 2701.569070 / 2857.724818 = 5.464338%`；预声明`idle_cpu_reduction≥10%`，因此`cpu_gate_passed=false`。各轮末图hash相同。该结果只表示本轮固定输入IDLE像素路径，不是整板CPU降低5.46%。

实际通过项：

- ARM g++ -O3编译成功，17.275秒；候选cpp SHA `91aad0be3f4b8bb81fc4826ca86b96ab1c6057f229b4483325764aca5bade2e2`。
- native22个固定case，2165691个RGB通道比较0差异；重编库legacy入口与原库在这些case上也0差异。不是对所有比例/尺寸/姿态的穷尽证明。
- 7组、164帧真实素材画面与metadata均0差异：IDLE、说话、聆听、点头、关闭潜动、说话退出到IDLE、说话素材池轮换；`quality_passed=true`。
- 新四源Python分发18项离线合成/假C ABI检查通过；详见`EXACT_BENCHMARK_REVIEW.md`和`exact-behavior-tests.log`。不把这些检查称为实GUI运行验证。

旧失败均保留：首轮85秒超时；Q16候选IDLE mean=0.21727超0.1门槛；首个vmlaq float候选在alpha=.6 native自检失败；后续vfmaq明确FMA才在上述case中取得一致。没有覆盖这些失败记录。

本子任务未创建`gui_trial.py`，未写systemd override、未克隆待启用GUI、未停止/重启任何服务、未改生产偏好/数据库/相机配置。父任务原先要求的GUI受保护试运行实现已按新指令取消，不存在已准备可直接部署的控制器或GUI回退入口。现役GUI继续使用原可靠性修复版。

本次结果快照还显示同camera450495下YuNet累计3次超限、受限恢复2次后`LATCHED/recovery_budget_exhausted`，YOLO约9.94Hz、SFace超限0。不能把它隐去或归因已定为测试压力；额外headless进程应全部退出，不再继续并行压测。父任务另行负责留证和受控同版本恢复；恢复不构成本GUI候选通过，也不能用降级/不同负载时段宣称整机收益。

当前新候选仅作未部署的实验工件保存。主任务应优先完成生产可靠性处置和证据交接，后续另选更有收益的CPU热点；本轮不再追加测试或尝试自动promote。
