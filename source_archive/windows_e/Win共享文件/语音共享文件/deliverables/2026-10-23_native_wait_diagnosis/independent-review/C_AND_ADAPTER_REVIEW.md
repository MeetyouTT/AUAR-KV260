# C采样器及adapter独立主机复核

当前C源`9fa707c081e03ab95bea34d0624a4bb88efd9b78037935cc81a79219962e6048`、adapter源`18561f3a1c1a2d663332ce863340f43be765f0e2f509dae5abdf43f53a8863c8`。**主机正确性检查未发现阻断；随后主任务ARM实编/语义通过，但成本失败，不能接生产。** 完整调用meanCPU183193ns>100000ns、P99wall6.856ms>1ms，见`board-result.json`。本任务没有接板、创建DPU owner或更改root源码。

C源以本机Python3.8头文件编译（x86_64，`-std=c11 -O2 -Wall -Wextra -fPIC -shared`），无warning。10项真实C扩展/解析检查通过：10个数值端点、当前PID/TID、参数与部分初始化、重复init/close、1000次采样fd不增长、异线程拒采/close/dealloc、fork子拒绝父Probe且父仍可用、已知sleep、uint64边界/溢出/NUL/缺失/额外字段/257字节拒绝。

adapter另7项假factory检查通过：字段映射、全零schedstat不可用、非法结果隔离、CPU成本停用与低CPU迟wall保留、最多2个调用线程reader、跨PID/TID/计数倒退delta，以及持有父线程锁时fork后的有界sample/snapshot/close。

初轮该fork反例实际失败：子进程等待继承锁，1秒alarm退出status14，证据`adapter-tests-initial.log`保留。root把PID拒绝移到锁之前，并给子进程snapshot/close不等待继承锁的路径；随后`adapter-tests-final.log`7项全过，父reader继续可用。失败时源码在并发修订，未为旧版封存SHA，不将该失败SHA错误归给当前修复版。

资源与边界判断：

- C对象只保存fd/PID/TID，无Python引用环；初始化失败、重复初始化、dealloc和幂等close路径有界。每个对象必须在实际采样线程构造；adapter惰性创建满足这一点，主线程不应提前sample占用两个reader名额。
- 当前C入口保持GIL，没有allow-threads；PID/TID/fork错误在读取前拒绝。正常调用由CPython保证GIL，`PyGILState_Check`不是对任意无GIL C调用的安全承诺。
- C内部端点不含对象构造/owner检查，adapter内部计时不含最后统计更新；当前bench外层包含完整调用及全字段prefix消费，口径正确。门槛不能拿内部read时间冒充全成本。
- 对照observer若自禁用，只统计有效样本并注明stopped_early；空集合必须返回count0/其余None，不能计算成0成本。root已补此路径，native仍须1000个有效完整样本才能通过门槛。
- `run_delay`、CPU、wall和切换计数只记录原始数值，不从hardcap扣时间，不直接标GIL原因。读取自身仍可能被调度；持GIL的短proc读也可能延迟其它Python线程，需ARM实际尾部成本确认。

未完成：生产trace集成及实际VART故障归因；ARM成本未达门槛，未部署。`host-build/`下二进制只属于本机测试，不能作为ARM产物或生产依赖。独立测试脚本均在本目录，输入与输出SHA见`review-provenance.json`。
