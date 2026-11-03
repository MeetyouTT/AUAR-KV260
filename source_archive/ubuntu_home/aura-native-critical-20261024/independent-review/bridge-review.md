# 原生桥独立审查：模型与缓冲生命周期

审查仅使用Ubuntu本地源码、fake VART/XIR与注入的registry；未连接板卡、未调用真实VART、未创建context/runner factory、未改生产源码。本报告不替代板级同输入推理或真实故障验收。

**最终复核：** C++桥 `3dfd77a2ec137468aa7af1329188dbf36c037ba54c83c4ae9128ae8c6bb083fd`（`bridge-final-reviewed/`，清单 `bridge-final-source-manifest.json`），绑定 `edbddc1e682a7a2c83facb7ee1c436b40940cdcf4a920e67a2c2e0aa723ea58c`（`binding-reviewed-final.py`）。最终C++10组fake控制流、绑定20项及独立post-adopt交错通过。结果是“可以继续接线开发，尚不能部署”。此前快照、反例及结果保留为历史，不覆盖成最终版证据。

此前生命周期首修快照为 `bridge-yolo-reviewed/native_bridge.cpp` SHA256 `f0301ad8d65d0569afb8fe5215e4dc085cd3581670eae8cbd6510e07379049aa`，头文件 `f94fde13e8af67e04d2d860387fe48ab9bbdbeaf3ca2842af6f6449bfecaff5e`；原始清单见 `bridge-yolo-source-manifest.json`。

## 已确认并修正的阻断

1. **完成未知后的输入覆盖。** 初版 optional execute 在检查gate之前先memcpy；如果前一次native完成未知，后续请求虽被fence拒绝，仍可能覆盖正在使用的输入。当前在runner operation锁后、任何memcpy前检查fenced，测试确认第二次native调用不发生、原输入保持、输出不发布、runner保留。原始 `test_bridge_review.cpp` 已过时且期待旧覆盖反例，不可把其空结果当回归通过。当前正向证据是 `bridge-current-result.json`，新生命周期快照也重新执行同6组。

2. **YOLO借用资源不能保证未知完成后保活。** 旧桥 `aefecc93...` 只保存YOLO库和owner FD，detector、BGR、output与count均借用调用者。fenced保留Context无法阻止旧Python `DpuYoloX.close()` 直接destroy detector。`test_yolo_explicit_close.py`实际执行参考类AST的close，证明即使另有强引用仍会destroy/关闭owner（资源为fake，未运行构造）。

   新快照改成Context独占adopt detector，并拥有持久BGR/output/count；unknown后拒绝resize/copy，正常完成才复制caller输出。context正常close恰一次调用destroy；fenced不close。registry在进程期间保留，避免fenced模型在静态析构阶段被隐式销毁。Python绑定仍须完成下面的原子转移合同，C++改动本身不能证明旧owner不会再destroy。

## 实际验证

`test_bridge_yolo.cpp`以捕获快照编译，`-std=c++17 -O2 -Wall -Wextra -Werror -pthread`通过；`bridge-yolo-result.json`为10组通过（6 optional＋4 YOLO），非重复相加成16组：

- optional：正常execute/wait与输出；unknown后输入不变、拒绝再次提交与关闭；source TTL到期不提交；同runner并发拒绝且在途close不释放；wait失败fence；uint32 job ID超int范围不窄化、fence。
- YOLO：padded BGR逐行复制且内部input/output/count不借用caller指针，snapshot字段/size正确；unknown后buffer与detector保留、caller输出不发布；重复adopt拒绝、正常close恰一次destroy；并发execute拒绝且在途context close不释放。
- 并发close检查主动释放fixture强引用，使拒绝依赖实际在途引用；YOLO fenced close也先移除fixture强引用，避免测试自身额外引用掩盖错误。

测试会在fixture结束时清理fake registry，清理对象没有真实在途硬件；这不是生产fenced资源允许销毁的证明。生产只能走受控API，不能模仿测试直接clear registry。

## 接线前必须完成的合同

