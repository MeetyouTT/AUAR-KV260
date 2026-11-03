# 卡顿后转轴大幅往返：隔离与末脉冲复现

## 用户反馈和实际处置

用户确认“现在的位置就是中位”，并反馈点左右时系统卡住、转轴大幅来回。本轮立即停止继续点动验证，不再以细调小或正常ACK解释本次异常。

UTC11:52首次API读/STOP均URLError：界面处于activating，入口已变为aura-render24-rgb565-20261020/887c4b6b2b5d/startup/launcher.py，实际GTK253345。此部署不是本轮发起，已向用户询问是否另有更新会话，尚未答复。之后确认candidate/trial=COMMITTED；新启动config.runtime/实际argv指向其隔离runtime/aura。WorkingDirectory仍指向旧voice-barge-in目录，最初按它读到的哈希不能代表新进程，已另按config/argv完整纠正：运动/GTK Python与前轮一致，渲染C++953d553e…及库201adac3…更新。没有据此宣称渲染更新必然导致大幅机械摆动。

UTC11:55找到唯一Native owner253350，对其SIGTERM，等待锁释放；随后通过完整审计common/runtime守卫，只STOP并读回1420µs、flags0/lease0/epoch42/ACK41/reference1440/target1420。未ARM/COMMIT。旧界面重启前epoch37～42完整history未回收；reference1440只是上一点动起始参考，不是机械中位。

UTC11:57部署临时互斥保护256477，仅flock持有同一/run/aura-vsrv.lock，不打开/dev/mem或PWM。后续独立非阻塞锁尝试确实被拒绝，保护进程PID/命令/boot/fd复核通过；不是删除锁文件来阻止进程。用户界面运动UNAVAILABLE/backend_pid=null为隔离后的预期状态，不建议按重新连接绕过。后续恢复须核对保护记录并结束该进程，不删除inode、不自动重放。

按用户确认记录当前中位姿态，关联最后1420µs读回，保存到板端aura-pan-incident-20261020/center_observation.json和共享交付。user_confirmed_center_pose=true、associated_command_us1420；electrical_waveform_verified=false、physical_angle_feedback=false、motion_release_authorized=false。确认姿态与电气/机构标定放行分开，不继续默认1500或上一reference1440。

最后只读GUI为IDLE/无error/序列继续，相机仍106060、12.49Hz采集/9.92Hz检测、无错误。本轮未重启GUI或相机、未恢复CPU优化、未修改正在运行的渲染/控制/固件；运动指令0，只有停止和隔离。

## 已复现的机制和证据边界

源平台14da0e60对应RTL SHA cc62cf5f71c2b76668417c0de49e95563d41a56f0d0fd702ac74fb465b7684f3，与当前共享RTL/源发布记录一致。ManualPan普通2秒点动结束走hardware.stop；RTL在STOP或expire时立即servo_pwm<=0。停止若恰在高电平，末脉冲会被截短，尽管width/target寄存器与ACK正常。

Vivado2022.2、100MHz/50Hz、BUILD_ID参数14da0e60的离线复现：1420µs目标在高电平500µs处STOP，末脉冲500.02µs；许可1ms到期末脉冲1000µs；低电平STOP保持完整1420µs。补真实100ms租约、第21ms附近续期后到期，也出现末1000µs脉冲（此前已逐帧到1440）。所有下降沿均监视，没有跳过STOP/expire。日志与四场景testbench冻结保存。

旧HDL测试的下降沿脉宽检查含dut.active条件，STOP/expire令active=0，掩盖了末脉冲。此前ACK/软件测试通过不覆盖这种引脚波形。这是已证实的数字机制及测试缺口；尚未测实板J2.3输出和舵机反应，不能把仿真数值称现场测量。异常短脉冲可能被位置舵机解释为另一位置，后续正常脉冲又拉回，是对现场大摆的有依据解释，仍待电气实测与供电/断信号行为核对。

另外，activated和IPC请求在GTK处理事件时生成issued，没核对原始GDK触摸时间，存在卡顿后的旧触摸被当新意图风险；本次未取得重启前触摸/动作完整时间线，未声称重放已发生。新渲染版本的启动与用户卡顿时序也尚未对齐。

## 离线候选与验证

在私有pan-incident/candidate-v2和新共享交付里制作隔离VSRV/2候选，没有覆盖生产源码。BUILD_ID故意为0，不是发布固件，旧Native仍ABI1/build14da0e60，未被改。

新增QUIESCE正常完成：高电平等完整脉冲结束，低电平不多发一帧，再撤销所有许可。按ceil(MAX_US/MILLIS_US)+1保留完整脉冲的租约下界（当前3ms）；过短许可拒绝，每个新帧先检查余量，100ms长度不变，到期前不再启新脉冲。原STOP仍立即关断，紧急截短仍可能发生，不能借此宣称所有断信号机械行为已安全，外部使能/断能及实际舵机仍需验证。

五个新增仿真全部通过：QUIESCE高电平完整1420µs、短租约零输出、真实100ms到期末完整1440µs、QUIESCE低电平无多发、紧急STOP仍立即关断。原协议/AXI顺序/背压/权限/范围/斜坡/复位测试台、原100MHz正常波形测试台也通过。没有重跑无关Python全仓测试，未把此前347项当作本轮硬件修复验收。

尚需Native ABI/命令白名单与正常结束调用适配、过期触摸丢弃、实现/时序/联合DPU兼容检查、断开舵机后的外部波形和实体复验，不能直接部署该候选或解开保护。已询问现场是否有示波器/逻辑分析仪，未答复不能当作具备仪器或允许试转。

## 交付

见[本轮完整证据与候选](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_pan_stall_waveform/README.md)。过滤接口、STOP/互斥/实际runtime、中位关联、旧RTL四场景、新候选及七项HDL场景/测试台保存；没有相机照片、身份库、权重、原始UART。Windows回执不改，旧冻结工件保留。共享入口/Ubuntu回执和导航更新为“隔离中，离线候选通过，未实板放行”。

交付完整性核验通过：新包20个内容文件写入verification.json（清单本身不自校验），5轮UART源/返回体SHA与过滤JSON一致，13份仿真/中位副本与私有原件一致，5个README链接存在；原六份交付共138个冻结内容文件长度/SHA保持。候选两个旧测试台编译所用RTL与候选源码一致，四份仿真日志标记通过且无ERROR/FATAL。此核验只确认本机工件，不表示Windows同步已确认，也不代替外部波形或实体验收。
