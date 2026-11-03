# FPGA 全模型调度与 Windows 网线协同调研

日期：2026-10-12。

用户要求在线寻找“所有模型的调度在 FPGA 上，Windows 模型通过网线与板端协同加速”的具体论文/GitHub 方案。本轮按资料规则查看 ZIP 入口、当前方案与最新证据，并复核现有 DPU 调度、实际相机入口、Windows 对话绑定和请求参数。

## 完成内容

- 形成[详细研究与拟议实现](/home/ghmd/AMD_Smart/reviews/2026-10-12-FPGA-WINDOWS-MODEL-SCHEDULING-RESEARCH.md)：模型位置、PL 调度器接口、Windows worker 合同、网络成本、计算优化、实施步骤和独立消融。
- 搜索 Google Scholar/GitHub；Scholar 页面未能读取，转查作者全文、会议/出版方材料和官方仓库。
- 找到 RTAS 2026 多 DPU 论文的公开实验包，下载并检查真实源码。包含 Python/VART 调度、模型分块和响应时间分析；未发现 RTL 文件。更正“有实验包就能直接得到 PL 调度器”的潜在误解。
- 核对 FPGA EDF 调度论文、ARTICo³、Triton 资源限流、GLITCHES、Coyote、llama.cpp RPC、OmniVoice FlashInfer 与 Ollama 参数。
- 记录关键适配边界：GLITCHES 的多卡吞吐为仿真、网络扩展为未来工作；Coyote 面向 Alveo/Linux；FlashInfer 官方要求 Linux；这些均不是当前原生 Windows/KV260 的既成收益。

## 实际核验

- [归档与校验清单](/home/ghmd/AMD_Smart/data/research/2026-10-12-fpga-scheduling/manifest.json)：16,180,438 字节，109 条目，全部 ZIP CRC 通过，MD5 与 Zenodo 发布值一致；计算并保存 SHA-256。
- 阅读原包 README、MIT LICENSE 及两个 scheduler 源码的关键路径；保存原样参考副本，未执行第三方脚本。
- 用 Python 核算 1 Gb/s 理想发送时间：VGA BGR 7.3728 ms/帧；1080p BGR 49.7664 ms/帧、30 fps 1492.992 Mb/s；16 kHz 单声道 PCM16 0.256 Mb/s。均为理论计算，非实测。
- 本地代码证据：SingleCuScheduler 仍仅 detection/identity；实际相机服务直接实例化 DpuYoloX/PersonByteTracks；Windows 对话入口默认回环绑定，LLM 请求当前 `stream: false`。
- 第一次沙箱内下载连接失败；按权限机制升级重试成功，校验通过。
- 收尾检查通过：两份新增文档的本地链接均存在，归档 SHA-256 复核一致，保存的四份参考文件与 ZIP 内原件逐字节一致。

## 设计结论与待办

本轮用户明确要求研究 PL 全模型调度，因此提出：PL 执行准入和仲裁，PS/Windows 代理执行授权，DPU/ARM/Windows CPU/GPU 分资源池；模型权重常驻计算端。任务到期禁止消费结果，但不自动释放仍忙的资源。Windows 各模型需暴露独立阶段才能称为模型级统一调度。

建议先建立真实模型/资源成本表和统一 worker 合同，完成板端录音至 Windows 推理再回板播放及视觉并行的带日志软件对照；随后实现同策略 PL 原型与联合位流。第二 DPU 身份模型、OmniVoice 内核优化分别验证。

本轮只新增研究文档、归档/参考源码和日志，未改运行代码、配置、模型选择、Windows 环境或位流。未做推理、LAN 性能测量、RTL 仿真、板测及机构动作。所有性能收益仍待上述实验验证。
