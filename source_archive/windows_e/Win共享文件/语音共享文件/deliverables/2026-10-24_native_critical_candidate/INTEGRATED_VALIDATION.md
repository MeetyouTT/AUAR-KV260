# 原生三模型 v2 同版集成记录

冻结代码候选：`integrated/native-v2-560d824588eb8f8a`。该编号固定226份源文件内容，包含221份Python（实际214份底座＋7新增、5修改）及5份C/C++。完整Python SHA和AST核对通过；没有复制模型、配置正文、身份库、目标二进制或第三方板载头文件到源码候选。它是代码候选，尚不是可直接启动的生产release。

## 实际通过

- 原生：20组恢复/seed/ACK集成、8组仲裁回归、5组C ABI控制流；20/5组两套ASAN/UBSAN通过。原30ms/5ms/TTL/YOLO优先、完成未知fence保持。
- Python：28项业务回归通过，包含SFace前两probe Deferred/第三probe可用、晚GIL过期、YOLO临时拒绝后的下一轮继续推理、unknown保活、双LATCHED来源计数和启动清理。
- 既有回归：237项运行，235通过、2项私有ELF检查跳过、0失败/错误。实际GUI消费者与camera闭包分开，首次范围混淆的2项失败记录保留。
- 接口：7个C/ctypes结构的尺寸和每个字段offset全部匹配；真实CDLL→当前C++桥→fake依赖12项通过，包括三模型原始字节、SFace三ACK/重放/过期、primary早拒超限、unknown和seal/checkpoint累计承接。
- 目标链接：SDK11.2使用21份实板头交叉编译自有object；板上只做共享库链接，0.795秒、无警告，库SHA`c675ba69…`。无板上cc1编译、无Context/runner创建、候选推理0，生产PID/5YuNet＋3SFace故障及primary3均不变。
- 目标加载：随后在独立进程仅加载该库、读取6个ABI常量，实板确认ABI2、Report88/State432/Seed520/Recovery104/Ack32；factory调用0、候选模型作业0、生产状态不变。**这只证明链接/加载/常量接口，不是模型推理验收。**

实际证据分别在`schedule-integration/checks-result.json`、`business-integration/validation.json`、`v2-roundtrip/result.json`、`v2-target-link-result.json`和`v2-target-constant-abi-result.json`。不同检查有覆盖重叠，不加总为独立业务场景数。r1冻结时尚未做目标加载，其元数据反映冻结时点，随后目标常量结果单独记录。

## 新发现及修复

原生primary在入口/等待阶段deadline过期时也要记结束周期与主周期超限，并锁定PROBATION；不能把拒绝提交当作健康主任务推进。现在primary_calls包含有效结束周期，admissions只表示真实lease，not_submitted明确计未提交。source TTL过期但period未迟到时分开记录，不伪造period late。

普通primary暂时拒绝使用独立`PrimaryAdmissionDeferred`，不会走旧UI的fatal close分支永久停掉YOLO。unknown native仍停止新提交并保留owner。旧Pythonactive锁不跨C调用，释放gate不依赖重新取得GIL；SFace probe成功则用释放后的单次ACK保留原freshness语义。

## 当前实际运行

`current-resume-board.json`：同boot008f3e1b…、camera29563/GUI29588/X1077、三服务active；YOLO约9.95Hz，face worker存活、gap0、primary超限累计3。**YuNet5fault/4恢复后guard LATCHED走CPU；SFace3fault/2恢复后预算耗尽LATCHED，ready=false、完成755次。当前只有YOLO正常DPU。** SFace三次分别约36.081/34.009/31.308ms、均status0/hardcap-only，保留原始数字事件；本轮没有精确native/GIL新探针，不直接归因到硬件或唯一GIL机制。

## 未完成及启用限制

旧生产代码缺少原子seal/export，health既缺attempt_times等内部字段，也不能证明快照后停止前没有新作业。r1只接受前任v2完整seal checkpoint，同boot旧版本首迁移仍被明确拒绝；不通过外部quiescent标记、零预算、重启清计数或把LATCHED改RUNNING绕过。

独立`business-newboot-r2`正在补明确opt-in的新kernel boot入口：旧历史归档，新boot一次marker和独立计数域，旧单调时间不重放。它不会产生当前旧进程缺失的精确checkpoint，也不允许把同boot保护当作新boot解除；r2未完成前不能写为已验收。

真实INT8同输入输出等价、完整三模型业务吞吐/源帧龄/CPU与DPU收益、真人精度、长稳和实际冷启均未执行。等价基准工具已完成20项fake检查，仅可在确认生产owner退出、完整恢复安排就绪的维护窗口使用；unknown必须保留owner，不能timeout kill后自动换owner。当前候选没有替换生产，不能称全部修好。
