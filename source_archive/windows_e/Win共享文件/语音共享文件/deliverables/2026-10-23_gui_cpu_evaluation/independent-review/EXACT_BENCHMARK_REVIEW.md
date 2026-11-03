# 新exact分发与基准独立检查

范围：只在本机审查`compare_exact.py`、`build_exact_helper.py`及四源候选，修改tests和本目录；未接板、未改业务源、未开音频/模型或生产服务。

最终结论见`FINAL_GATE.md`：**Python分发18项离线检查通过；新FMA的native及画质已通过本轮case，但CPU仅降5.464338%，未达10%门槛，不部署。** 下文按审查发生时点保留发现和修订；原11项fake测试针对旧两源候选，不能直接作为新四源的验收结果。

## 新Python边界修复与验证

发现并反馈`blend_exact`端点输入已有legacy lazy proxy时原地打exact flag的问题。父任务已改为仅`proxy is not a and proxy is not b`才打flag，使端点保留原代理语义。

本子任务更新`tests/test_gui_cpu_review.py`的FakeNative/FakeBody以调用和记录blend_exact，并增加7项对**实际候选NativePixels方法**的测试（`__new__`实例＋假C ABI、内存合成图）：新exact wrapper/路由、普通blend继续旧API、materialize去除flag并走plain pose、plain与已有legacy proxy端点不污染、nested materialize、真实BlinkLayer.apply先材料化再plain pose。旧11项也更新exact断言后重跑。18项全部通过，0.017秒，日志`exact-behavior-tests.log`。

执行环境：现有`xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106` Docker、`--network none --read-only`、工作区和共享源码只读挂载；解释器`/opt/vitis_ai/conda/envs/vitis-ai-pytorch/bin/python`。首次误用容器system python，缺PIL，失败日志另存`exact-behavior-tests-system-python-missing-pil.log`；改用已有conda解释器后完整通过，没有安装依赖或联网。

假C ABI仅验证Python选择/标记/生命周期与画面操作契约，不证明ARM混合公式一致、线程安全、实际像素质量或CPU收益。

## 新基准检查

- 一个core，baseline/candidate各自独立body player和native output/cache；MouthBank/BlinkLayer共享读取。在本轮时间<3600秒时，BlinkSchedule.phase不扩展starts；MouthBank.image复制图后操作，未发现共享状态污染。
- baseline完整回放一段再reset candidate完整回放同段，不再逐帧交替推进共享core；core、body和facials瞬态重置、seed一致。metadata比较新增body matrix、display state和transitioning。新增effects-off、speaking退出和7.9秒说话池轮换，比原静态方案完整。
- ABBA/process CPU口径保持；`NativePixels.cpu_times`不被当成整进程CPU。限额CPUQuota=75%会改变wall分布，headless结果不能当整机提升；正式YuNet处于不同恢复/降级阶段时更不能横向宣称整机收益。
- 源pin覆盖8份Python、cpp/lib/demo/preview；候选3份Python和cpp也带hash。完整素材文件未逐个hash，但现有Blink初始化核验anchor/layer，reuse初始化也有其检查。发布前仍须完整运行清单和GUI回退。
- native_check先做旧lib材料化＋pose对新exact导出的直接像素比较，并检查新库legacy导出对旧库不变，失败则不构造core。这一快速失败顺序正确。
- 已反馈并修正覆盖口径：原B的(a=x+y,b=7x+3y)变换det=-4，在mod256只有16384个独立对；父任务已将第二式改7x+2y(det=-5)，使每个RGB lane全覆盖65536对。门槛未变，新覆盖等待下一轮实际执行。

## 浮点收缩边界

父任务反馈新库ARM编译成功但opaque256×256/alpha=.6仍有max1、1070 RGB通道差异，基准已在core初始化前失败；本子任务未独立接板复核该运行。

本机另用libm.fmaf和显式float32中间舍入构造`fp-contraction-counterexamples.json`：a=5,b=0,t_float32=.6000000238418579时，分别乘加结果2.0、FMA结果1.9999998807907104；截断分别2和1。父任务随后反馈实际板端a5b0为参考1/候选2，a10b0为参考3/候选4，且objdump显示`vmlaq_n_f32`编为独立fmul+fadd；这与旧参考使用FMA、新候选分开运算的方向吻合。本子任务未直接读取板端二进制。

父任务据此仅将新`blend8_exact`两处vmlaq改为`vfmaq_n_f32`明确请求FMA，旧分支不变；本子任务已更新`native_pixels.cpp.patch`和manifest到该修订。**新的FMA候选仍须下一轮ARM像素自检后才能称一致**；18项Python测试不覆盖该C++数值变化。

所有测试对象与报告hash见`exact-review-manifest.json`。通过Python离线测试不解除native、质量或CPU门槛，也不说明YuNet罕见长尾已消除。
