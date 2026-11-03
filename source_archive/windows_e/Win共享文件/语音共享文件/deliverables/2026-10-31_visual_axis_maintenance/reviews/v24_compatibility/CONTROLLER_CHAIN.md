# v24真实控制器与清单关系

本次补齐本地清单链，未操作设备。v24的`config/pan_face.local.json`与v23相同，它不是当前boot的运动资格证明。

| 层 | v24引用及校验 | 本次结论 |
| --- | --- | --- |
| 业务GUI | `tools/face_pan_controls.py` before `3ebb1b32…`，相关23组件与v23相同 | 当前v24候选仍可按原before SHA审查 |
| 手动配置 | `pan_manual.local.json` SHA`60e54c03…`，boot55152f95，`face_follow_config`指向旧gui-wide-v1 | 仍跨boot；不能仅改boot解除FAULT |
| 人脸配置 | `pan_face.local.json` SHA`19e0a563…`，release_root=`/home/root/aura-pan-wide-20261028/control-10282601` | 与v24组件清单匹配 |
| 控制器清单 | 本地`offline_wide/manifests/controller-manifest.json` SHA`5c8206ee626c91c9f311ee870245813e169ac14e554e2579554c74489066f562` | 与face配置引用完全相同；25项路径/长度/SHA已展开，22项Python逐项匹配本地归档 |
| 固件候选清单 | 本地`offline_wide/manifests/candidate-manifest.json` SHA`6a4b645a5bbfd35c9107976edf27886cf8e0c91e40f48be6f052a95e1172c1cf` | 与face配置参数`manifest-sha256`完全相同；不意味着当前已加载 |
| 当前板端文件 | 上述25个destination及实际固件/VART/FDT | 未复读，逐项`current_board_pin_matches=null` |

前次交接将独立清单内容保留为缺项；本次在本地`manifests`目录定位到完整字节，已闭合引用关系。原证据保留，并由本审阅记录补充；“板端当前字节尚未核对”仍然成立。

## 独立发布包包含什么

25项中有22项Python、2项Native库及1项许可证。完整条目和SHA见`evidence/controller_manifest_chain.json`：

- 启动和会话：`run_face_motion.py`、`continuous_face_control.py`、`continuous_session.py`、`hardware_slew_session.py`、`boundary_rearm.py`、`face_zone.py`。
- 输入及诊断：`face_stream.py`、`input_timing.py`、`run_input_diagnostics.py`、`common/__init__.py`、`common/motion_observation.py`。
- 驱动及预算：`pulse_driver.py`、`lease_aware_driver.py`、`batch_driver.py`、`batch_transport.py`、`deadline_driver.py`、`pwm_budget.py`。
- 输出收尾：`live_report.py`、`live_writer.py`、`session_shutdown.py`。
- 轨迹兼容：`trajectory.py`、`one_euro.py`、`libaura_trajectory.so`、`LICENSE.Ruckig`。
- Native批量读：`libvsrv_batch.so`。

R2仍只有三个源码改动。新控制器清单需要保留旧25项中的24项，替换`continuous_session.py`并新增`session_target_lock.py`，合计26项；GUI另外替换同一份`face_pan_controls.py`。`controller_release_plan.json`只是可审查的条目计划，不是发布清单，不指定新设备路径，不授权加载或运动。二进制不复制进本候选包。

## 清单以外的关联门槛

`FacePanProcess.arguments()`先检查face配置的控制器清单SHA并校验全部destination，再启动该root下的`run_face_motion.py`。新模块必须进入新的完整清单；不能只传文件后沿用旧清单，也不能改写冻结清单来掩盖变化。

`run_face_motion.py`从固件release导入`bench_identity_stop.validated_context`，按`manifest/context`验证平台；从该验证返回的固件root取得`vsrv_driver/vsrv_transport`，并使用控制器自己的batch/lease/deadline模块。随后插入的搜索路径顺序是控制器目录、固件root、app-root，已有模块缓存还会影响实际导入。不能把GUI树中的`board.motion.*`核对当作独立控制器顶层驱动也已核对。

v24配置参数`app-root`仍指向旧`gui-wide-v1/runtime/aura`，`context`、`zone-settings`、方向和人工证据仍绑定旧5515目录。主窗口准备新release时要成套核对这些输入：当前boot/FDT/FPGA/VART及配对文件、方向/安装/停止参考、区域设置、手动release，以及关联的source pins。遇到不匹配保持拒绝，不为获得READY改弱检查。

手动后端`manual_live_config.current_config()`要求本GUI自己的`startup/config.json`组件清单与pan配置字节相同，并检查传入base中的boot/FDT/face-config/enabled不变。此处不应拿旧gui-wide-v1配置代替生产v24；更新配置必须由主窗口正常发布流程完成。

子进程退出后，`verified_stopped_face_command()`核对同boot区域设置、报告SHA、受允许的控制器清单及其全部destination，再比较flags/lease/脉宽/目标/ACK/epoch/session/reference。新release的停止报告应进入新root的runs；旧前驱报告不能代替本次实体位置或当前启动证明。

启动`run_face_motion.py`会创建Native寄存器传输，并可能ARM/COMMIT；其中前置的“只读状态benchmark”不使整个程序成为只读检查器。只读盘点应读取固定文件及既有状态投影，不能运行它来测试加载是否匹配。

## 对识别稳定性的实际作用

现有模式是水平转轴越线后向画面中部回正，回到中部停止，并非持续保证人脸正面姿态或清晰度。会话锁减少已知轨迹ID更换导致的静默换人，固定锚保持短时像素连续性；二者都不是生物身份认证。身份仍由原SFace/源龄/图库版本及0.85阈值决定，个人权限另受原本地授权和未标定声纹限制。

主窗口后续可用数值/布尔检查：同匿名运动键在帧推进时是否稳定、脸中心是否回到容差区、遮挡/离开是否停止、目标更换后是否需要新会话，以及新鲜脸源/正面姿态和识别结果是否各自满足自己的TTL。实体朝向、实际角度、模糊度连续指标、多人交叉识别准确率和长稳仍为未验。
