v10 是独立的人脸源候选；本目录操作均为 Ubuntu 本机软件开发，没有访问 UART、板卡、生产服务或执行器。五个运行文件已经冻结，路径、字节数和 SHA256 见 `transfer-files.json`。板端入口为 `pan-face-edge-v5/face-source-v10/entry.py`。

本轮复现了 v9 的一类无谓 `UNCONFIRMED`：检测线程处理某张图后较晚公布 `count=0`，但 Flow 已经对同一张或更新的真实图完成固定人脸模板匹配。旧代码要求 Flow 的“当时看到的检测 snapshot frame”恰好等于最新 miss frame；因此即使新像素已经证明当前人脸存在，也会被挡到下一次 Flow 测量。两个确定性反例中，v9 返回 `UNCONFIRMED`，v10 返回 `READY`，输出仍沿用实际图像原始 frame_id/stamp/deadline。

v10 改为要求像素测量的 frame_id 和 stamp 两者都不早于该 miss 的真实源，另继续要求正确 continuity key、当前图像年龄小于250ms、实际单脸检测锚小于500ms、当前采集新鲜、相机/人脸服务健康。早于 miss 的图像、错误 key、多人、过期、坏纹理仍拒绝。不会把未测过的新图当测量，不替换旧图时间，不借用身体或检测器预测框。若 miss 图本身已被真实模板匹配，晚到的 miss 公布不会再使其凭空失效。

另一处改动减少确定无收益的计算：真实检测锚更新时，v9 总会用旧模板额外进行一次 NCC，只为决定是否保留旧 motion binding。如果旧 binding、旧 anchor key、新 detector key 三个字典完全相同，无论 NCC 成功或失败最终 key 都是同一字典。v10 仅在这三个 key 完全相同、旧 box/template 有效且旧实锚未过500ms时跳过这一次可选 NCC；随后仍用新检测源的真实脸 crop 重建固定模板，并对当前图像执行原来的 NCC（若当前就是检测锚同图，则直接采用已确认真脸框，与旧版一致）。key churn、旧 binding 失效或过期的情况不使用该捷径。诊断增加 `continuity_match_skips` 和 `continuity_match_calls`，便于实板确认收益。

30/30 本机回归通过，Python 3.8.10，0.070秒；四个运行文件编译通过。完整命令及边界见 `validation.json`。覆盖原23项、miss同图/更新图时序反例、两个时间维度都不能更旧、错误continuity/过期拒绝、当前NCC仍需执行、key churn仍需旧像素连续性验证、无效/过期binding不可跳过。冻结 v9、r4、v6 均未修改。

没有证据证明这两项就是全部59次ARM/分钟的原因。现役真实 detector miss/key churn、模板匹配失败、捕获/推理/线程调度长尾仍可能造成有效源断档。批量读热路径和控制状态重构也由主终端独立负责。v10 的板端时延、无谓拒绝实际频率、持续跟随与实体平滑度都尚未验证；不能将合成反例或少一次 NCC 调用称为机械修复通过。

锁顺序检查：现役 `state.lock` 与 `face.lock` 共用同一 RLock。observation 在获得该锁之后才取 now，因此外层锁等待本身不会用等待前时钟；读取 Flow 的短 condition 后再嵌套 face 锁不会等待另一个独立锁。worker 不持 Flow.condition 获取 face.lock，raw offer 在调用原检测 offer 前也已释放 condition。没有在本次有限静态审查中发现锁环。Flow.snapshot 与 diagnostics 分两次读取可能令诊断对应稍新一代，诊断不参与运动授权；本版未为此扩大改动。
