# 本轮诊断源码

源码长度/SHA见../evidence/result.json，提供审阅依据，不是自动修复工具。

- board_snapshot.py、comparison_snapshot.py、final_check.py：板端只读快照，路径/接口为本项目专用。
- board_display_baseline.py：保存基线并单次DPMS唤醒，绑定旧boot。
- listen_uart.py：本机被动采集。首次180秒使用尚无interfaces选项及分片时间戳的前版；这里是随后60秒桥UART观察使用的新版，均无串口发送。
- shutdown_policy.py和board_shutdown_candidate.py：关机程序的源片段，不要单独执行candidate的--shutdown。
- board_shutdown_combined.py：本轮实际执行的完整关机程序，SHA71eed27c…；绑定旧boot、PID及配置，当前新启动应拒绝执行。无参数只作准备检查，--shutdown会正常停服、核验检查点并关机；已执行一次，不应重复或仅修改boot绕过守卫。

一个历史有效检查点和7个拒绝反例通过，共8项；软件回读不能替代实体屏幕验收。当前没有实现冷启动自动修复。
