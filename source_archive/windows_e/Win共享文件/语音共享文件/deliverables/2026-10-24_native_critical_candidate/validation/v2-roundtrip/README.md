# v2 真实 ctypes/C++ 接口往返

此检查在Ubuntu本机编译临时共享库，用生产候选的 `NativeContext`、`NativeRunner` 和 `native_protection` 经实际 `ctypes.CDLL` 调用候选C ABI。没有连接板卡、没有加载VART或模型、真实DPU作业0。

`fake_v2_dso.cpp`只替换硬件owner工厂及外部XIR/VART/YOLO依赖。其余仲裁、恢复、源TTL、post-release ACK、自有缓冲、状态结构、checkpoint、关闭与unknown保留均使用当前 `schedule-integration` 原始实现。工厂不会取得project/hardware锁、不会dlopen原YOLO库；它为每次检查建立显式fake Context，故**不验证真实工厂的进程唯一性或跨进程硬件所有权**，也不能把本机创建多个Context当作生产许可。真实工厂的单进程禁止重建由原C++套件覆盖。

运行：

```bash
cd /home/ghmd/aura-native-critical-20261024/v2-roundtrip
python3 run_roundtrip.py
```

该命令快照当前五份C++候选源码，使用明确标记的fake头编译临时DSO，临时建立fake model tag/manifest，只加载业务候选binding/protection模块。全部源码和fake头SHA在运行前固定，结束时复查未改变；临时DSO与tag随检查结束删除，不把fake库当目标板ELF交付。

12项实测覆盖：

- C/Python两侧实际ABI尺寸88/32/104/432/520一致。
- SFace的0/42/127/128/255编码字节及YuNet四端口原始输出完整往返。
- YOLO已移交句柄、确认输出与恰好一次destroy，旧owner.close不再销毁该句柄。
- SFace前三次确认native输出始终存在，前两ACK不准发布、第3ACK才业务ready；重放不重复计成功。
- native完成后/Python确认前超过TTL不推进probe；结果访问再次检查TTL。
- pending SFace确认不占DPU执行权，YOLO仍能推进；同任务新提交被拒绝且不覆盖token。
- 已进入PROBATION时primary入口deadline过期，主周期调用/迟到/未提交计数增长并锁定；旧ACK不能复活。
- native sourceTTL过期不提交；unknown completion fence、无输出，模型/Context拒绝关闭并被Python引用保留。
- 精确checkpoint先seal，旧gate后续拒绝；fake新Context承接相同累计后继续增长。
- 另一个Python线程在编译函数内50ms睡眠区间能进入编译计数函数，直接证明此CDLL调用释放GIL；不把调用前后线程进展当释放证据。

时钟使用仅fixture可控的单调ns，故冷却与TTL边界无需真实等待10秒。Python binding的monotonic读取被测试显式对齐同一个fixture clock；该方法不代表真实Linux调度、GIL重获延迟分布或板上时延已验证。

首轮12项中1项失败是测试构造只停在COOLDOWN、未提交首probe进入PROBATION，却期望primary迟到锁PROBATION。已将测试修为实际产生pending token再迟到，失败记录以`result-prior-*.json`保留，后续完整通过；没有把该测试错误写成候选代码缺陷。

最新源码SHA及实际输出见`result.json`。接口/缓冲/保护在fake依赖下通过仍不能替代真实INT8模型输出等价、准确率、板上保护/资源占用或长稳验收；本候选不得据此直接部署。
