# SFace 真人三模型 DPU 影子短测

UTC2026-10-22约07:18～07:20，用户回复“现在有人”后执行。结论：真实相机人脸的SFace INT8特征计算已在KV260 DPU完成，和YOLO、YuNet在同进程共享owner和调度器。20秒观察通过，随后按预案恢复到已通过30分钟检查的YOLO＋YuNet配置。当前生产身份仍配置Windows CPU，SFace影子已关闭。

| 实测项 | 结果 |
| --- | --- |
| 实际SFace执行/完成/特征返回 | 10 / 10 / 10 |
| 通过目标与时效复核的结果 | 10；这不是10次身份识别正确 |
| SFace特征调用耗时 | 平均14.478ms，最小12.090ms，最大19.487ms |
| SFace DPU调度占用最大值 | 14.910ms；与含CPU预后处理的调用耗时分开 |
| 可选任务准入 | 请求17次，执行10次，7次无合适DPU时间片而延后；0计算失败/0过期结果 |
| YOLO / YuNet有效速率 | 10.039 / 2.148Hz，使用20秒观察内计数差计算 |
| CPU四核总量 | 20.021秒窗口65.601%；末5秒64.484% |
| MCP01匹配播放告警 | 0 |
| 影子身份决策/模板写入 | 0 / 0 |
| 回退完成 | `passed=true`、`complete=true`、`rollback_verified=true`，回退timer停止 |

耗时统计从影子worker开始调用特征后端到得到向量，包含该调用内CPU预后处理和调度执行，不含摄像头采集、YuNet检测、排队等待、远端Windows请求和身份判定，不能当作摄像头到身份结果的全链时延。全部20个1秒健康快照和最终计数见[完整报告](evidence/sface-shadow-pilot-full.json)。DPU模型为10,796,375B，SHA `12b2ff5c7de157133ebd5aa71665fc5ddcd1f65d9e30e2d6e965e0752e467f25`，精确model_id为`sface-int8-12b2ff5c7de15713`。

测试前5秒CPU69.133%，与上述20秒CPU窗口长度、启动影响和真人画面不同，且原Windows请求仍保留，不能将差值作为SFace迁回的CPU收益。此次未启用XRT忙时采集，没有新的三模型忙时百分比；此前4.66%～4.80%仅属于双模型窗口。SFace低频影子请求也不是最大吞吐或2Hz能力验收。观察窗口内YOLO周期超时累计1次（启动已有），YuNet初始20ms估计偏差累计1次/最大23.508ms，真正可选任务截止超限0；SFace预算偏差及真正超限均0，不称全链零超时。

`compare_cosine=false`让影子在原Windows特征请求前独立入队。Windows8792此前TCP及health超时，尚未定位到远端主机、监听或防火墙；没有同图FP32特征用于余弦比较。原Windows异常及FP32身份判断语义保持，不能把DPU输出成功说成身份功能已经离线可用。未创建INT8登记库，未设置现场阈值，没有读取或迁移原FP32向量。

短测新相机PID164951，完成后原YuNet根重新启动为PID165277；UI主PID131932和Xserver1077保持。单元SHA恢复为`84116d8faf6f4d3972f5f2eac35f8c98cf8ecbe51752a8f78d803aa8a7cdd75c`，6份YuNet源码/模型/manifest和旧数据库路径均通过独立复核，影子为空，相关回退timer全部inactive，XRT统计关闭且检测继续推进。见[最终活动审计](evidence/active-release-audit.json)。新进程短暂启动时的累计Hz不能替代上述观察内速率；最终审计新的YuNet最大调度占用25.914ms/估计偏差1次属于恢复后的新进程，不混入先前30分钟的22.069ms统计。

实现、16项软件回归的冻结快照见[sface-shadow-candidate](sface-shadow-candidate/README.md)，始终回退脚本及3项本地准备检查见[deploy-preparation](sface-shadow-candidate/deploy-preparation/README.md)。这些子目录README/manifest保留生成时状态，是否实板执行以本报告和release.json为准。主任务独占UART，另一个Codex只准备本机代码，不并发操作生产。部署wrapper、只读收集/审计脚本及模型SHA在本交付中留存；预训练模型位于[首轮模型工件](../2026-10-21_dpu_vision_start/README.md)。

本轮证明三模型真实共享DPU调度可行，尚未证明较长三模型稳定、身份精度或正式登记闭环。下一项为独立版本INT8登记和同人/异人/多人歧义现场验收，再做长期三模型和相同输入负载的对照。原始UART、摄像头图像、人脸裁剪、音频、特征数组和身份库均未写入共享交付；Windows同步与独立回执未确认。
