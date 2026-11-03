# 2026-10-11 项目全局进度复核

## 结论与范围

响应用户“整个看看我们这个项目，看看做到那里了”。先阅读完整 ZIP 的 README、无声源定位方案、当前分工与 FPGA 入口，再核对最新框架、主仓源码/配置、10 月 2—11 日日志和独立板测证据。当前处于“多个子系统已上板、统一整机正在集成”的阶段；完整视觉身份、真实语音问答、创新方法实验和正式发布尚未完成。不以文件数或单元测试数换算完成百分比。

本轮没有连接板卡或 Windows 服务，没有启停设备、加载 PL、播放录音或发送运动命令。历史板测描述的是对应测试窗口，不是本轮在线状态。当前人员安排以 10 月 9 日更新为准：A 负责视觉与 FPGA，玩偶运行于 KV260 PS/Linux；B/C 的最新具体个人任务未由本轮重新指定。

## 分模块状态

| 模块 | 已有成果与证据级别 | 尚缺的验收 |
| --- | --- | --- |
| 平台、Linux、DPU | PetaLinux 2022.2、B4096 基线推理；管理器/ZOCL 修复有持久化及历史断电冷启动证据；DPU 与自研 VSRV 同配置有限板测通过 | 最新 UI/相机/项目模型/运动组合的启动与整机长稳 |
| FPGA 运动控制 | 10 月 8 日源工程实现、配套包及同板推理/PWM 命令通过；序号拒绝、租约到期、STOP 已有板测 | 新绝对源期限 RTL、源时钟映射及故障实验；最终信号/机构验收 |
| 视觉采集与预览 | 真实相机、CPU YuNet 人脸、IoU/速度预测跟踪及 UI 预览；最新两次短测约 12.6—15.9 fps | 正式 DPU 人体链、ByteTrack、多人遮挡/重入精度与长期性能 |
| 今日 YOLO 工作 | 独立目录有官方 YOLOX-Nano 权重、模型属性和板端库检查；主仓新增模型专用适配源码 | 本轮读取时探针包仍在 staging，未找到推理结果；不计为真实检测/实时集成通过 |
| 身份 | YuNet/五点对齐/SFace 板端图片参考链；SQLite 身份库与软件合同已有实现/测试 | 登记、离开再识别、陌生人、删除、多目标绑定的实机闭环；正式配置仍 disabled |
| 汐蓝、音频输出、触屏 | GTK/GStreamer 缓存播放器、五页 UI、真实相机、暂停/继续/取消；基础手指滑块/页签有实测，最新五页有原生指针操作证据 | 全部新页面手指/边缘/多指；物理显示延迟、最新冷启动、长稳 |
| 真实语音与看图问答 | Windows 已有 Qwen3-TTS 选定声线、桌面演示与 ASR 等代码/历史记录；板端真实缓存播放通过；媒体合同和模拟流水线通过 | MCP01 真麦录音→Windows ASR/VLM/TTS→板端动态回答及取消/断网恢复 |
| 视觉说话人 | Light-ASD 接口/结果归属设计已有 | 模型接入、同步声画、多人判断/拒判实测 |
| 时效调度创新 | 固定/可变有效期、任务预算、结果归属及软件监督已有实现和模拟测试 | 标定数据、真实多任务 DPU 负载、新 PL 绝对源期限、G0—G5 基线/消融实验 |
| 机构 | 上电后 30.135 秒双向视觉命令 374/374 接受；用户曾反馈运动慢/幅度小；固定往返 616 条接受并 STOP | 3D 机构、正式零点/方向/角度/限位、准确机械随动及误差 |
| 交付复现 | 八模块图册、42 工作包映射、七类提交框架、环境检查与部分打包脚本 | 干净目录全量构建、统一发布工件、三个可复用技能包、独立人员复现及最终报告 |

## 关键证据与旧结论纠正

