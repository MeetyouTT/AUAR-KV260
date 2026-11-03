# 2026-10-02：运行时联合启用准备

已阅读最新 DFX/ZOCL/M3 封存结果，准备联合输入包。DFX manager 和修复 ZOCL 逐字节匹配已板测二进制；压缩包成员回读哈希通过。未重新编译、修改原产物或执行板端切换。

本次 Ubuntu 未发现 /dev/serial/by-id，未取得新的板端实时状态；旧恢复结果只作为历史证据。接回备用卡和 USB 串口后，先重新预检与备份，再受控启用、扩大运行观察及确认恢复入口。无需重新烧录 SD 卡。30 轮切换和 30 分钟采样属于计划，尚未执行。

原程序中两项软件缺陷、重复 /boot 配置、overlay 属性警告和既有 DRC/时序限制保持记录。永久启用、重启验收、长期验证和 PWM 尚未完成。

方案：[NEXT_STEPS.md](/home/ghmd/kv260-runtime-enable-20261002/NEXT_STEPS.md)。
联合包：/home/ghmd/kv260-runtime-enable-20261002/bundle/kv260-runtime-reviewed.tar.gz

准备时间：2026-10-03T06:27:41.266749+00:00。
