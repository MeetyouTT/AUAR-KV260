# YuNet 最新帧有界重试：离线候选

主任务集成修正版：专项39项及既有67＋66回归通过，另有5项独立反例审查通过；原37项为父版本记录。25ms退让从拒绝返回后另行起算，200ms绝对截止仍从首个准入尝试起算；health只在显式重试开启时公开数字状态。native前撤回增加`withdrawn_after_slot`，允许与原诊断native_failed比对；真实execute/wait失败不能以撤回计数隐藏。本修正版的manifest与源SHA优先于下方父版本描述，仍未板验证。

状态：**默认关闭，尚未上板，尚无性能/时效收益结论。** 本目录只准备可审查代码和无设备软件证据，不修改生产、共享冻结交付、配置、模型、GIL、CPU 亲和性、音频或运动。真实板卡操作由主任务独占。

## 要解决的现象与范围

原 FaceTargetService 遇到 SlotUnavailable 会保留既有结果和原 TTL，但本轮结束后仍等待原 200ms 间隔。多次准入拒绝可能造成旧结果过期；此前稀疏健康快照不足以证实每次过期的完整因果链。本候选仅缩短“纯 DPU 准入拒绝后等待下一次尝试”的路径，不声称解决 VART 墙钟长尾或 USB 音频故障。

准确起点见 baseline-manifest.json。face_targets.py 为 d03e2aee…（迁移后版本），dpu_yunet.py 为 7ff2b247…；runtime/schedule/metrics/thread observer 使用已冻结的 14 源候选。candidate 的六份文件中仅 face_targets.py、dpu_yunet.py、dpu_vision_runtime.py 有改动，另三份逐字节保持。

## 行为

- `FaceTargetService(..., slot_retry=False)` 默认维持单次处理及原工作线程节拍，无环境变量或生产调用方自动启用；只接受显式 bool。
- 只有 **exact type SlotAdmissionDenied** 允许重试：原 scheduler 启用中的 YuNet 工作被原门槛拒绝。普通 SlotUnavailable、取消、已禁用、native 异常和非零 VART status 均不进入重试。
- 首次准入拒绝后，至少退让 25ms；每轮最多追加两次尝试，即最多三次 CPU 准备。每次从单元素 pending 取较新 frame id、非倒退时间戳且未过 TTL 的最新包，不复制或排队旧图像。
- 绝对截止为首次被拒准入尝试开始时刻 + 200ms。该时刻取在 `schedule.optional` 入口前，是保守上界依据，**不是精确的 scheduler 决策时间**；拒绝诊断开销不能推迟截止。
- 没有新帧时通过 Condition.wait 等到唤醒或截止，释放相机共享锁；所有退让等待都在 DPU 时隙外。重试使用本轮截止，下一轮重新开始。
- CPU 准备之前、编码之后、实际 native 提交之前，检查 closed、源 TTL 和已有的本轮截止。最后检查位于 execute_start 诊断之后，紧邻 execute_async。已持有 DPU 时隙时，state.lock 使用 `acquire(False)`，取不到锁即撤回，退出时隙后再记账；不等待相机锁，也不把这种撤回当准入拒绝。
- 200ms 是**继续开始 CPU 准备/申请准入/native 提交的截止**，不是函数返回墙钟上限。CPU/native 操作不能被该 Python 截止中断；它们可能在截止后结束，统计会记录 maximum_deadline_overrun_ms。TTL/closed 在发布前继续按原规则检查。
- 成功、无脸、其他错误后的原 200ms 节拍保持；原 30ms 占用硬限、5ms guard、YOLO 优先和超限后 CPU 回退保持。未改变 scheduler。

最后一次非阻塞检查只能判断当时状态；不能保证检查后线程绝不被抢占，也不能撤销已经开始的 native 调用。因此本候选不能提供硬实时保证。

## 数字证据解释

`retry_health()` 返回固定字段数字/布尔计数，无图像、身份向量或数据库：rounds/retries/denied/exhausted、deadline/closed/expired/disabled/busy，以及本轮最大墙钟和超过截止的最大墙钟。该读接口尚未接入生产 health。

**scheduler.calls 是已准入时隙结束数，包含 native 前撤回，不可当 native 完成数。** 由于检查按要求放在 execute_start 诊断之后，撤回也可能留下现有 diagnostics 的 native_attempts=1/native_failed=1；这不能单独当硬件或 VART 失败。完成吞吐使用原 diagnostics 的 `native_completed`（status 0）差值，并结合取消计数、错误和真实发布数解释。测试直接验证了“calls=1、execute_async=0、native_completed=0”的撤回。

## 软件验证与复现

```bash
python3 -B /home/ghmd/aura-yunet-retry-offline-20261022/run_tests.py
python3 -B /home/ghmd/aura-yunet-retry-offline-20261022/run_tests.py --regression
python3 -B /home/ghmd/aura-yunet-retry-offline-20261022/verify_candidate.py
```

使用本机已有 Vitis AI CPU 容器和 numpy，network=none、无设备、只读源码挂载。测试只用合成整数帧/数组、fake native runner、虚拟时钟及少量本地同步线程，没有创建模型 runner 或读取真实数据。

专项 37 项覆盖 default 行为对照、latest/TTL、最大次数、无新帧、关闭、新轮、准备/编码/诊断开销跨截止、绝对边界、真实 Condition 解锁、另一线程争锁时的非阻塞撤回、失败/禁用不重试、30ms/5ms、YOLO 优先、完成与准入计数区别和 SFace 原 API。相关冻结 identity 与 timing 回归分别为 67 和 66 项；最终结果以 test-results.txt、regression-results.txt 为准。

回归运行器会临时组合冻结 14 源和本候选六文件（候选覆盖），再只读挂载；临时目录退出清理。首次回归因测试原有硬编码路径选中旧 ui_camera_service 而出现两项夹具错误，第二次只读子挂载缺少目标文件被 Docker 拒绝；均未执行板端工作。现已修正临时完整 overlay，失败日志在私有工作目录保留，不算通过证据。

## 主任务接入点与板端验收

1. 独立审查 candidate-manifest.json、三个差异及测试日志；从新 boot 的实际活动源另做 SHA 对照，不能直接复用旧 boot/PID helper。
2. 生产构造位于迁移后 `board/identity/camera_faces.py` 创建 FaceTargetService 的位置。仅在隔离实验副本显式传 `slot_retry=True`；正式 source/config 不在本候选中改动。若同时接入独立时效统计，需在隔离副本合并 face_targets.py 并重新测试，两个候选同改该文件，不能直接互相覆盖。
3. 先完成板端无设备软件/开销前置，再跑只改变此重试策略的双模型 120 秒；GIL/亲和性不混入。前后检查 YOLO、有效发布、TTL/拒绝链、native_completed、CPU、30ms/5ms、USB、源码及回退。无需真人身份登记。
4. 若阶段目标通过，再按 10/30 分钟逐级延长；每次有独立回退保护，故障即恢复原版。之后才评估与已测 1ms 组合及 SFace 三模型。

没有相同输入的实板对照，没有实测板端额外 CPU 开销，没有长期稳定性数据，也没有生产开关常驻；不能将此离线通过称为 DPU 加速收益、过期修复或整机验收通过。
