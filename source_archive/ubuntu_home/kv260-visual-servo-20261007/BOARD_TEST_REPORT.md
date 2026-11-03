# VSRV 带电受控板测：2026-10-08

用户明确要求“直接测试把，我有断电保护”，随后要求“继续”。本轮据此执行带电、有限时长板测，不再要求断开舵机动力。用户所述断电保护仅记录为现场报告，没有验证其电路。没有开启视觉自动随动。

板卡 boot ID `f7a3ff07-fc20-4804-af12-c314a7a1847a`，备用卡 CID 与历史记录一致。候选 `aura-visual-servo-b4096-v1` 已实际加载到 slot 0，ID `0x56535256`、ABI 1、BUILD `0x14da0e60` 通过真实寄存器访问核对；地址 `0x80080000`，源设计输出 J2.3/E10。

| 实际检查 | 结果 |
| --- | --- |
| 当前启动基础设备树和源候选的基础树哈希 | 一致；新固件四个文件传输/安装哈希均通过 |
| 加载初态 | flags=0、lease=0，没有自动 ARM 或输出许可 |
| 错误固件访问、第二写方 | native 拒绝官方镜像；第二持有者被锁拒绝，errno=11 |
| 未 ARM 提交、重复序号 | 拒绝，接受序号不前进 |
| 120 ms 许可停止续约 | 回读约 120.073 ms 后到期；bound/reference/armed/active 全清；旧提交不能重新启用 |
| 目标和有效脉宽 | 1504/1496 µs 接受，90 ms 后有效脉宽回读正确 |
| 显式 STOP | 确认约 2.970 ms，许可及输出使能全清 |
| 有限往返 | 4.003 s，1500→1480→1520→1500 µs，92 次提交全部接受，结束 STOP |
| 提交到接受回读 | 本次 92 次中位数 3.281 ms、最大 3.944 ms；是该样本耗时，不是最坏时延保证 |
| DPU | 实际查询 B4096/300 MHz/fingerprint `0x101000056010407`；ResNet18 固定图 Top5 与基线一致 |
| 同配置并行 | 第二次推理成功结束时 PWM active=true、lease=149 ms；USB 采集/检测/显示计数持续增长 |
| 最终状态 | PWM 停止、未 ARM、lease=0；PID 1498 独占摄像头、Monitor On；ZOCL 引用回到 0 |

实际 PL 参考时钟读数为 99,999,999 Hz。源电路的控制域为 100 MHz、分频 100、周期 20,000 µs；本轮没有示波器实测引脚周期、脉宽和电压，不能把寄存器回读当成外部波形验收。舵机机械运动也仍待现场反馈；指令接受不等于物理到位。

第一次共存检查里 400 ms PWM 先于分类程序结束而到期，只证明程序存活阶段重叠。因此又执行了 4 秒有限测试，得到推理完成时 PWM 仍有效的直接记录。每次许可为 150 ms，约 40 ms 间隔续约；程序有 4 秒截止和 finally STOP，没有常驻运动任务。

新增 `native/vsrv_mmio.c` 与 `vsrv_transport.py`：AArch64 `volatile uint32_t`、实际反汇编 `ldr w0` / `str w1`、`dsb sy` 屏障、固定地址/寄存器白名单、boot/CID/固件/BUILD 校验、合作进程排他锁。0x24 命令寄存器不可读，非法地址在进入 MMIO 前拒绝。释放 transport 也确认 STOP；身份不匹配时不向未知配置写入。该锁约束使用本 transport 的合作进程，不能阻止任意 root 程序绕过它。

新增板测程序 `board/common.py`、`install.py`、`load.py`、`bench.py`、`coexist.py`，以及 adaptation-check 下的 `scripts/vsrv_*.py` 启动、并行和收尾程序。新增 `tests/test_transport.py`，`scripts/check_host.py` 纳入 transport；38 项主机单元测试和 Python 编译通过。原运动 RTL、视觉算法、原 FPGA 工程未修改。

收尾初次误把 `/etc/vart.conf` 不变作为通过条件，检查失败，原证据保留。实际内容正确指向候选 XCLBIN；本机 DFX 管理器 `update_env()` 在加载 XRT_FLAT 时自动更新该文件。修正为核对与活动镜像配套后收尾通过，没有手工恢复成错误的旧指向。原官方固件四个文件哈希不变。

内核本次加载仍出现 overlay 移除时可能泄漏属性的警告，XRT 有可选 AIE_RESOURCES section `-22` 提示；日志完整保留。这不是无告警正式发布。源实现仍有外部时序约束缺项和此前 DPU 参考优化告警。短板测不代替长测、故障覆盖、正式交付或完整视觉闭环。

当前机械基准脉宽、极性、蓝线 x=320 左/中/右实测映射仍未知。测试中的 1500 µs 只是台架测试点，不改成用户当前位置的标定值。`CALIBRATION_PENDING.json` 保持 confirmed=false；未启动 `realtime_visual_servo.py` 物理随动。下一步根据现场动作/示波器结果确认极性和机械参考，再记录蓝线映射。

完整阶段证据与最终状态索引见 [CURRENT_BOARD_TEST.json](CURRENT_BOARD_TEST.json)。原始命令源码、输出哈希和串口记录在 adaptation-check 的对应 evidence 目录，主机汇总证据另存，不覆盖失败尝试。
