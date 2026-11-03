本目录只包含位置感知滤波数学和合成回放，不连接相机、模型、UART、板卡、生产服务或执行器。没有修改v5/v6。共享调研文档核查的是较早v2r2；当前v5正常区内zone_holding已经保留ARM，只在真实expiry/丢目标等情况下重建，不能沿用旧状态诊断。

接口：

```python
from one_euro import OneEuroFilter
position = OneEuroFilter(min_cutoff_hz=1., beta=6., derivative_cutoff_hz=1.)
filtered_ratio = position.filter(measured_ratio, actual_source_mono_ms/1000.)
# position.derivative_ratio_s: image residual ratio/s, not human angular velocity
# position.cutoff_hz: current adaptive cutoff
```

首次样本直接初始化；其后使用真实source dt。重复/倒退/非有限时间拒绝且不修改历史。新目标/过期后由调用方reset，普通同目标区内保持不得把滤波历史每次清空。此类不创建帧号/时间戳，不做执行许可或lease管理；调用方仍须执行原始新源/250ms/丢脸停合同。

公式核对作者 [pinned C++](https://github.com/casiez/OneEuroFilter/blob/d78925584245597f2aa9c4c01a802eb0f0b77fb9/cpp/OneEuroFilter.cpp)：2023修订后的导数使用当前值减上一filtered值，再按真实dt计算；导数低通截止1Hz，位置截止为min_cutoff+beta*abs(filtered_derivative)。这是替换现有位置中值+80ms低通的候选，不再串三点因果中值或另一层固定位置EMA。源单位是image-width ratio，beta=6的单位为1/ratio；若改用pixel，等价beta需除以图像宽度640，不能照搬原数值。参数是离线起点，尚未实机调优。[作者调参说明](https://gery.casiez.net/1euro/)建议先固定beta=0处理慢速抖动，再增加beta降低快速滞后。

AB.json使用同55/80/120/65/80ms实际间隔，基线直接导入当前v5 FaceEdgeController，读取其filtered_center_ratio；只比较感知输出，未将控制器状态/命令结果混作硬件收益。11项数学检查通过。离线结果：静止噪声std从0.659px到0.604px，0.5ratio/s快移均值位置滤波滞后从132.4ms到31.7ms。慢移滞后仍约116.6ms，不能宣传所有速度均零滞后。

必须保留单点离群门控：裸OneEuro不是坏框拒绝器，单帧+0.25ratio反例仍通过约0.1963ratio。建议独立门控只对同时超过0.08ratio且超过1.5ratio/s的跳变暂缓一个新源；下一实际新帧回到旧位置则丢弃候选，下一帧同向推进或贴近候选则只接受当前真样本。普通0.5..1ratio/s单调快移直接放行，禁止按固定每帧距离限制所有快速运动。阈值只是可测候选，实际可见脸尺度/相机自身运动需现场验证。

因果限制：无法在没有额外质量证据时，同时零等待地确认任意突变是真快移并保证去除任意单帧尖峰。对超过门槛的真实突变需要一帧确认；暂缓期间不得把旧坐标换成新时间戳、不得补帧、不得续旧lease。如果因此跨过实际硬件期限，仍按expiry停止。

复验：`python3 -m unittest discover -s . -p 'test_*.py' -v` 和 `python3 replay_ab.py`。测试与JSON均是纯软件证据，不代表边界起步、PWM、机械顿挫或真人体验已经通过。
