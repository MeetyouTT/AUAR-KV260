# 多终端并行推进

用户继续并重复允许多个终端。读ZIP README、共享入口/规则、现行计划及最新日志/release。首次3个agent额度拒绝，后续新会话成功：audio_audit_continue、timing_continuation、sface_supply_continuation，均只改独立本机目录；主任务独占UART。

当前215707/215734/1077原配置只读核验源/模型/unit/旧库路径通过、YuNet DPU仍运行，最大26.826ms/估计偏差1/真超限0；音频日志尾最后告警比读取时间早约1030秒，journald重启28未增。该瞬时检查不是长期根因证明。

板端合成同输入真实callback微基准：原/候选各240次、6组AB/BA，OpenCV1线程中位CPU2.9831→2.6278ms（11.91%），2线程3.2537→2.5673ms（21.09%），像素/内存/layout通过。真实Gst1.18.5 appsrc→appsink各12个合成BGR Gst.Buffer，原/候选callback逐值/own data/释放后结果通过，管线NULL释放。没有第二UVC采集/DPU/音频，没有改生产，原PID保持/检测增长。微基准extract_dup模拟，不能当USB整链或整板CPU收益；两轮线程条件分别报告。脚本b5404b… / a5730d…，证据私有run_staged_helper目录，过滤数值进共享新包。

主任务从活动startup config解析实际runtime/aura回收tools/board_avatar_worker.py、board_recording.py、barge_in_capture.py、board/runtime/audio/echo_cancel.py、channel_jobs.py，5源SHA核验齐全。第一次路径少aura子目录只报缺失，无文件改动，修正后成功。私有actual-source供音频agent接线审查，不复制配置秘密。

后续软件候选结果待补；共享2026-10-22_parallel_pipeline记录进行中，不宣称正式SFace或全局CPU优化已启用。
