# 2026-10-08 VSRV 受控带电板测

用户授权“直接测试把，我有断电保护”，随后要求继续。已按带电有限测试执行；保护功能仅为用户报告，未验证。当前参考脉宽/方向/蓝线锚点仍未知，未启动视觉物理随动。

10:35 UTC 板卡只读预检：boot f7a3ff07-fc20-4804-af12-c314a7a1847a，基础 DT 与源候选一致；官方 B4096 活动、ZOCL 无客户；PID 1498 USB 预览正常。以串口传输 3,169,381 字节压缩固件，完整 SHA 校验通过，独立目录安装，官方固件未覆盖。

10:42 UTC 新源候选 aura-visual-servo-b4096-v1 加载成功；真实读取 ID 0x56535256 / ABI 1 / BUILD 0x14da0e60，初态/STOP flags=0、lease=0，PL 参考时钟 99,999,999 Hz。

10:43 UTC 有限协议测试通过：排他锁拒绝第二写方，未 ARM/重复序号拒绝；120 ms 许可约 120.073 ms 后到期且不能自动重新 ARM；1504/1496 µs 接受并回读正确；STOP 确认 2.970 ms。

10:43—10:45 UTC 实际 DPU 查询和 ResNet18 固定图 Top5 与基线一致。首次并行测试 PWM 提前到期，随后补充 4.003 秒有限测试，1500→1480→1520→1500 µs、92 次接受；推理结束时 PWM 仍有效；USB 采集/检测/显示继续增长。提交到 ACK 中位 3.281 ms、最大 3.944 ms，只是本次样本。结束 finally STOP，未设置常驻运动。

10:46 收尾检查误要求 VART 配置不变而失败，原证据保留；核对源码和实际配置，DFX 管理器加载 XRT_FLAT 自动更新 /etc/vart.conf，已正确指向新 XCLBIN。修正检查后 10:50 UTC 收尾通过：active/armed/bound/referenced=false、lease=0、有效测试点1500；PID 1498 独占相机，Monitor On，ZOCL refcnt=0，官方四个固件哈希保持不变。

真实 transport 已新增并上板验证；native 完整 32 位访存及屏障反汇编通过。38 项主机单元测试和编译通过。新增代码、原始证据、限制和后续标定见 [BOARD_TEST_REPORT](/home/ghmd/kv260-visual-servo-20261007/BOARD_TEST_REPORT.md) 与 CURRENT_BOARD_TEST.json。原运动 RTL、视觉算法和原 FPGA 工程未改。

引脚实际周期/脉宽/电压和机械运动尚未取得现场证据；示波器结果不能用有效宽度寄存器代替。用户尚未明确回复短时测试运动情况。当前 profile 保持未确认，蓝线固定映射和视觉随动未开启。overlay 属性泄漏警告、可选 AIE section -22 提示、源实现外部约束缺项与参考优化告警保留；仍为 controlled_bench，不是正式整机交付。

13:02 UTC 再次读取实际 X11 画面，预览/检测/显示计数增长且 rc=0；主机查看真实 framebuffer JPEG，确认摄像头画面与蓝线可见，UI MOTION OFF。随后最终寄存器状态复核再次通过，记录见 CURRENT_BOARD_TEST.json 的 final_refresh_evidence。未再输出 PWM。
