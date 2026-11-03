# 分阶段事务代码草案：EXECUTION_NOT_READY

`platform_transaction_draft.py` 是只在本机审阅和隔离模拟中使用的状态控制器。它没有SSH、shell、设备、板端文件或真实服务适配器；导入和运行该文件只会定义类或打印未就绪清单。`BoardBackendUnavailable`无法构造真实事务；`ReviewTransaction`只接受显式`simulation_only=True`的隔离backend。没有execute-board、run-all、force、kill、清锁、ARM、COMMIT、GUI启动或恢复监听入口。

当前真实事实另存 `TRANSACTION_REVIEW_CONTEXT.json`，只引用已经实读的boot、startup、相机身份、计数下界和固件指纹。该文件不是板端会话，未生成stop intent、未来checkpoint、wide FDT、新PID或用户批准回执。用户目前只确认已通电且能观察；PL切换/参考/新运动授权均未记录。

## 可以审阅的阶段接口

| 单次显式方法 | 前态 | 本次行为/后态 | 保持与拒绝 |
| --- | --- | --- | --- |
| `preflight()` | NEW | 重新核身份/owner/暂停和来源，PREFLIGHTED | 闭包不符进入HOLD |
| `request_normal_stop(approval)` | PREFLIGHTED | 保存匹配上下文的意图后只请求一次正常停止，STOP_PENDING | 未批准不创建意图；不kill |
| `observe_normal_stop()` | STOP_PENDING | 只读观察；正常退出且无DPU owner后CAMERA_STOPPED | pending保持；不再次发送stop |
| `validate_and_seal_checkpoint(approval)` | CAMERA_STOPPED | 读取真正原始文件→原完整validator→确认未消费→保存封存意图→原字节独占封存，CHECKPOINT_SEALED | 原owner/boot/birth、counter下界、时钟、前驱链不符均HOLD；未知封存结果HOLD不覆盖 |
| `request_unload(approval)` | CHECKPOINT_SEALED | 重核无owner、真实checkpoint，再保存意图并只启动一次卸载，UNLOAD_PENDING | 通信未知即pending；不重发 |
| `observe_unload()` | UNLOAD_PENDING | 只读关联已保存job/意图；实际client结果+平台读回通过后UNLOADED | 只见wrapper RC0不能通过 |
| `request_load_wide(approval)` | UNLOADED | 再核无owner/未消费真实checkpoint，保存意图后只启动一次load，LOAD_PENDING | 无自动重试 |
| `observe_load_wide()` | LOAD_PENDING | 实际client身份/退出、wide/VART/配套/新FDT读回通过后WIDE_VERIFIED | pending保持；错配/失败HOLD |
| `request_id_stop_only(approval)` | WIDE_VERIFIED | 从本次真实新FDT形成context，只调用原ID/STOP入口，ID_STOP_PENDING | 第一项设备命令必须STOP；不带物理参考 |
| `observe_id_stop_only()` | ID_STOP_PENDING | 只读关联唯一可信job；核ID/ABI/build、STOP flags/lease0和transport关闭，ID_STOP_VERIFIED | 不允许额外MMIO owner；回执出现BIND/REF/ARM/COMMIT即HOLD |
| `request_restore_original_camera(approval)` | ID_STOP_VERIFIED | 再核wide/owner/真实checkpoint未消费，保存意图后启动原相机一次，CAMERA_START_PENDING | 不预填新PID、不重发start |
| `observe_restored_camera()` | CAMERA_START_PENDING | 原命令的真实新owner、唯一DPU、源推进、sealed seed逐值恢复和本次消费通过，CAMERA_RESTORED_PLATFORM_ONLY_NO_MOTION | pending保持；错误或历史被清除HOLD；不启动GUI或运动 |

每次调用都需核boot/startup/GUI无writer/监听暂停和完整owner清单。ID/STOP pending阶段仅允许与保存的job身份和intent精确关联的单一临时transport；其他MMIO owner不被豁免。wide已确认后还会重核同一个fresh context。不存在“超时后回到上一阶段重发”的路径。

`Approval`在草案里也仅允许模拟scope。真实批准应由唯一主操作者在最终发布后绑定具体操作、当前上下文SHA和真实用户回执；不能将“通电可观察”填写成PL或运动批准。模拟测试中的`SIMULATION_APPROVAL_ONLY`无实板含义。

