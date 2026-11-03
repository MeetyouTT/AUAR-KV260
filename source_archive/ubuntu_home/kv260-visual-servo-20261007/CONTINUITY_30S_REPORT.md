# 30 秒稳定性与左右移动补测（2026-10-08 本地日期）

最新更新：上电后 30.135 秒、374/374 条命令接受，双向及中心覆盖、TIME_LIMIT 正常结束、完整 trace 主机核验通过。30 秒双向视觉命令测试已通过；机械方向与准确指向尚未验收。重复观察于 14.988 秒因人脸框右沿贴边停止。用户反馈动作太慢、太小后，已完成 1400～1600 µs 固定往返两轮，28.717 秒、616 条接受、端点到达核验通过、最终 STOP。详见 [最新记录](/home/ghmd/AMD_Smart/logs/daily/2026-10-08-SERVO-VISIBLE-TEST.md)。下文保留此前实测历史。

结论：中心位置的真实视觉命令连续提交通过 30 秒；左右移动的连续 30 秒随动尚未通过。本轮最终输出禁能、镜像预览正常运行。中心稳定通过不代表已经完成准确机械指向或完整左右随动。

| 测试 | 实测 | 结论 |
|---|---|---|
| 首次测试 | 2.233 秒，27/27 条接受，1500..1504 µs | LOST_OR_AMBIGUOUS 后停止 |
| 中心稳定 | 30.143 秒，375/375 条接受，目标及有效宽度读回始终 1500 µs，方向全为 CENTER | TIME_LIMIT 正常结束，30 秒连续提交通过 |
| 左右补测 | 6.522 秒，80/80 条接受，CENTER/CLOCKWISE/COUNTERCLOCKWISE 均有记录，目标及有效宽度读回 1496..1509 µs | LOST_OR_AMBIGUOUS 后停止，左右连续 30 秒未通过 |

中心稳定窗口 ACK 时源年龄中位 56.262 ms、最大 82.225 ms；提交中位 2.904 ms、最大 9.982 ms。左右窗口 ACK 时源年龄最大 70.521 ms、提交最大 3.459 ms。三轮均未发生源过期或硬件租约中断，结果只代表本次测试窗口。

## 本轮新增诊断

新增 quality_visual_direction_start.py，仅在既有 bench 的 STOP 分支追加当时 observation；先核对完整源 SHA 和精确替换唯一分支，再执行。既有阈值、速度、限幅、提交预算、源时间、ARM/COMMIT/STOP 行为及时间上限不变，原板端发布源码未修改。脚本语法编译通过。

两次失跟时，新 snapshot 中只有上一帧目标缓存，visible=false、consecutive=0，没有当前可见目标。此前框均完整位于图像内部；左右补测最后有效框约 [199.659,185.212,259.045,256.461]，score=0.999517，是上一帧分数，不能代表失跟帧的分数。源码 FaceTracks.update 对未匹配目标立即标为不可见；本记录可以证明“新帧没有有效可见人脸观察”，不能仅据此断言用户转头、光照、模型置信度或裁剪哪一项是根因。

两个 5 秒只读预检均通过，年龄最大约 137 ms，分别有 64/63 帧满足测试条件。保持正脸后的中心测试完整通过。用户实际动作方式已询问，尚未收到本轮回复，不能把推测写为现场确认。

## 收尾和证据

最终独立核对 flags=0、lease=0、ACK=80、active/armed/bound/referenced=false，width_us=1500 为停止后保留值；摄像头 PID 16981 唯一拥有者，采集/检测/显示增长，error=null，显示 On，原官方固件哈希不变。

boot c2753755-e758-4ab6-a4b6-2929271aa723；camera epoch d9c2155d0af74326904cbb9b0ba94b31。UTC 2026-10-09 03:22—03:28 对应本地 2026-10-08。

原始证据目录均位于 /home/ghmd/kv260-adaptation-check-20261006/evidence/：

- 首次预检：20261009T032231.210307Z-newboot_visual_preflight
- 首次测试：20261009T032309.271167Z-quality_visual_direction_start
- 第二次预检：20261009T032440.372095Z-newboot_visual_preflight
- 中心稳定：20261009T032515.292668Z-quality_visual_direction_start
- 左右补测：20261009T032659.476867Z-quality_visual_direction_start
- 最终停止：20261009T032758.428276Z-newboot_vsrv_final
- 三轮完整事件回读及主机检查：见 CURRENT_CONTINUITY_TEST.json 的 trace_verification

执行结果、输出 SHA、UART 回显恢复与原始记录均保留。此次没有修改 RTL、模型权重、速度/增益或放宽过期/失跟保护。状态更新见 [CURRENT_CONTINUITY_TEST.json](CURRENT_CONTINUITY_TEST.json)。

下一步应针对移动时未取得有效人脸观察收集原始帧与检测结果，结合实际动作方式定位原因，再补左右连续 30 秒；不要用预测位置续租旧目标。机械方向、机械零点及三点指向标定仍待实测，1500 µs 仅此前授权测试点。
