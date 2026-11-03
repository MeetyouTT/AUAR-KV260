# GitHub参考与转轴低延迟闭环修复（当前 r10）

UTC2026-10-26 05:12 更新。用户要求参考GitHub尽快实现只跟人脸、平滑且响应快；期间反馈“方向反了”，修正后明确“方向正确，但是起转晚、延迟高、转动顿挫”。此反馈作为r8实体验收仍不通过保留。当前已运行continuous-v10r10/source-v12；方向沿用已确认的+1，r10平顺与起步快慢尚无有效真人复测，不能称完整解决。

## 已落实的改动

1. **移除控制循环中的大报告阻塞。** 原runner每0.5秒同步json.dump(indent=2)，运行报告会增长到211026 bytes/512条观测。板上只读、独立进程、相同报告序列化三次为123.220/154.575/245.425ms（输出StringIO，不含写盘），该数值不是直接采到原控制线程的耗时，但原代码确实在运动线程同步执行同一格式化路径。r8/r10运行时只写最近8条命令/事件/观测，使用紧凑编码单次写入；完整有界512/128条轨迹在已执行STOP后保存。计数、fault与readback不裁掉。
2. **固定已确认方向。** r8原自动polarity=-1，用户指出反向后先GUI STOP并取得flags0/lease0，再将自动映射改+1，手动按钮方向-1保持。用户随后确认方向正确，该真实反馈已记录到direction-calibration.json。此前-1由镜像映射推导不再作为当前自动方向。没有自动回中1420，没有伪造轴角校准。
3. **提前准备但区内不输出PWM。** r10在已确认单脸后建立ARM，区内持续接收真实源但不COMMIT；越线时可直接推进有限轨迹。仍需ARM后真实新图，旧图/换脸/丢脸/错boot仍拒绝或STOP。新增pwm_output_started供证据区分“准备”和“驱动”；因此区内可能ARM，但不能把ARM次数当实体转动次数。PL源码确认ARM不令active置位，未修改PL；此新增策略的真人正例尚待当前复测。
4. **恢复实测脸速反馈。** 现役上限10→20µs/s，velocity_gain 0→12；持续向外增加速度，回区前按实测图像回移速度提前减速。OneEuro和Ruckig沿用，未再叠加固定低通。每新图4µs、加速度100µs/s²、jerk800µs/s³、软件范围1400..1600、图像250ms/实检测锚500ms/提交20ms余量及10秒运动段保持。区内按原规则立即冻结目标；故障/源失效仍STOP，不能宣传这些强制停止也符合普通轨迹的jerk约束。

## 实际验证与边界

- r8修日志前的r7现场25.472s：12ACK/10目标变化/41ARM，采样1448..1451µs，用户看不到明显动作；验收失败保留。
- r8首个4.089s窗口：发布最大5.936ms、控制回合6.352ms、>100ms回合0。完整162.668s（方向尚错误）：258ACK/125目标变化/72段、1453..1522，发布最大29.655ms、控制回合78.696ms、>100ms0。只证明真实命令与调度，不证明方向/跟随通过。
- 改+1后25.126s：24ACK/12目标变化/6段，采样1500..1512、fatal=false；用户确认方向正确，同时明确迟缓/顿挫未解决。不同真人输入，不能将其与前一窗口当作严格A/B收益。
- r10含预备与脸速反馈的69项主机回归通过；同一合成输入周期80ms、首次有效指令260→200ms，是FakeDevice软件结果，不是摄像头或机械延迟。覆盖区内无COMMIT/无位置变化、预备取消、ARM后真实源、两种方向、4µs步长、旧源不续授权、行程/丢脸/故障停止、动态速度与回区保持。
- 18运行源码pins及258GUI pins通过。camera189651/GUI137253保持，本轮不重启视频/身份、不切固件、不清故障或预算；新boot16a…，primary累计4/可选0、0保留，identity ready不代表本轮身份准确率验收。
- r10首18.350s：publish最大8.430ms、控制回合9.971ms、无>100ms回合、0ARM/ACK。25.106s观察也全为UNCONFIRMED，0命令/位移，1511µs保持。126.683s快照仍0ARM/ACK、3934未确认，发布最大20.356ms、控制回合21.085ms、>100ms0。私有X11预览确认取景没有可见人脸；不是用无脸窗口宣称随动通过。当前保持运行，需人脸重新入画后测试。

## 本轮GitHub原件核查

通过用户指定的GitHub插件只读读取README/实际代码，未创建Issue/PR或更改远端代码：

- [Ruckig速度接口](https://github.com/pantor/ruckig/blob/main/examples/05_velocity.cpp)：连续传递前次运动状态；用现有本地速度接口，不依赖Pro跟踪或云waypoints。
- [OneEuroFilter实现](https://github.com/casiez/OneEuroFilter/blob/main/cpp/OneEuroFilter.cpp)：使用真实时间戳和速度自适应截止频率，现代码已采用；本轮没有把它当尚未开发而重复引入。
- [pantilt-face控制循环](https://github.com/MikeWorden/pantilt-face/blob/main/src/pantilt_face/control/tracker.py)与[README](https://github.com/MikeWorden/pantilt-face)：参考短控制路径、测量时序、命令累积与阈值关系；上游明确增益尚未实物调准，不照搬其参数或声称其时延已在本机达到。
- [Pimoroni厂商跟随示例](https://github.com/pimoroni/PanTiltFacetracker/blob/master/facetracker_haar.py)：只参考脸位置误差闭环；逐帧角度增量和原硬件限制不直接移植。
- [ServoEasing](https://github.com/ArminJo/ServoEasing)：区分点到点缓动和连续输入；不替换KV260驱动，不套用其他舵机的死区数值。

原件路径/blob指纹见[GITHUB_SOURCE_METADATA.json](GITHUB_SOURCE_METADATA.json)。首次厂商文件名facetracker.py查询404后按仓库目录读取实际facetracker_haar.py，未据不存在文件作结论。

## 复现与交接

[当前代码](continuous_v10r10/)、[32文件指纹/69项独立软件复验](OFFLINE_VERIFICATION.json)、[板端过滤证据](BOARD_VERIFICATION.json)、[报告格式化成本](BOARD_REPORT_SERIALIZATION.json)、[预备合成时序](PREARM_SOFTWARE_TIMING.json)。共享快照首次复验缺主机轨迹.so，补齐host专用依赖与独立driver后通过；patch工具同文件删除/新增的请求被拒后已按分步方式修正，仅影响本机辅助验证脚本，不涉及板端控制源。

Linux x86_64离线复验：`python3 continuous_v10r10/verify_offline.py --output result.json`（新输出文件）。29个候选文件＋3个依赖指纹；非Windows/ARM硬件测试。r9只是未激活的中间候选，当前为r10 manifest770cf34a6db0c64a8efd8faadd5b21455aab791e03e98ecf0d4c301651ad133f；r8已留STOP报告。相机源仍v12，用户边界左脸框10%绿线/右脸中心80.647%橙线不变。

当前未完成：r10真人越线/回区/换向的起步与平顺验收，以及有效脸源间断的现场对照。无可见人脸时不输出动作。未共享原图、身份库、录音、大模型或原始UART；Windows接收/运行/实体验收回执未代填。
