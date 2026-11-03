# v15分段计时独立审查

2026-10-26。用户改为两个终端后，子任务仅做本机源码审查和隔离测试。没有访问UART、板端HTTP、MMIO、模型或服务，也没有改已冻结v15源。板端USB告警、CPU及恢复事实由主端独占采集，本回执不代验。

## 结论

当前正常路径没有发现会阻塞部署的返回值、原异常、回调次序或线程隔离问题。`entry.py`在实际FaceTargetService、DpuYuNet实例创建前安装包装，因此实例保存的`execute=self.scheduled`回调会进入计时层。后续operator包装只修改原生C函数的线程策略及SFace接口，不覆盖这里包装的DpuYuNet/NativePinnedRunner方法。

`stage_timing.measured`只记录调用线程的wall与thread-CPU，不保留图像、输出张量或身份正文。TLS在`finally`恢复，已发布账本为独立新对象，后续process不会修改它。OpenCV全局函数虽被包装，但仅当本线程处于有效process和compat范围时记录；其他线程直接调用原函数。

`native_call_with_result_handling`包含准入调用、结果确认、指标及反量化，不能视为纯DPU核时间；`native_admission_loop`减去其中原生调用的时长，只能称等待与Python开销。`decode_and_compat_bookkeeping_ms`从compat总调用减去顺序且不重叠的resize/blob/layout/forward，保留NMS和其余后处理。源代码的嵌套时长与wall减thread-CPU说明准确，不能把所有阶段直接相加。

## 追加验证

- 原v15测试54项通过。
- 本目录追加6项检查通过：其它线程不串入当前ledger；回调异常原样传播；已发布对象不被下一轮改写；长数字/最长协议上下文的完整包低于8192字节；全256灰阶以及4组合成BGR图经过原resize/blob/NHWC流程后，与整数编码逐字节相同。
- v15本地7项运行源指纹与冻结manifest保持一致。详细数量、包长和本机假调用成本见[REVIEW_RESULTS.json](REVIEW_RESULTS.json)。

运行：`/home/ghmd/kv260-adaptation-check-20261006/identity/.venv/bin/python -m unittest discover -s /home/ghmd/aura-pan-follow-shadow-20261024/v15_local_review_20261026 -p 'test_*.py'`。

## 分析时必须保留的边界

1. `detector_timing`和`detector_stages`由相邻的finally分别发布。快照可能短暂拿到相邻源帧，两者都有`frame_id/source_mono_ms`，必须匹配后再联合分析，不能默认属于同一轮。它不影响运动源的既有时效与身份门槛。
2. `clip((pixel+1)//2,127)`的等价域是原始uint8整数像素、原BGR布局、原resize、固定fix-point=7。实现前必须提升到uint16或更宽整数；直接uint8加一会在255处溢出成0，和原127结果不同。这里只证明输入量化的数学/字节等价，未实现优化，未量板端性能或模型准确率。
3. 计时API在业务try之前取时。若`thread_time_ns`等API本身抛异常，包装可能阻止原业务调用；当前目标已支持该API且没有观察到此故障，因此列为诊断韧性改进，不作为现发故障或部署阻塞。未来若需处理，应保留原业务异常，并用缺失标记表示不可用CPU时间。
4. 8192字节检查基于固定字段集合及长数值压力包，实际运行时仍应记录包长和阶段开销。测试不能替代真实KV260成本/帧率或现场随动验收。