- [最新 UI 核验](/home/ghmd/aura-board-ui-design-20261009/validation_final.json) 为 PASS，范围明确是原生 UI、CPU 真实相机与缓存播放，不是整机验收。118 项主机框架及 60 项板端软件测试是该记录的范围；帧龄不是物理面板端到端延迟。
- [上电后视觉 trace 核验](/home/ghmd/kv260-adaptation-check-20261006/evidence/20261009T033432.902440Z-powered_follow_trace_export/HOST_TRACE_VERIFICATION.json)：374 条命令，中心 85、顺时针 121、逆时针 168，STOP 通过，mechanical_following_verified=false。早期“30 秒未通过”已经被后续命令测试更新，机械跟随验收仍不能升级为通过。
- [固定往返核验](/home/ghmd/kv260-adaptation-check-20261006/evidence/20261009T034221.835799Z-visible_sweep_trace_export/HOST_TRACE_VERIFICATION.json)：616 条、十段端点到达、端点保持和 STOP 通过；固定往返不等于视觉随动。
- [源平台实测](/home/ghmd/AMD_Smart/logs/daily/2026-10-08-VISUAL-SERVO-SOURCE-PLATFORM.md) 最终 WNS +0.001 ns，有外部约束缺项和参考优化告警；构建曾通过，但增加新监督逻辑仍需重新综合实现。
- [当前主仓配置](/home/ghmd/Win共享文件/共享文件夹/aura/config/runtime.kv260.json) 中正式检测入口/指纹未配置，identity/dialogue/motion 禁用；独立 UI 服务已上板不能自动更新这一统一配置的就绪程度。
- [现有 RTL](/home/ghmd/Win共享文件/共享文件夹/aura/hardware/rtl/visual_servo.sv) COMMIT 装入相对 lease；尚无源观测绝对期限监督。软件模型不能代替 PL 在 PS 停顿时独立执行的证据。
- [提交入口](/home/ghmd/Win共享文件/共享文件夹/aura/submission/aura_junior/README.md) 明确 FRAMEWORK_NOT_FINAL_COMPETITION_RELEASE；完整复建脚本仍受旧 cache/DCP/本机路径依赖限制。

## 本轮实际验证

在 `/home/ghmd/Win共享文件/共享文件夹/aura` 执行：

1. `python3 -B -s -m unittest discover -s tests/framework -q`：118 项，1.604 秒，OK，退出码 0。
2. `python3 -B -s tools/aura_project.py --config config/runtime.sim.json doctor`：退出码 0，两份 CPU 参考权重哈希通过。
3. 同入口 `--config config/runtime.kv260.json doctor`：退出码 2；本 Ubuntu Python 缺 NumPy/ByteTrack，配置指定的 person_detector.xmodel 不存在，DPU entrypoint/arch_fingerprint 未配置。不能据此断言目标板缺库，也不否认独立 YOLO 目录已有权重。
4. 今天 YOLO 已完成的 inspect/model_inspect/model_probe 三份 response.output 与记录长度/SHA 全部一致。model_probe 只读取模型属性和示例接口，未调用模型推理。后续 probe_stage 为 complete=false，另有分块文件，属于正在进行的工作。
5. 核对上述两份运动 trace 汇总与 CURRENT_CONTINUITY_TEST.json，区分命令连续性、现场反馈和机械验收。

核验脚本首次假定所有证据目录都有 response.output，在新 staging 目录报 FileNotFoundError；未影响工程或板卡。随后按证据格式区分，三份完整响应复核通过，未完成阶段如实保留。没有等待或干预正在进行的 YOLO 工作。

## 下一步建议（计划，不是已完成）

1. A 线继续完成 YOLO 固定图推理、实时人体框与时效/精度记录，再接正式跟踪和身份，统一相机所有权与应用配置。
2. 交互线并行做 MCP01 真实录音/停止/回放，接 Windows 动态问答；沿用已完成板端界面和声线。
3. 在固定期限基线上补齐 PL 源期限 ABI/RTL/仿真和同板验证，再测可变期限调度收益；不要提前宣称创新效果。
4. 把 UI、视觉、媒体和平台输入收敛成同一个 release，补最新冷启动、故障恢复与长稳。机构按已记录安排等待 3D 模型，独立数字工作继续。

本轮只新增此进度日志，未修改业务源码、配置、模型或已有发布包。竞赛定位采用已有本地方案，本轮未复核外部最新公告。
