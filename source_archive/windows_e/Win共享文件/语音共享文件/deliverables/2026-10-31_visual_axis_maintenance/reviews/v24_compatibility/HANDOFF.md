# v24兼容复核与R2候选

**结论：v24相关before pins匹配，仍保持三个源码改动的候选；R2进一步修复两个审阅发现。当前不能据此开启跟随。** 本窗口未访问设备、相机、模型服务或私库，未改运行、相机、记忆/common源码及冻结发布器。

## 已固定的兼容关系

- v24 spec SHA`9015c45a…`、mapping SHA`6fb98995…`与主窗口交接一致；canonical状态COMMITTED，ready SHA和spec关联通过。
- v23→v24的380组件只变更`board/runtime/board_memory_policy.py`为`d6e459f9…`，其余379项保持。视觉/GUI/运动相关23份基线逐项匹配，原GUI before `3ebb1b32…`仍成立。
- v24保存startup为`888faff2…`，保存supervisor330179/GTK330183、PAUSED/mic=false。均仅为保存时点，不是本窗口现场复读。后续v25或新启动先核对应版本和owner。
- 真实控制器清单在本地`offline_wide/manifests/controller-manifest.json`找到，SHA与v24引用的`5c8206ee…`完全相同。25项中22份Python全部与已有归档匹配；对应固件清单SHA`6a4b645a…`也与配置引用相同。
- 当前板端25项文件字节、加载的固件/VART/FDT、当前位置和方向仍未复读，保持UNKNOWN/null。两份清单本地闭合不授予运动资格。

精确证据见[evidence/v24_before_pin_check.json](evidence/v24_before_pin_check.json)、[控制器链](CONTROLLER_CHAIN.md)及[evidence/controller_manifest_chain.json](evidence/controller_manifest_chain.json)。本次仅补充原交接，没有改写原46项证据或R1候选。

## R2的两处追加修正

1. **过期报告下的对话框停止按钮。** R1将状态标为UNAVAILABLE后，原`pan_controls.refresh_pan_dialog()`会禁用专用STOP并提供重连。R2在同一份`face_pan_controls.py`的组合界面层，运行owner存在时保持专用停止可用、关闭重连入口。没有创建替代owner或扩大运动权限。
2. **普通重复帧仍执行原时钟检查。** R1的会话级重复帧提前返回，会遮蔽原`observe()`的时钟回退STOP。R2只在控制器重建后拦截旧帧重新确认；普通重复帧继续走原时钟、锚到期及禁止续期校验。`session_target_lock.py`本身与R1相同，原限位、斜率、lease、QUIESCE和故障STOP保持。

仍是替换`controller/continuous_session.py`、`aura/tools/face_pan_controls.py`及新增`controller/session_target_lock.py`。R2相对R1只再变前两份文件；不需要增加第四个源码补丁。

## 验证及为什么复跑

先核v24相关before pins，确认记忆更新本身不要求重跑视觉依赖。随后源码审阅发现上述两个新缺口，各自建立反例：

- R1对话框见证：8项GUI检查中1项失败，专用STOP确实变为不可点；R2对应8项全部通过，含原6项新鲜度测试。
- R1重复帧/时钟见证：1项失败；调整控制器入口后，相关41项全部通过，含原21项硬件斜率/wide回归、19项会话边界及新增1项时钟回退检查。

本轮分两个独立进程执行8+41=49项不同检查，均通过；不是声称一次整套49项实机测试。复跑由两处新源码改动触发，不由v24单独的记忆版本触发。原46项通过记录、两项新失败见证和所有日志均保留。

全为合成脸框、独立时钟假寄存器和轻量控件替身，未启动GTK或Native库，不证明物理按钮/引脚/舵机、真实识别准确率或长期稳定。

## 后续真实控制器与只读检查

- [READONLY_FIELDS.md](READONLY_FIELDS.md)给出GUI、相机health、当前脸观测、识别view和控制器报告的精确JSON指针；[field_catalog.json](field_catalog.json)为55字段机器可读目录，10份本地源码SHA和行定位在[evidence/field_source_proofs.json](evidence/field_source_proofs.json)。相机依据仍是旧boot8100快照，当前owner源码先核对，字段缺失不作健康值。
- `visual_timeline.steps`是视觉时间轴worker轮数，不是相机/脸帧数。`face_measurement_count`应读当前脸观测的`face_tracking.valid_measurements`。health中的`identity.match_diagnostics`可残留旧结果，当前识别使用新鲜相机UI state及源帧/源时间，不能用旧last_score认证。
- 会话`target_lock`在控制器`result.target_lock`，当前GUI选择性转发没有它；不要读取一个不存在的`manual_pan.face_follow.target_lock`。匿名运动键也可能不同于身份检测键，不能直接当图库或说话者ID。
- 保持55字段之外的实际固件、VART、FDT、停止参考、方向/安装、相机身份配置阈值、声纹标定等为UNKNOWN/null，直到主窗口新鲜检查。0.85阈值和权限策略没有修改。
- `controller_release_plan.json`展开25→26项的新控制器条目计划。新release须完整保留旧25项中的24项、替换会话文件并加锁模块；GUI三文件源码包不是完整可安装发布包。主窗口选择新root并固化完整清单，不覆盖旧冻结清单。
- 单次脸观测GET不会占用额外的face-stream消费者；既有流只允许一个消费者，诊断不能与实际跟随争抢。不要运行会创建Native传输的`run_face_motion.py`来冒充只读预检。

主窗口仍按原门槛串行核对当前boot/owner、成套固件与VART、DPU正常释放/恢复、当前停止参考和方向安装。阶段检查通过后再安排水平回正、丢脸停止、换目标需新会话、实际STOP与识别源龄联测。镜头居中不保证人正面/清晰，不表示身份或个人权限已确认。

## 文件与复现

- R2：[候选清单](review_bundle_r2/candidate_manifest_r2.json)、[三文件源码包](review_bundle_r2/visual_axis_r2_sources.zip)、[相对原基线补丁](review_bundle_r2/visual_axis_r2.patch)。未部署。
- GUI证据：[r1_dialog_witness.log](evidence/r1_dialog_witness.log)、[r2_gui_targeted.json](evidence/r2_gui_targeted.json)。复跑`python -B tools/run_gui_review.py --source r2 --label gui_recheck`。
- 控制器证据：[r1_duplicate_clock_witness.log](evidence/r1_duplicate_clock_witness.log)、[r2_controller_targeted.json](evidence/r2_controller_targeted.json)。复跑`python -B tools/run_controller_review.py --source r2 --label controller_recheck`。
- 封包`python -B tools/seal_review.py`只写本审阅目录，不安装、导入运动驱动或发送控制命令。
