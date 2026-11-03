# GUI CPU 同输入基准独立复核

审查范围：本机源码、已回收JSON、现役源码哈希；未访问UART/板卡、未启停服务/音频/模型、未改共享入口。本子任务仅新增离线检查与隔离的C++候选。

结论：**首版lazy IDLE候选不能部署。** `compare-v2-safety.json`的完整IDLE48帧分段报告为max=2、p99=1、最差帧mean=0.2172709968；预声明mean≤0.1失败，6帧有差、4帧眨眼。SPEAKING_NEUTRAL16帧逐字节一致。总基准未完成，不能宣称CPU收益已通过。门槛应保持。

## 测量方案有效项与限制

- `time.process_time()`计入当前进程各native工作线程CPU，优于仅调用线程CPU；不等于整板CPU占用率。固定8Hz虚拟时间序列不能冒充实际UI吞吐。
- 核心与身体播放器均reset并重新设置同seed；两独立core的逐帧交替不会推进对方时间线。BlinkSchedule固定seed，在本轮t<3600时不扩展/修改随机序列，未发现静态同输入计时错误。
- ABBA顺序、4帧warmup后计48帧、相同native threads=3基本可用。CPU门槛≥10%与像素max≤2/p99≤1/mean≤0.1应保持。每轮末图hash只是弱核对，最终建议记录全部采样meta/hash摘要。
- v2直方图的searchsorted(side=right)对0基rank正确，插值得到与默认线性percentile相同的p99；不是近似抽样。离线标准库模型覆盖稀疏/重复/极值/随机样本。
- 静态状态每段reset，尚未覆盖说话退出→IDLE、6秒池轮换与真实native的idle_gain=0。当前质量不通过已经足以拒绝，无需为失败候选继续完整性能轮。
- staged helper实际仅pin了两个Python改动源；相机unit SHA并不证明所有导入的GUI/native/素材相同。`native-source-proof.json`补充了现役cpp/lib/demo/preview哈希；后续基准应固定完整依赖清单。
- v2进度直接定位两次core初始化耗时28.125s/30.013s；facials各约1.65s，不应将首轮85秒超时归因到像素统计。新基准可共享一个core和只读mouth/eye资产，保留两个独立body player；质量按变体完整顺序回放，禁止共享core时逐帧交替直接推进。

## 实际执行的离线验证

- `tests/test_benchmark_review.py`：3项通过，日志`benchmark-review-tests.log`，验证精确p99公式、v2 payload/script/candidate字节一致、预声明门槛和ABBA/process CPU计量存在。该测试记录针对v2当时的2源payload，后续Python候选变化不自动继承此结果。
- `blend_formula_counterexample.cpp`：在本机g++ -O2编译执行，结果`blend-formula-counterexample.json`。786432个通道/比例组合中float与Q16模型有70234个差异，最大1。此为主机公式反例，不是ARM NEON实测。
- `tests/test_cpp_candidate_review.py`：3项通过，日志`cpp-source-review-tests.log`，证明旧pixel/video函数源码保持、新旧entry分配不同flag、去除新增分支后的实现主体与旧函数逐字符相同。

## 融合混合的具体偏差与最小候选

现役读回`native_pixels.cpp` SHA为`953d553e57ee42589caaae9c720ff4f57b1734d81e6648990f9784d299ffc798`，与10月20日`active_baseline`相同。现役`aura_blend`采用float32 `uint8(a+t*(b-a))`，融合NEON `blend8`却采用Q16 `floor((a*(65536-W)+b*W)/65536)`，W=round(t*65536)、上限65535。两者不等价：a=9、b=4、t=.6f时分别6与5。数值偏差可以经过背景、affine、resize传播，不能按“只有1级灰度”绕过原门槛。

只在`candidate/aura/tools/native_pixels.cpp`新增`blend8_exact`和`aura_pose_blend_exact`，原`aura_pose_blend`转调internal helper(exact=false)，新entry为true；原`aura_pose`仍走旧entry。旧Q16 helper、flat8、scalar尾部、affine、resize、视频和`aura_blend`均保持源码。新增exact入口对other!=null时拒绝非有限或范围外blend。

候选SHA：`9d264a5a0fea1bafc0ce20dac55fe995cd0386792e25eff2e3d7fab377636ba4`；补丁`native_pixels.cpp.patch`（59行diff）。新NEON使用float32乘加并截断，避免Q16量化。**本子任务未编译该ARM库、未验证新入口逐像素一致或收益。** `vmlaq_n_f32`的FMLA/乘加收缩是否与现役编译器生成的`aura_blend`完全匹配，仍须同编译选项在ARM上用全部(a,b)及多种float比例和尾部尺寸验证；旧ABI像素也须与原lib实际对照。源码分支等价不等于已经完成二进制行为验收。

新的exact路径通过后，仍须按原画质/CPU门槛及状态边界复验，再考虑受控GUI试运行；不能将独立headless测试写成整机加速或YuNet长尾根因修复。

后续修订：以上`9d264a5a…`是首次vmlaq候选的历史状态，实际native自检未通过。父任务根据ARM小样/objdump将两处新exact乘加改为vfmaq；当前`native_pixels.cpp.patch`与manifest已更新到`91aad0be3f4b8bb81fc4826ca86b96ab1c6057f229b4483325764aca5bade2e2`。详情与18项Python分发检查见`EXACT_BENCHMARK_REVIEW.md`；新FMA版本仍待ARM数值/性能结论。
