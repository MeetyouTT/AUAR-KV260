# 来源和许可范围

工程源码来自队伍保存在 E 盘的 AURA 业务代码、Ubuntu 上的 wide FPGA、三模型调度、原生运行库与协作记录。build/reports/ubuntu_inputs.json、data/reference/additional_ubuntu_inputs.json、runtime_hashes.json、各技能的来源记录和总 checksums.sha256 可追溯到具体交付文件。历史工程的源树使用 Xilinx 命名惯例，第三方目录名、大小写与导入路径均按原件保留。

* AMD/Xilinx 的 DPU、Vivado 生成文件、XSA/固件、Xilinx IP 和板卡支持文件按各自工具与产品许可保留；工具链和整张 SD 映像由使用者按其授权准备。src/fpga/vendor 中的文件保留原始声明。
* 原生角色渲染所用上游及第三方 C++ 源许可随 src/avatar/native_integration/candidate_core/LICENSE、third_party_licenses 与来源清单保存，板端仍运行 AArch64 原生渲染器。角色模型、纹理和 EMS 资源的来源见 src/avatar/asset-provenance.json。工程中未找到可代表所有角色美术资产对公众授权再分发的文件；开放仓库前由队伍确认或替换这些资源。
* ByteTrack 的许可和固定来源位于 src/software/board/vision/bytetrack。Ruckig 的许可位于 src/motion。DroidSansFallbackFull 的声明见 licenses/font。通用 PYNQ 技能带有自己的许可文件。
* YOLOX 使用 KV260 映像中的部署工件，YuNet、SFace 与项目的公开量化、编译输入对应。ASR、VAD、ECAPA、OmniVoice 和 27B 依各上游模型及代码条款。板端外部包的前端许可文件随模型提供。各工件的固定版本和哈希以 models 的清单为依据。外部软件及权重未纳入团队统一授权。
* 设计报告、AI 协作记录、外部模型与角色资源的著作归属各自保留。工程归档未包含队伍已签发的统一公开源码许可或公开仓库地址。对外提交时，由权利人选定许可范围并填正式仓库信息。本次仅在用户两台工作机上整理和验证。
