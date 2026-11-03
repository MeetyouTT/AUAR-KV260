# 原生 DPU 执行路径修复状态

**最新状态：用户改为只开一个终端后，其他代理已停止。r2 `native-v2-d7256b06808509c9`已冻结，222 Python/5 C++；62业务与迁移、237旧回归（2跳过）及12真实CDLL-fake接口检查通过，原生20/8/5＋SAN过。板上链接/常量接口及222源预备成功，当前boot预检正确拒绝legacy，未启模型/切服务/重启。只有YOLO DPU正常；YuNet5fault/4恢复LATCHED CPU，SFace3fault/2恢复LATCHED且ready=false。** 详见共享[最新交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-24_native_critical_candidate/README.md)与[business-newboot-r2/README.md](business-newboot-r2/README.md)。下方多路/尚未实现迁移及SFace仍DPU为此前阶段。

本目录是实现与验证中的候选，没有替换生产，也没有提交真实DPU作业。UTC2026-10-24（洛杉矶10-23），用户最新允许多终端：root独占板卡，三路本机任务分别做恢复policy、原生调度/seed、Python业务接线。

## 当前板卡

见 [final-board-read-only.json](final-board-read-only.json)：同boot008f3e1b…、camera29563/GUI29588/X1077，服务active/NRestarts0；YOLO约9.96Hz，worker存活、gap累计0、primary累计超限3。**YuNet第5次超限后LATCHED退CPU；YOLO/SFace仍DPU。** SFace累计391次完成/超限0，不代表身份准确率验收。

event62778约36.5ms，execute标记35.666ms/线程CPU1.201ms，native status0，hardcap/guard均触发。保留5次故障、4次恢复，不重启或清零解除锁定。原生产4源、持久覆盖、原unit、身份配置/INT8库SHA及三个PID保持，见 [production-preservation-result.json](production-preservation-result.json)。probe/instance为空、线程nice0、真实帧推进时CU统计不变；本轮没有启用新探针/统计。

原handoff 7e8eaf3f…只支持clean或双方disabled且YuNet零attempt的迁移，不能直接承接当前mixed5fault/4recovery历史；健康快照又缺精确attempt_times等内部字段。新严格导出/承接正在实现，不伪造零预算或解锁LATCHED。

## 已有实现

`native_lease.hpp`将准入→原生提交/wait→确认→保护决策/释放放在同次原生调用内，保留30ms/5ms、YOLO优先、TTL、动态deadline复查与unknown fence。`native_bridge.cpp/h`使用固定指纹、batch1/XINT8、VART端口顺序和有界自有缓冲；输入拷贝在取得执行权前，确认完成后才拷贝输出。unknown后模型/缓冲保留且不覆盖。

YOLO原对象受控移交到同一个Context，保持原算法/C库；Context拥有detector和BGR/输出，可选模型必须先确认YOLO已移交。原owner FD副本与独立gate token避免新owner/重复gate。独立审查复现的准入边界、unknown输入覆盖、YOLO生命周期、adopt/close交错及detector跨锁读取已修。

`native_binding.py`提供SHA/ABI/张量校验，CDLL整段释放GIL；生命周期锁覆盖移交/创建/关闭及句柄记账，不包住推理调用。中断/未知结果保留，明确拒绝才恢复旧句柄。结果访问时复查源TTL，防止等待GIL或发布过程中数据过期。

原生记录start/native_return/release_decision/after_unlock，决策点与unlock后观测点分开。普通Linux仍可能在任意指令处被调度走，不声称硬实时保证；不能靠移动计时边界、重启清计数或调高阈值称通过。

## 验证范围

| 检查 | 结果 | 范围 |
| --- | --- | --- |
| 原生仲裁 | 8组普通编译、ASAN/UBSAN通过 | fake回调，无模型 |
| 独立准入修正 | 4项通过 | fake时钟，原反例保留 |
| 张量布局 | 6组通过 | 尺寸/溢出/越界/C ABI |
| C++桥独立审查 | 10组及ASAN/UBSAN通过 | fake VART/XIR、移交/关闭 |
| Python绑定 | 21项通过 | fake C ABI，含中断/TTL |
| 实际ctypes→C++接口往返 | 5项通过 | fake工厂与VART/XIR，真实CDLL/结构/缓冲 |
| 最新C++源 | 本机语法和AArch64对象交叉编译通过 | 实板21份依赖头；未做最新目标链接/加载 |
| 历史首版目标桥 | KV260编译链接、8组仲裁/6组布局通过 | 库未加载、DPU作业0；早于当前生命周期修复 |

不同检查有覆盖重叠，不合计为独立用例数。独立绑定审查固定edbddc1e…，其后根侧新增TTL复查由21项及5项接口检查覆盖，不能冒称旧独立报告已复核新SHA。

首版目标编译前后生产fault3→4，编译/隔离过但生产观察不干净，因果未证明；35秒UART前台超时后已只读取回实际成功报告，见 [first-target-compile-assessment.json](first-target-compile-assessment.json)。后续编译改本机；后台编译helper已修订、未上板执行。最终只读核验首轮漏写aura子目录导致路径错误、无mutation，修正后完成。

## 正在补齐

原生恢复policy、严格seed及全部累计承接、SFace前两probe不发布、三模型业务调用与健康字段。旧Python active执行权不能继续跨C调用持有。完成整合后才做维护窗口内同输入真模型输出等价、三模型业务/CPU/DPU对照及长稳。当前候选不能部署或解除现役LATCHED，更不能称根治。

共享只交付自有源码、数字证据与SHA，不复制权重、目标ELF/对象、第三方板载头文件正文、UART、人脸/向量/库内容。模型/身份空间/阈值、GUI/语音、PL/运动边界保持。
