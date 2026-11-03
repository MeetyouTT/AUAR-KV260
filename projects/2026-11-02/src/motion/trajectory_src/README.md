这是纯本地Ruckig一轴Velocity接口数学候选，无UART、相机、执行器、生产服务或平台寄存器访问。

部署候选仅使用 `libaura_trajectory_compat.so`：AArch64，136296字节，SHA256 `d08abd38232b6b7040b84befdd45c925a53885774ece339bdc1bf21f5adedd7a`。此前static候选依赖新glibc、初版dynamic候选依赖GLIBCXX_3.4.29，均保留作检查记录，不作为本次部署候选。

上游来自 [pantor/ruckig](https://github.com/pantor/ruckig/tree/99751e6ebc7c963bb80e99fbbe66f2c279d1db57)，commit `99751e6ebc7c963bb80e99fbbe66f2c279d1db57`，源码未修改，MIT许可随包见 LICENSE.Ruckig。使用[开源Velocity例子](https://github.com/pantor/ruckig/blob/99751e6ebc7c963bb80e99fbbe66f2c279d1db57/examples/05_velocity.cpp)的ControlInterface::Velocity，无Pro Tracking、云端waypoints或cloud_client编译，不依赖Python包装或Eigen。

接口按主进程约定：

```c
int aura_trajectory_step(double dt,const double current_pva[3],double target_velocity,
                         double max_velocity,double max_acceleration,double max_jerk,
                         double output_pva[3]);
```

dt为真实轨迹步长秒，范围0<dt<=0.1；p/v/a单位为us、us/s、us/s²，jerk单位us/s³。返回0表示Working或Finished的有效输出；非0是errno样式失败，output保持原样。每次传入上次输出的命令p/v/a，不能每次把v/a清零。内部每次用同一官方求解器从该连续状态重新求解，无隐藏跨会话状态或I/O。导出C ABI不抛C++异常。

Velocity模式上游不校验max_velocity；wrapper额外验证当前/目标/输出速度、加速度，并拒绝即使立刻以最大jerk消去加速度也必将超速的初态。Ruckig限制的是连续数学命令轨迹；整数微秒舍入、PL PWM、真实机构与无编码器误差并不由本库证明。position是命令状态，不是实际角度或实测舵机位置。

必须由主进程执行源授权、旧帧/新源/丢脸、绝对期限、硬件lease、行程限位、独占owner和STOP。此库不能创建新source或延长deadline。20ms控制tick只能消费原新鲜源授权的有限轨迹段，不能被当成新图像。开源Velocity接口不提供本机绝对位置行程保护；接近行程端点须外层提前规划/拒绝。硬STOP、用户要求的回区立即freeze以及越界强制冻结会中断数学jerk连续性，须明确作为例外，不能宣传这些瞬间也满足同一平滑保证。

兼容库动态依赖libstdc++、libgcc_s、libm、libc；导入版本实际仅GLIBC_2.17、GLIBCXX最高3.4.19、CXXABI最高1.3.9。compat_runtime.cpp仅把GCC11新增的allocator辅助函数hidden本地实现，保持同样bad_array_new_length异常类型，以免工具链头强制GLIBCXX_3.4.29；不替换轨迹计算。

`python3 build.py`直接编译11个开源核心源，显式不编译cloud_client.cpp、不定义WITH_CLOUD_CLIENT，无CMake默认联网选项。host测试命令：

```sh
AURA_TRAJECTORY_HOST_LIB=libaura_trajectory_compat_host.so /home/ghmd/kv260-adaptation-check-20261006/identity/.venv/bin/python -m unittest discover -s . -p 'test_trajectory.py' -v
```

10项host C ABI检查通过，包含解析jerk起步、跨调用加速度承接、反转/减速到0、可变dt、1000次改目标及非法输入输出不变。HOST_BENCHMARK.json为10000次host调用结果，不能作为板端时延。目标板仅完成交叉编译和ELF依赖核查，未实际加载/运行，机械效果待主进程统一验收。