## 真实适配器的待发布契约

以下接口在代码中只是隔离fake实现，尚无真实实现。这是不能执行板端事务的主要技术原因：

| 接口 | 真实实现必须证明 |
| --- | --- |
| `recheck` | 当前boot/startup、原或新owner真实PID/birth/cmdline、完整maps+fd、无额外DPU/MMIO、GUI/监听/服务shutdown保护；每次fresh读取 |
| 持久ledger | 创建当前boot独占会话根和唯一owner，意图须在命令前fsync；崩溃重入读取已有意图/job，不重建NEW后重新发送；不删除已有锁/marker |
| stop请求/观察 | 只发一次`systemctl stop --no-block`；成功必须正常退出和真实最终文件；pending不kill，原不确定owner保留 |
| checkpoint校验 | 对同一个hash pin调用原`load_business_checkpoint`；来源/模块namespace先核验，不能调用`consume_checkpoint`/NativeContext/runner；真实stop intent时间和单调时钟由适配器比对 |
| 原字节封存 | 用O_EXCL写精确原始字节、fsync并回读SHA；不重序列化、修补或替换checkpoint指针；未知提交结果不覆盖或再写 |
| loader启动/观察 | 保存实际`dfx-mgr-client`的PID/birth/命令指纹和结果，不能把xmutil外壳0当子结果；超时保留原job，fresh只读关联真实daemon状态；没有可信结论就pending/HOLD |
| ID/STOP | 原bench SHA及完整配套先核；用本次FDT生成context并独占输出文件；原transport/close收据；首写与命令集仅STOP；不绕过原锁或平台标识 |
| 恢复 | 原服务启动一次；实际新owner来自systemd+proc+health；原audit的exact seed与sealed文档逐值相同、消费只发生一次；保持原模型/图库选择、保护历史和源推进 |

控制器当前的`persist_simulation_state`只是测试快照，不能被解释为已实现持久板端ledger。原始validator在测试中是fake：测试证明调用顺序和拒绝传播，没有声称执行过真实validator或C/native设备。

## 原完整validator的补充静态审阅

已额外实读并保存 `startup_sources_readonly_03.json`、`04.json`：

- `native_protection.py` SHA `b8637c2aa387915a49ef0fd7a1c7cb9d015fb71802c4eaa11539a64466db1faa`。
- `native_binding.py` SHA `5f385c03cf84b1f9ba3afe4d4a6cfd3022ba639aba06b8d923f83783bfd48da6`。顶层仅stdlib、常量、ctypes结构、函数和类定义；加载Native DSO发生于`NativeContext.__init__`，原validator不会构造它。
- candidate的`board/__init__.py`不存在，该层是namespace；`board/vision/__init__.py` SHA `091e8b3b95a7f46655ba0c5275630eb3aee2079b57a95a0f5ef35d4e44c47284`，仅docstring。
- 原`load_business_checkpoint`读hash pin JSON、校验完整静止/计数/boot时钟、导入C结构并构造seed结构、读取前驱`/proc`身份、检查marker不存在；不写marker、不CDLL、不打开音频/数据库/设备、不创建runner。

真实适配器仍需控制clean Python namespace与`sys.path/sys.modules`，确认加载的正是上述路径，防止其他`board`包遮蔽。独立只读安全审阅另在`parallel_platform_review`进行。本子代理没有为了测试validator而先停止相机，也没有直接import可能含顶层设备动作的维护脚本。

## 已完成的隔离验证

`test_platform_transaction_draft.py` 的25项测试通过，实证记录 `transaction_validation.json`。覆盖阶段跳跃拒绝、缺少批准、错误上下文、正常停止pending不重发、不kill、写前意图、旧boot/累计overrun清零/validator拒绝、精确非规范JSON原字节封存、未知封存保持、loader pending及未知launch不重发、真实子退出失败与旧VART拒绝、ID/STOP优先、外来MMIO owner阻断、恢复pending不重启、exact seed历史一致、全路径保持GUI/监听/运动关闭。

所有测试owner、文件、job和批准均是明确标记的synthetic内存对象，没有SSH、板端文件、真实checkpoint调用、MMIO或音频。通过这些测试不能将发布状态从EXECUTION_NOT_READY改成READY。真实适配器、持久ledger、独立审阅与具体用户批准未落实前，不应添加能连跑板卡的入口。
