# KV260 M3：DPU 与最小自研寄存器共存

这是独立的硬件派生工程，目录 `/home/ghmd/kv260-m3-axilite-20261002`。目标是在同一份 PL 配置中加入最小 AXI-Lite 寄存器，保留此前验证过的官方 DPU 4.1 B4096 配置与模型要求。Linux/PetaLinux 镜像沿用已有测试卡。

## 本轮改动

- 新增 `rtl/aura_m3_regs.v`：三个只读身份寄存器与一个 SCRATCH，无外部输出。
- 新增 IP 打包、源码身份、连接和 routed 审阅脚本，以及分阶段执行入口。
- 仅在独立克隆的参考平台 `scripts/main.tcl` 中加载本地 IP 仓库与连接脚本；原 `config_bd.tcl`、厂商规则和原工程保持。
- 保留已验证独立 DPU 4.1 工程的四项兼容性改动，记录于 `evidence/inherited_dpu41_changes.patch`。

## 构建入口

```bash
python3 scripts/run_phase.py ip
python3 scripts/run_phase.py platform
python3 scripts/run_phase.py overlay
python3 scripts/run_phase.py review
```

每次执行单独保存 `logs/<phase>_<attempt>/console.log` 和 `result.json`，记录起止 UTC 与实际返回码。修复后的运行器还保存并执行入口快照及其 SHA-256，工程根目录只在子进程环境中指定。运行中的状态不能解释为完成。

平台生成 XSA/XPFM；overlay 阶段生成包含 DPU 与 M3 的完整硬件。这个流程不调用 `petalinux-build`，也不制作或写入 SD/QSPI 镜像。

## 现有证据

源码 commit 为 `a3a83f179503792226adf83082aee7c05de620b4`。此前已验证工程为 `/home/ghmd/kv260-dpu41-control-20261001`，保留原成果与板端对照。

M3 IP 打包、平台与联合实现已完成，窗口为 `0x80080000–0x80080fff`。OOC 为 54 LUT、118 FF；最终 M3 层级为 50 LUT、118 FF、22 个实际 SLICE site，BRAM/URAM/DSP 均为 0。

最终 setup / hold / pulse-width 余量为 +0.009 / +0.009 / +0.071 ns，内部未约束端点与布线错误均为 0，621 个实际 DRC 对象均为 Warning，实际 HDPR-5 为 0。DPU 全部 91 个参数、架构指纹和内存连接与已验证父工程一致。11 项新工件哈希核验通过，见 [M3_BUILD_REPORT.md](M3_BUILD_REPORT.md) 与 [artifacts.json](evidence/artifacts.json)。

完整 I/O 约束覆盖仍未通过：原参考平台有 7 个输入、9 个输出缺少延迟约束。M3 板端寄存器访问、同配置 DPU 推理、专门 AXI 协议仿真及 M3 运行 bundle 均未完成；本次通过的是主机端已覆盖路径和元数据审阅。

首轮打包的重复地址块、首轮平台检查的 100 MHz 与 99.999 MHz 频率声明不匹配已定位并修复，只修改自研模块的封装。历史日志和生成文件分别保存在 `evidence/ip_attempt01/`、`evidence/ip_attempt02/`、`evidence/platform_attempt01/`。参考工具中已有的 `too many nested evaluations` 提示保留，原参考成功构建日志中也有同样提示，不能混同为本轮模块的失败位置。

详细寄存器行为见 [M3_REGISTER_CONTRACT.md](docs/M3_REGISTER_CONTRACT.md)。实际构建阶段记录在 `logs/`；源文件身份在 `evidence/build_identity.json`；地址和连接记录在 `evidence/m3_platform_addresses.txt` 与 `evidence/m3_platform_connections.txt`。

联合实现后入口报错的 `overlay_01` 和汇总输入缺失的 `review_01` 真实失败记录保留；固定入口快照后的 `overlay_02`、补提历史内存拓扑后的 `review-finalize_01` 均返回 0。`review-finalize` 是已有 routed 报告完整时的汇总恢复入口，不替代首次 `review`。

本轮没有执行板端加载、重启、烧录或连接执行器。OOC 综合、平台连接检查与主机构建均不能替代实际板端验证。
