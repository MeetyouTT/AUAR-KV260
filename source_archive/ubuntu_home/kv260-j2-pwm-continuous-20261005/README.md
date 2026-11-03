# J2 持续 PWM 测试

用户明确要求一直输出。独立测试配置：50 Hz、1500 µs 高电平，显式 START 后持续运行，显式 STOP 或复位后保持低电平。RUN_FRAMES=0 在本版本表示持续模式；一秒及五秒版本的源码和证据保留。

本 50 Hz 版本此前已加载并持续运行，SCRATCH、空闲 STOP、运行中 STOP 与重新启动均通过，boot ID 未变化。用户后续要求换波形，本版本已于 `evidence/20261005T093908.195150Z-uart-restore/` STOP、卸载并恢复官方应用，原固件及 VART 配置核验一致。后续当前状态见 [10 Hz 方波项目](/home/ghmd/kv260-j2-square10-20261005/README.md)。外部照片出现重复窄脉冲，但幅度、测点和精确时序未确认，不能据此验收。证据见 [板测状态](BOARD_BRINGUP_STATUS.md) 和 [历史控制验证](CONTINUOUS_VERIFICATION.json)。

输入端 CH1 尖端 VIB、地夹 GND1，两处接点属于用户报告；本体与软件 10×、DC 1 MΩ、1 V/div、5 ms/div、CH1 上升沿约 1.6 V。持续输出可用自动触发和 RUN；重复脉冲目标周期 20 ms、高电平 1.5 ms。要停止，运行本目录 `scripts/uart_burst.py stop`；恢复官方运行 `scripts/uart_burst.py restore`，先 STOP 再卸载。
