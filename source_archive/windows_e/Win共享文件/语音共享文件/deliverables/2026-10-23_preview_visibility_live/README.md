# 隐藏相机预览停止处理：已上线（2026-10-23）

**已保留 GUI 修复。主页面 GUI 进程组 CPU 从149.88%单核降到94.88%，相对下降36.70%。** 切离视觉页后不再转换、缩放和推送隐藏预览；重新进入视觉页自动恢复。显示中的管线、分辨率、像素格式和角色8fps配置保持。

当前camera **499773**、GUI监督 **535987**、Xserver **1077**。本轮相机没有重启，camera unit `29786434…`保持。**YuNet仍因已有37.069ms/guard越界锁定在CPU保护；YOLO、SFace后端保持DPU。此修复不代表YuNet已恢复或长尾已根治。**

## 实测效果与范围

接受版helper `66cde810eb059dce…`，相同正式配置，每个状态约16秒。CPU为GUI监督及其子进程总和，100%代表一核；它不是整板CPU百分比，也不是模型推理加速比。

| 状态 | 原GUI CPU | 修复后GUI CPU | 相机预览 |
|---|---:|---:|---|
| 视觉页 | 148.84% | 147.36% | 12.49→12.73Hz |
| 主页面 | 149.88% | 94.88% | 隐藏预览201帧→0帧 |
| 再次进入视觉页 | — | 147.09% | 12.68Hz，重新绑定成功 |

主页面角色送显8.049→8.058Hz，P95间隔152.33→134.04ms；另外两组约8.18/8.12Hz。频率来自native sink handoff，不是HDMI物理扫描测量。CPU收益限定在**预览隐藏的页面**；视觉页保留实际视频处理，不能宣称所有页面都下降36.7%。真实场景输入非逐帧配对，直接功能证据是隐藏输出退休、帧增量为0、再显示重新收到新鲜帧。

验收期间camera PID和后端保持：YuNet故障 **2→2**、时效缺口 **1→1**、主周期超限 **1→1**、新增USB/音频告警0。SFace累计52次/超限0，接受窗口无新请求；不称三模型持续满载或认人精度复验。30ms上限、5ms guard、1000ms业务TTL、250ms预览期限、身份阈值与新旧数据库均保持。

## 改动与验证

- [board_avatar_gtk.py](candidate/aura/tools/board_avatar_gtk.py)：vision/large窗口unmap时解绑，map使用代次避免旧50ms回调复活；同XID重映射沿原同步绑定流程。
- [board_camera_preview.py](candidate/aura/tools/board_camera_preview.py)：无输出时跳过服务/帧读取；输出退休与推流按对象身份和生命周期锁同步，正常FLUSHING不报错，释放handler/probe。

15项离线生命周期、16项发布保护测试通过；真实GTK/GStreamer/X11的5项离屏合成帧检查通过，包括隐藏停止、同XID恢复、large独立继续、全部隐藏不读取、快速重映射。实流视觉→主页面→视觉检查通过。最终核对175份Python源，仅上述2份改变；原native库、已修的SFace不可用处理均保持。

源码差异及独立复核在`independent-review/`，数值原值在[evidence/trial.json](evidence/trial.json)，当前服务/源码/回退核对在[evidence/final-audit.json](evidence/final-audit.json)。生成时的`activation-manifest.json`不等于最终状态；当前状态看`ACTIVE_RELEASE.json`。

## 已保留的失败与故障

1. 第一轮因YuNet已有保护停用而在GUI切换前拒绝，无生产修改；已保存32.704/37.069ms两条正常完成status0的数值证据，后一guard越界约1.536ms，owner未fence。
2. 第二轮得到主页面GUI CPU下降36.80%，但末尾发现累计时效缺口0→1，因此拒绝并**实际恢复原GUI528120**，相机仍499773，guard退出。缺口下/上界均8ms，其单调时间早于候选运行目录标记68.112秒；不把这次结果追认为通过。
3. 最后一轮保留既有gap1、fault2，要求计数不增加也不减少；通过后保留。没有重启相机、清计数或放宽TTL来通过。相同恢复协议上一轮已实际执行；当前手动入口只执行了只读`--check`。
4. 一次启动请求因本机提前轮询占用串口而被独占保护拒绝；没有板端命令重叠。上传完成后仅重试启动，证据保留。

## 当前运行与回退

GUI runtime：`/home/root/aura-video-cpu-20261023/66cde810eb059dce/runtime`。仅新增自有13z前缀override；原12z可靠性配置和其它dropin保留。相机仍为`release-reliability-f7624754038f-450136`。

操作见[OPERATIONS.md](OPERATIONS.md)。后续Windows发布需合入此2源生命周期改动；不要用旧GUI完整副本覆盖当前运行源。双方回执分别维护，本轮未修改Windows回执。所有新交付只含代码、哈希与数值记录，没有身份库、权重、真人照片/音频/向量或原始串口内容。

后续仍需处理YuNet提交/返回长尾与guard越界、SFace有界恢复、独立陌生人/多人、冷启动和整机长稳；本次仅完成GUI可见性修复。
