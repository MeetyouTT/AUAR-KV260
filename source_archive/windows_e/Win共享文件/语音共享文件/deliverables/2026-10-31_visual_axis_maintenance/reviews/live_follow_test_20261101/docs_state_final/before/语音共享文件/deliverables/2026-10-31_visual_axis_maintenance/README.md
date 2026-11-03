# 视觉与转轴维护候选

**最新实板只读回执：[平台阻塞、V2纠正包与共存恢复顺序](reviews/platform_receipt_v2/HANDOFF.md)**。新回执SHA18de8aba…已核验：实际加载及VART均为BENCHMARK_B4096；wide四件文件、25项控制器及手动3个payload在盘上匹配，但boot/FDT/方向绑定不符，位置仍未知。V1探针3条driver路径误放在release同目录，现按已核验validator纠正为`release/driver/`；原UNAVAILABLE不能判文件缺失，正确位置仍待主窗口复读。V2新增6项布局检查通过，原28项IO和R2证据保留。本窗口未访问设备或修改运行；以下旧轮次状态按历史保留。

**下一轮只读核对：[新投影与平台脚本交接](reviews/platform_readonly_v1/HANDOFF.md)**。主窗口提供的投影SHA已核验，保存状态确认同owner/380组件、follow=false、FAULT/null及身份后端可用；固件/VART、位置方向仍UNKNOWN/null。已提供固定v24策略的只读脚本与两文件包，28项假文件系统/HTTP测试通过，未实板执行。R2候选原样保留。

**最新复审：[v24兼容与R2交接](reviews/v24_compatibility/HANDOFF.md)**。v24相关23份before pins一致，已补齐独立控制器25项清单映射。R2追加修复过期报告下专用STOP按钮被禁用、普通重复帧绕过时钟回退校验的问题；本次8项GUI＋41项控制回归通过。原R1三文件及46项证据完整保留，以下是原轮次记录。实际设备、固件/VART和本次位置方向仍待主窗口新鲜核对，未部署。

本目录按主窗口约定的2026-10-31任务名保留，离线收尾日期为2026-11-01（America/Los_Angeles）。**当前不能据此恢复跟随；已完成源码核查、最小候选修补和46项离线回归，未部署。**

v23保存状态为跟随关闭、机械FAULT、脉宽null、监听PAUSED/enabled=false/mic=false。本窗口没有复读现场，保存PID、boot和READY不能当现在状态。

- [交接与现场门槛](HANDOFF.md)
- [数据流和源码依据](DATAFLOW.md)
- [结构化状态](HANDOFF.json)
- [三个文件的候选清单](review_bundle/candidate_manifest.json)、[补丁](review_bundle/visual_axis_candidate.patch)、[源码包](review_bundle/visual_axis_candidate_sources.zip)
- [最终46项结果](evidence/after_fix_safety_final.json)、[完整日志](evidence/after_fix_safety_final.log)
- [修补前41项反例](evidence/before_fix.log)、[基线指纹](evidence/baseline_manifest.json)、[阈值核对](evidence/threshold_audit.json)

## 修补内容

1. 真实连续跟随控制器增加会话级匿名人脸锁。目标ID/代次、相机/服务上下文变化后停止并结束本会话；不会在重建单个运动段后自动接纳新目标。同一匿名目标短暂丢失时先停止，再用新的实际画面重新确认；不继承旧图像许可、ARM、速度或租约。控制器重建后仍拒绝旧帧、倒序帧和同帧内容变更。
2. 界面只把1500ms内的运行报告用作当前反馈。启动无收据、过期/未来/无效心跳和结束报告不再沿用旧手动脉宽；显示状态不可用并保留停止入口。停止收尾未确认时继续保留重试入口。脉宽始终是控制读回，不是实体角度。

候选只更改`candidate/controller/continuous_session.py`、`candidate/aura/tools/face_pan_controls.py`，新增`candidate/controller/session_target_lock.py`。原wide硬件斜率、限位、lease/STOP/QUIESCE、故障及过期保护、方向/位置资格检查均保留；未修改相机、识别、记忆、冻结发布器或运行目录。

## 验证范围

原21项硬件斜率/wide测试保持通过，新增25项涵盖换人/换代、丢脸、相机/服务更换、跨段重放、源锚点到期、未确认目标、停止语义和界面报告新鲜度，合计46项通过。全部使用合成框和假寄存器，没有相机、模型、网络、MMIO或运动。

修补前首次41项运行产生17个失败及2个缺少新增诊断字段的错误；其中目标替换反例确实从2次提交继续增长到8次，并再次ARM。原21项当时均通过。失败原日志与首次候选41项通过结果完整保留；后补4项验证新的重复帧门槛不遮蔽锚点到期和源质量检查，45项通过结果也保留。末轮将同板视觉目标切换继续归入完整脉冲QUIESCE，同时保留boot/方向/几何故障的立即STOP，补测后最终46项通过。

测试中的`tests/fixtures/test_recenter.py`沿用历史测试场景和包格式，将原Linux Ruckig加载替换为一旦被调用就失败的占位轨迹；本次测试的硬件斜率模式不调用PS轨迹。原21项断言未改。假设备模拟不是新RTL、引脚波形、机械响应或识别准确率验收。

复跑：在本目录执行`python -B tools/run_offline_tests.py --tree candidate --label local_recheck`。封包脚本只写本目录：`python -B tools/build_review_bundle.py`。`prepare_baseline.py`用于首次组装，已存在的基线/候选会拒绝覆盖。

## 必须保留的证据边界

- GUI基线及三个历史转轴配置与v23组件SHA一致；真实跟随入口是`FacePanProcess`启动的独立wide控制器。`board_pan_follow.py`只是影子评估器。
- wide控制器来自已有归档清单并逐字节核对；尚未取得板上`control-10282601`源码与该归档一致的新鲜证明，不能直接把本候选包当板上补丁部署。
- 相机源码另有独立owner。已读相机源码快照属于旧boot8100/PID1334，不能由v23的380个GUI组件推定为当前相机源码核对通过。
- v23对应公开配置阈值为0.85，业务根旧副本仍为0.50；本次均未改。当前相机实际识别配置仍须主窗口现读。匿名脸框、人体ID、运动锁定和人脸匹配均不授予个人记忆权限；未标定声纹约束保留。
- 当前模式由PL每20ms最多4µs改变输出脉宽，标称200µs/s；不能将配置中旧PS的40µs/s或加速度/jerk字段冒充该模式的实际机械速度约束。既有软件提交截止检查仍有最终相对租约写入窗口，未宣称新增绝对源期限硬件保证。
- 无真实帧、人脸模板、对话或权重导出。候选包没有配置、固件、Native库、模型或安装器。
