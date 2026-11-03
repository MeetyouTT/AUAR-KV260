# GUI-only发布流程独立复核

**最新小修订：协议16项全部通过，生命周期仍为15项；2源候选和真实Gtk结果未变。** root上轮GUI-only实流虽得到隐藏CPU下降/重映射恢复，但camera gap从0增到1，已明确拒绝并实际恢复原GUI，不因后续时序说明追认。当前只允许下一轮以**既有非负int gap1**开始；`assert_camera_unchanged`要求结束仍为1，增加到2或清到0均拒绝，不重启相机、不改TTL。

新增仅两项反例：既有gap1→1允许且快照/计数不改；gap1→2及1→0均拒绝。16项单次最终结果写入builder统一`trial-review-tests-final.log`，旧14项日志为`trial-review-before-preserved-gap.log`；当前controller SHA见清单。已读到camera_after先保存再validate、各measure记录起终monotonic_ns，后续拒绝仍可核对完整终态与窗口。此改动只改变基线事实的保留，不声明gap已修好，也不改变GUI以外验收范围。

**后续降级基线修订已复核：** 首次真实预检因同camera499773既有YuNet LATCHED拒绝，没有mutation。root未重启清计数，改为明确仅验收GUI生命周期、保存原CPU fallback及两条已完成故障。当前controller14项、生命周期15项全部通过；对应最终日志与SHA清单已更新。以下9项为前一修订的历史过程。

新增`validate_preserved_camera`只允许事件证据齐全的已完成YuNet LATCHED：overruns为正整数、task1事件数匹配且event_sequence唯一、native_completed=1/status0/native_failed0/body_failed0；owner_fence、未知/未完成native、空/缺/重复证据和SFace disabled/unavailable仍拒绝。guard曾越界但作业已完成可以作为**原有降级事实**保留，不表示DPU任务重新运行或保护已解除。

新增真实`assert_camera_unchanged(before,after)`以同PID、相同backend、所有kind并集的disabled/overruns、primary计数验证前后保持，拒绝新增故障、切后端、改PID或清计数。报告标注`GUI_LIFECYCLE_ONLY_EXISTING_CAMERA_FAULTS_PRESERVED`和`preserved_camera_degraded`，不得把GUI通过写成DPU整体恢复。

本轮只新增5项controller反例到14项，最终日志`trial-review-preserved-camera-final.log`；连续30轮frame_visible=false不触发unmap/attach的单项回归使lifecycle达到15项，日志`lifecycle-tests-final.log`。现役baseline和候选原本已是`preview_image.set_visible(True)`，旧共享副本中的bool(image)条件没有被迁入，**本次没有为此修改候选业务源SHA**。父级Stack/对话框可见性继续控制真正的map/unmap，placeholder/clear黑帧和按钮ref时效保持。

范围：本地只读审查`gui_trial.py`，另写独有`tests/test_trial_review.py`；未改root控制器或业务候选，未接UART/板卡、未启动GUI/音频/模型。受审文件SHA见`trial-reviewed-manifest.json`。本结论只覆盖本轮发现及测试的流程，不代替主任务实际Gtk/Gst与受保护业务验收。

## 发现与修订确认

| 发现 | 影响 | 当前修订 |
|---|---|---|
| 完整`systemctl show ExecStart`含PID/启动时间等动态字段 | 同一原命令正常重启也会在回退末尾误失败，guard可能保持 | 改为保存、比较`/proc/MainPID/cmdline`；原ExecStart仅作记录。独立新PID/相同argv回退测试通过。|
| `copytree(...,symlinks=True)`后直接写候选 | 源Python若是link，可能沿链接覆盖原BASE | clone前拒绝Python symlink/非自身resolve；候选写前再次验路径。临时目录symlink反例确认原源未变。|
| 停GUI后任意新PREF SHA直接加入白名单 | 并发用户语义变化可能被误作自有规范化保存，随后被原文覆盖 | 仅接纳与私有原件JSON语义全等的新字节；语义变化拒绝且不覆盖，规范化格式变化允许。两项测试通过。|
| guard在两段baseline页面改变之后才arm | controller在baseline阶段被杀时无法独立恢复原vision页面 | 600s guard提前到首次measure之前；`gui_transition_started`区分仅改页与GUI切换，前者guard只恢复原页。顺序检查通过。|

主任务同时修了已知的三处：异常明确清`accepted/passed`；在stop前记`mutated/gui_transition_started`覆盖部分成功；DPU比较原同进程故障计数差值、保留既有累计，不以重启过关。这些改动已在当前源中读到，没有扩大为重启相机或放宽保护。

## 已执行独立检查

`python3 -B -m unittest discover -s /home/ghmd/aura-video-cpu-20261023/tests -p test_trial_review.py -v`：**9项全部通过**。标准库测试仅使用自有临时目录与Mock服务，最终版禁止测试网络请求。

覆盖：新PID同argv的原GUI恢复；只读check不stop/start/write；已接受候选的普通guard不撤销；手动恢复中的guard不被accepted标记挡住；手动恢复先arm独立timer后stop；源link不覆盖BASE；语义变更偏好不接纳；仅JSON格式变化可接纳；600s guard先于首次baseline页面操作。

初轮在guard仍旧顺序时8/9通过，唯一失败记录在`trial-review-tests.log`；root修订后新增stage标记使旧夹具误入page-only分支，已保留`trial-review-tests-fixture-update.log`并补相应夹具状态/全局禁网络，最终日志`trial-review-tests-final.log`为9/9。修夹具不改变root业务或控制器。

## 当前可确认的边界

- 控制器只stop/start GUI；camera PID、unitSHA、Xserver PID及现有DPU owner需持续保持。原静态库和identity/config/database进入protected，原dropin集合按SHA核对，仅增删自己的13z override。
- 原偏好私有保存、允许等价规范化后再恢复原字节；语义变化应拒绝，不把它悄悄当可覆盖数据。
- 未accepted的独立600s guard可回退；手动恢复另arm120s guard。仅改baseline页面的失败恢复不重启GUI；进入GUI切换后失败走同一restore路径。
- CPU为进程组tick差值与真实received帧计数；隐藏预览0增量、当前输出inactive，可见及重新map后帧率/年龄/头像8fps均是独立门槛。不能把回调入口当物理扫描率。
- 初始和最终DPU记录必须同PID、无新增fault/primary overrun，counter已有值保留；当前源按该差值验收。若真实故障导致锁定，应保存并拒绝GUI验收，不自动重启相机清零。

主任务报告真实离屏Gtk/Gst/X11五项已通过；我没有复跑或独立接板验证。最终发布仍取决于root的GUI-only受保护试运行、原页/偏好/源/owner核对及实际回退检查。本轮发现的阻断在当前修订均已处理，未提出新的扩展改动。