1. **Python原子adopt（候选已实现并软件验证）。** 持原detector.lock，先清除旧handle并暂存指针，再调用强异常保证的native adopt。只有明确失败才还原；结果未知时保留Context/资源，不把旧handle重新暴露。绑定拒绝fork对象，另以生命周期锁串行adopt/close。最终20项fake用例和独立交错通过；尚未对真实既有detector做转移验收。
2. **唯一执行权。** YOLO/YuNet/SFace须共享同一native Context，且旧Python lease不可继续跨native调用阻挡YOLO。创建新runner、adopt与切换只在停止旧调用后进行；当前C++ runner_create并未与真实DPU gate串行化，不可在运行中随意创建模型。
3. **恢复与历史。** 当前NativeLease没有disabled解除、受限恢复permit或旧fault/attempt/recovery seed导入。若直接接生产，一次optional超限会永久disabled，劣于现有自动恢复。必须迁移10s/600s两轮/三probe、SFace前两Deferred及owner-fence语义，不能靠销毁重建Context重置状态。
4. **结果可用性。** C返回code0仅证明native完成/status0；hardcap/guard仍可能为true。Python必须结合保护与策略、返回时source TTL验证，禁止将超限或恢复前两probe的SFace结果用于匹配/登记。snapshot不能代替完整恢复policy状态。
5. **原模型等价。** 固定模型/库SHA、输入输出port名称/维度/XINT8/fix_point、预处理/反量化/阈值/模板空间，并使用同一输入核对原始INT8和最终结果。纯fake通过不能证明实际VART TensorBuffer、DMA同步与模型等价。
6. **计时和可用性边界。** 确认native/Python共同CLOCK_MONOTONIC坐标，界定uint64范围与deadline更新。30ms是返回后判断的保护线；当前wait(-1)不能中断native永久阻塞。C++消除Python重获GIL后释放gate的依赖，但不能保证消除Linux runqueue长尾。真实三模型/GUI音频交互、未知完成、冷启与长期稳定均待验。

现阶段未发现新的optional缓冲/关闭阻断；YOLO原版生命周期缺口已由新C++快照修正并经fake控制流验证，但Python转移、恢复/seed和真实三模型接线仍是部署阻断。

## Python绑定并发复核

初始绑定 `309a1e31079b435bca8c1d82bf0ebeecdda73b3ec187435a77408c60af3e4b07` 存在一个已实跑的生命周期反例：native adopt返回后、`self.adopted=True`前暂停，另一线程close Context成功；adopt恢复后标记True，但handle已0，原owner FD关闭被跳过。C++ shared_ptr只覆盖native调用期间，不能保护其后的Python记账。证据 `binding-lifecycle-counterexample-result.json`，输入快照与测试独立保留。

主实现随后加独立RLock，只覆盖adopt/create/close和句柄/registry记账，不覆盖任何推理调用。修订绑定 `01830e7994f5a0198ac4843be07e1aa95d461f791132e07ea3d77496e413240e` 在完全相同post-native点通过正向检查：锁仍被adopt持有，另一线程close未进入native；恢复后正常close并关闭原owner FD。`binding-lifecycle-regression-result.json` 记录本地实跑通过，也通过AST确认两个execute方法不获取Python上下文锁。

该阶段正向检查仅证明并发交错解决，不包含初始化/close结果未知。主实现随后补充create/close的BaseException保留：结果未知即quarantine并禁止后续执行/重试，保留原owner引用和资源，不将未知当成明确失败回滚。最终绑定 `edbddc1e...` 的20项用例由本代理重新运行通过，包含context/runner factory中断、close在fake native已删资源后中断、不得再次destroy或使用旧句柄；这些均是fake native软件故障注入，不是真实信号或VART故障板测。

`bridge-yolo-sanitizer-result.json` 为同一C++快照10组以AddressSanitizer/UndefinedBehaviorSanitizer编译运行通过，stderr空。它补充软件内存/未定义行为检查，仍不是硬件buffer生命周期或实际VART ABI运行验证。

## 最终小复核

- 最终绑定的同一post-adopt native返回交错重新检查通过，owner FD最终正常关闭；两个execute方法仍无Python生命周期锁。证据 `binding-final-result.json`，执行前后绑定字节保持一致。
- 最终C++新增“先adopt YOLO，才能创建optional runner”；读取detector使用与adopt相同的短yolo_operation锁，避免两个不同mutex保护同一裸指针。锁释放后Context引用保证对象不能被close，detector接管后不会重新置空。Python也强制相同前置条件，已由20项中的专用拒绝用例覆盖。
- 最终 `bridge-final-result.json` 为同10组重新编译通过；`bridge-final-sanitizer-result.json` 对同一最终3dfd77a2…快照以ASAN/UBSAN重编译运行亦通过、stderr空。仅startup前置约束变化，未把先前fake测试写成真实模型结果。主代理另有实际CDLL→C++桥→fake VART往返及匹配目标头文件的编译证据，由其按最新SHA单独记录，本报告不把未由本代理执行的结果冒作本代理实测。

**剩余部署阻断是尚未实现的恢复/历史seed合同与全业务接线，而不是上述已实现的软件中断保留。** 必须先完成唯一gate的三模型适配、旧Python lease退出、10s/600s两轮三probe及SFace前两Deferred、旧counter/owner fence迁移，然后同输入模型等价和受控实板业务验收。实际模型/库/身份数据/阈值与30ms/5ms保护应保持；尚不能宣称长尾已根治。
