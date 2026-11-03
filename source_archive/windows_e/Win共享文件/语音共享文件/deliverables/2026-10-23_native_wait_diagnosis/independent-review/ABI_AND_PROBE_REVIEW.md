# VART边界与低开销调度观测复核

结论：**保持GIL的CPython C采样器正确性检查成立，但主任务ARM完整调用成本门槛失败，未接生产；后续转为独立外部进程观测。** 调度计数能量化runnable排队分量，不能单独证明GIL或VART是根因。当前14个映射库的指纹已由主任务新取证，源码提交仍未匹配。本任务只读本机工件并作主机隔离测试，未接UART/板卡、未创建runner或推理、未改生产或主任务源码。外部方案见`EXTERNAL_PLAN_REVIEW.md`。

## 本机证据与版本边界

主任务当前`aura-native-wait-20261023/preflight.json`已记录camera499773的14个映射库。下面两项与历史camera449083的指纹完全相同，不再是缺失项：

| 映射文件 | 大小 | SHA256 |
|---|---:|---|
| `/usr/lib/python3.9/site-packages/vart.so` | 194720 | `dc6bff9be31b8dc349a72489e06237f8503175805d042025558694823f61de34` |
| `/usr/lib/libvart-runner.so.3.0.0` | 153696 | `c534e4615343d2f58b8f9d1c4b018acfd7726d20acdc42b7fa6ccd2f869650ba` |

本地SDK sample runner库为3219056字节/SHA`7029db11…`/BuildID`6ba63d9c…`；历史SD提取同名runner为153696字节/SHA`d274f2a1…`/BuildID`5bd42056…`。它们均不与上述历史板载文件逐字节相同；大小、SONAME、`3.0.0`或包名不足以建立源码对应。SHA不同也不自动证明`.text`行为不同（例如构建后元数据变更），仍需当前BuildID/代码段关联。

本轮同时确认Python3.9头文件存在、扩展suffix为`.cpython-39-aarch64-linux-gnu.so`、gcc可用、schedstat非零；sysctl不存在。板端信息来自主任务保存的preflight，本独立任务没有亲自执行板端命令。

已保存官方v3.0提交`2057c588c241c3902353bc618afc8ab214d7aeed`的`runner_py_module.cpp`：258–290行在GIL保护下构造TensorBuffer，`self->execute_async`的局部作用域显式`gil_scoped_release`，返回后重获GIL再登记job；291–302行wait lambda未显式释放GIL。它证明这份上游源码的路径，**不能替代本板绑定匹配**。原件及来源SHA在`aura-affinity-review-20261022/vart-source/provenance.json`。

## 现役Python计时还有提交前盲区

当前`PinnedRunner.execute_encoded`执行顺序为：slot取得→`execute_start`诊断→可选`pre_execute()`→`runner.execute_async([source], outputs)`→`execute_return`→wait。YuNet的`scheduled()`在有准入guard时实际传入`pre_execute=check`，SFace未传。

所以现有`execute_wall`还包括mark返回后的Python工作、check以及两者之间的调度/GIL间隙，不严格等于绑定函数内部时长。新观测应增加check完成后的`before_vart_call`和返回后的`after_vart_return`，保留原execute/hardcap字段及其口径。Python标记到下一条native指令仍有微小盲区；若要真正区分native返回与GIL重获，最终需要匹配绑定内部端点，不能用Python端外推。

## C采样字段与判读

建议每个调用返回固定数值元组：PID/TID、mono_before/after、thread_cpu_before/after、sched runtime/run_delay/pcount、nvcsw/nivcsw、各读取成功位/errno。256字节有界读取、严格3个无符号字段；跨PID/TID、计数倒退、缺失或全零不可相减成“0等待”。不修改内核开关。

本地Linux5.15.36原始proc实现直接读`se.sum_exec_runtime`、`sched_info.run_delay/pcount`；sched_info关闭时输出`0 0 0`。运行时间字段可能滞后当前运行段，总CPU差主用`CLOCK_THREAD_CPUTIME_ID`。历史板载schedstat非零而`sched_schedstats` sysctl不存在已被实际记录，两者不矛盾。

| 观测 | 可支持的结论 | 不能推出 |
|---|---|---|
| run_delay增量较大 | 存在可运行但未获得CPU的时间 | 原因只有CPU竞争，GIL/VART已排除 |
| wall远大于线程CPU，run_delay很小 | 非运行时间以非runnable等待或端点差为主 | 等待一定是GIL或一定是驱动 |
| voluntary增加 | 存在主动阻塞/睡眠类切换 | 等待时长、持锁方、GIL归因 |
| involuntary不增加 | 该计数未新增 | 没有runqueue等待（主动阻塞后唤醒仍可能排队） |

`wall - thread_cpu - run_delay`仅能标作未归因残差，字段不是原子快照，区间也不同，不应要求逐纳秒闭合或把负残差强制当0。调度、GIL及native阻塞可以共同发生，不应强制互斥分类。

## 低开销实现/验收边界

- 使用真正CPython扩展的普通C入口，不在采样内主动释放GIL；`ctypes.CDLL`会重新引入主动release/reacquire问题。持GIL只是减少观测器自身的GIL等待，不保证proc读取不会阻塞或线程不被抢占。
- 初版可open/read/close降低缓存生命周期复杂度；如复用fd，须PID/TID绑定、fork后重开、线程退出close，不让旧线程fd成为新线程样本。
- 同时计量Python外层完整`sample()`调用和C内部读取。元组/PyLong构造及包装处理不能落在开销门槛之外；保留CPU、wall、P99/max及停用原因，不能只看均值。
- 先无DPU的固定线程隔离开销/字段检查，再正常负载同版短观测；原30ms/5ms计入所有采样成本、不扣除。当前YuNet处于LATCHED，只接生产诊断不会自然产生新的YuNet DPU样本；需要主任务另行设计有保护的受控观测，不能靠反复重启清旧计数捕获。

## 主任务最少还需读取的信息

1. 当前499773的VART/XIR/XRT路径、SHA/大小已经保存；剩余优先是ELF BuildID/代码段关联和本地Python原始ELF副本。历史`readelf -n libxir`曾超3秒，不宜重复无限制命令。
2. 当前vart/xir/xrt包版本/来源。只作构建关联，不能仅凭包名证明源码。
3. 若要native VART封装，再取匹配的runner/tensor_buffer/XIR头文件及SHA、实际DT_NEEDED。**当前Linux计数C扩展不依赖VART/XIR ABI，可与此核对并行推进。**

后续C/adapter独立主机检查共17项通过，见`C_AND_ADAPTER_REVIEW.md`。这不等于ARM开销或DPU故障实验；仍没有声称当前板库已释放GIL、30ms是DPU计算时间或发现了唯一根因。输入证据路径/SHA见`review-provenance.json`。
