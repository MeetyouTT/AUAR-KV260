# KV260 FPGA 开发环境现状核验

日期：2026-10-04。用户要求先确认 FPGA 环境是否完成，再确定下一步。本轮先读项目 ZIP 的 README、FPGA 框架/开工步骤、当前有效分工与最新实际记录，再在独立目录实际启动工具和检查已有工件。

## 结果

**当前 KV260/K26 的核心 FPGA 开发环境已就绪，可以从已有 M3 工程继续开发运动硬件。** 现有工具具备本轮实际验证的能力；完整 PWM、运动监督及最终联合平台仍未完成。

| 检查项 | 当前实际结果 |
| --- | --- |
| Vivado | v2022.2，SW Build 3671981、IP Build 3669848；当前启动返回 0 |
| Vitis 编译器 | v++ v2022.2，SW Build 3671529；当前启动返回 0 |
| Vitis HLS | v2022.2，SW Build 3670227；版本检查返回 0 |
| K26 器件 | `xck26-sfvc784-2LV-c` 当前查询成功 |
| KV260 板卡定义 | `xilinx.com:kv260_som:part0:1.4` 当前查询成功 |
| Clocking Wizard | 在新的独立工程中创建并生成输出产品成功；之前的速度模型查询问题本次未重现 |
| 当前综合能力 | 读取原 M3 RTL，在 K26 上实际 OOC 综合成功，54 LUT、118 FF；日志确认取得 Synthesis/device 授权，随后正常释放 |
| XSCT/HSI | `xsct -nodisp` 实际打开原联合 XSA，读出 175 个 cell，返回 0 |
| PetaLinux | 2022.2 环境加载和自带环境检查通过，build/config 入口可见 |
| 主机依赖 | build-essential、flex、bison、libssl-dev、git、python3 均为 install ok installed |
| 原硬件工件 | 11 项工件 SHA-256/大小全部通过，包括 BIT、BIN、XSA、XCLBIN、HWH、arch.json、routed DCP 等 |
| 原工程输入 | 11 项源码/配置 SHA-256 全部与原构建身份一致；核验前后均通过 |

独立主机回读：[64 项检查全部通过](/home/ghmd/kv260-fpga-environment-review-20261004/reviews/20261004T113221.737583Z/review.json)。本轮综合日志没有 ERROR 或 CRITICAL WARNING；普通工具/板卡定义及未使用 AXI 保护字段等 Warning 保留于完整日志。

主机有 18 个逻辑 CPU、约 30.8 GiB RAM，核验时工作文件系统空闲约 110 GiB。空间数字是本次快照，不保证后续任意并行完整构建的容量。

结构化状态见 [FPGA_ENVIRONMENT_STATUS.json](FPGA_ENVIRONMENT_STATUS.json)。

## 已有工程成果与当前边界

已有原样官方参考 platform/overlay 构建成功记录，见 [参考平台报告](/home/ghmd/kv260-reference-2022.2-20260930/REPORT.md)。已有 DPU 4.1 B4096＋M3 最小 AXI-Lite 联合工程完整实现与位流，见 [M3 构建报告](/home/ghmd/kv260-m3-axilite-20261002/M3_BUILD_REPORT.md)。

M3 实际包含 IP_ID、ABI_VERSION、BUILD_ID、SCRATCH；历史板测已经验证寄存器读写及同配置 DPU 原图推理，见 [M3 板测报告](/home/ghmd/kv260-m3-boardtest-20261002/M3_BOARD_REPORT.md)。不能将这四个寄存器的通过扩展为完整 PWM、停止/超时监督或三人业务验收。

最新板卡冷启动验收激活的是官方 benchmark，当前修复运行时及原图推理通过；本轮环境核验没有再次连接板卡、切换 PL 或重新验收 M3。最新 NFS/运行时状态见 [冷启动报告](/home/ghmd/kv260-platform-warnings-20261004/NFS_REPAIR_REPORT.md)。

现有 M3 完整 routed 设计仍有以下实际记录：

- 最差 setup/hold 余量均为 **+0.009 ns**；缺输入延迟 7 个端口、缺输出延迟 9 个端口。
- 已占用 CLB site 为 **99.45%**，LUT 为 **60.23%**。两者统计含义分别保留；新增运动逻辑的布局可行性需通过新的联合实现证明。
- 当前为完整静态 PL 配置。后续运动硬件需要与 DPU 一同形成匹配位流、XSA、HWH、XCLBIN/DTBO 和部署描述。

这些属于工程实现和交付工作。本轮不修改原约束或 RTL，也未执行完整 platform/overlay 重建、完整 PetaLinux 镜像构建或新一轮 AXI 协议/波形测试。匹配最终 rootfs 的 SDK/sysroot 与 B/C 应用依赖仍需随最终平台验收。

本轮 Clocking Wizard 检查覆盖主机 IP 生成。板端 DisplayPort 时钟权限和 overlay 属性生命周期问题仍在 [平台告警方案](/home/ghmd/kv260-platform-warnings-20261004/WARNING_REPAIR_PLAN.md) 中跟踪；本轮没有修复这些内核/设备树问题。

## 下一步先做什么

**第一项：冻结运动接口和实际 PWM/停止引脚约束。** 在已有 M3 的 AXI 接入基础上，明确运动 ABI、命令提交/接受/拒绝、禁能/超时/停止/恢复语义，并核对实际载板、接线、引脚与电气参数。M3 的 `0x0c` 为 SCRATCH，完整运动地址和含义需独立冻结。

随后按顺序推进：

1. 实现 PWM 与命令监督 RTL，完成相应仿真，记录周期/边界更新、过期和停止/恢复行为。
2. 从保留的 M3 基线派生独立候选，与原 DPU 一同综合、布局、布线；补齐新增引脚与实际接口约束，并检查资源、时序和 DRC。
3. 形成同一构建的匹配部署包，按现有可恢复流程上板。先验收无动力 PWM/停止波形与同配置 DPU 原图推理，再接 B 的唯一运动服务和执行器。

本轮仅给出下一阶段步骤，未把计划记为已经实现。

## 环境入口与核验失败记录

本轮默认命令环境的 PATH 中没有工具命令，是尚未加载设置脚本。本轮每次在独立子进程加载实际安装入口，未修改 `.bashrc` 等全局配置。

硬件开发终端：

```bash
source /home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh
vivado -version
v++ --version
```

Linux 构建使用另一终端加载 PetaLinux：

```bash
source /home/ghmd/petalinux/2022.2/settings.sh
```

PetaLinux 自带检查仍提示未发现 TFTP server。本项目当前采用已实测的 SD 启动；本轮未配置或验收 TFTP 启动。

保留两次 PetaLinux 核查脚本失败：

1. v1 的 source 包装继承了调用参数，PetaLinux 将第一个参数 settings.sh 文件误作安装目录，返回 126。修改核查脚本为 source 前清空位置参数；安装入口内容未改动。
2. v2 的环境检查已返回 0，后续核查错误地读取 `PETALINUX_BASE_VER`，得到 null。实际入口导出的是 `PETALINUX_VER`；v3 使用正确变量后全部通过。

三版控制器和失败目录均保存；没有在长时运行的控制器上在线修改代码。独立主机核验确认原 11 项工件、11 项源码/配置和四个安装设置脚本 SHA-256 保持一致。本轮新增核查脚本、报告和项目日志；原 FPGA 工程、安装、板端及前轮封存包保持原样。
