# 板端实时 DPU 接入与音频恢复

更新：2026-10-22（洛杉矶00:25后，UTC07:25后）。**YuNet DPU已通过30分钟实时检查并保留；SFace又通过真人三模型DPU影子短测，测试后恢复到YOLO＋YuNet常驻。SFace正式身份后端仍配置Windows CPU。** 真人短测完成10次SFace特征计算，平均14.48ms，YOLO10.04Hz/YuNet2.15Hz；没有用影子结果判定身份或写入登记库。MCP01本次播放告警在正常重开原应用后消失，初次触发根因仍未确定。机器可读状态见[release.json](release.json)。

| 指标 | 音频恢复后的原配置 | YuNet DPU配置 |
| --- | --- | --- |
| CPU四核总占用，约15秒窗口 | 63.28% | 首段55.09%、后段52.99% |
| XRT DPU任务忙时，约15秒窗口 | 4.13% | 首段4.66%、后段4.80% |
| YOLO / YuNet实时速率 | 原配置YOLO约9.89Hz | 30分钟平均9.95 / 2.37Hz |
| 持续检查 | 短时基线 | 30分钟、360次健康采样、CPU整段53.93% |

实时画面和有效人脸处理频率非严格匹配，不能将CPU差值全部归为DPU硬件加速。30分钟无USB告警、无YuNet真正超限/CPU回退；有1次YOLO周期超时记录、1次YuNet超过20ms初始估计但在实际截止前完成（最大22.07ms）。没有把“无YuNet回退”写成全链零超时。主检测帧龄健康采样中位106ms/P95=160ms/P99=184ms/最大191ms，这些不是逐帧完整分布。

- [实际操作、性能窗口与限制](实时实施_音频恢复与YuNet.md)
- [SFace真人三模型影子短测、自动恢复与证据范围](SFace_真人影子短测.md)
- [交付文件、冻结候选、语法及引用核验](evidence/final-delivery-validation.json)
- [后续顺序与恢复前状态](下一阶段计划与现状.md)
- [SFace版本隔离候选、21项回归与接入说明](sface-candidate/README.md)
- [MCP01驱动机制审查、最小恢复候选及12项模拟](audio-recovery/audit/USB_AUDIO_AUDIT.md)
- [首轮模型适配、公开精度与固定输入实板对照](../2026-10-21_dpu_vision_start/README.md)

本轮生产操作集中在Ubuntu主任务：一次空闲界面服务正常重启，以及隔离相机目录内的YuNet DPU试运行。另一个Codex只准备SFace候选/测试，独立审查任务只读本机源码，不并发操作UART/生产。原始UART、图像、音频、特征和身份库没有复制到此目录；Windows同步与独立回执尚未确认。

SFace当前仍配置Windows CPU业务后端，本轮8792 TCP/health超时，不能据此判定Windows服务已停止。直接候选的新INT8库与原FP32库严格隔离，阈值留空阻止直接启用；21项软件回归和最新板上纯配置检查通过，见[sface-final-configcheck-note.json](sface-final-configcheck-note.json)。另一个影子候选16项回归、部署准备3项本地检查通过，已实板执行真人短测：20秒、10次完成/10次通过目标与时效复核、0计算失败/0 USB告警，始终不发布身份、不写库。`compare_cosine=false`，没有同图FP32余弦对照或现场识别精度结果。短测按预案自动恢复，当前不常驻影子计算；后续仍需独立INT8登记/现场阈值及较长三模型观察。

当前CPU仍负责采集、图像转换、跟踪、YuNet解码、脸部对齐、身份模板比对、界面和录放音；DPU承担YOLO与YuNet的CNN。使用单进程共享owner、YOLO优先、可选任务预算与过期丢弃，保持原身份库与Windows回退。

新相机根：`/home/root/aura-dpu-vision-20261021/runtime/81fdb11903abb71e-live-134783/aura`，影子短测恢复后相机PID165277，原界面主PID131932与Xserver1077保持。最终模型/manifest/6源码SHA、运行后端、旧数据库路径、影子关闭、统计关闭和定时器停止见[活动配置审计](evidence/active-release-audit.json)。30分钟观察结束时的PID134844审计另存为[短测前审计](evidence/active-release-audit-pre-shadow.json)。现场识别精度、SFace正式身份业务、冷启动及更长三模型运行仍未验收。板端该目录上级的`rollback.py`用于从本轮YuNet候选退回最初CPU相机；SFace试验使用自己的rollback恢复到保留的YuNet配置，两者不要混用。

后续展示将区分：CPU四核总占用、XRT任务忙时、完整路径时延/有效吞吐/帧龄、识别精度，以及FPGA静态资源。当前相机配置请求30Hz，但实得约12.5Hz；不能把配置频率写成实测帧率。软件调度也不等于新增自研PL仲裁硬件。
