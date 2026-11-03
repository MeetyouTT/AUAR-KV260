# M3 最小寄存器合同

目标：在沿用已验证 DPU 4.1 B4096 配置的同一 PL 配置中，加入自研 AXI-Lite 寄存器。此版没有 PWM、运动控制、外部输出或中断。

候选地址窗口 `0x80080000–0x80080fff`，接在 `PS_0/M_AXI_HPM0_LPD → axi_ic_ctrl_100/M06_AXI → aura_m3_regs_0/S_AXI`；沿用 `clk_wiz_0/clk_100M` 和 `proc_sys_reset_100MHz/peripheral_aresetn`。该参考时钟名义为 100 MHz，BD 实际为 99.999 MHz；模块跟随源时钟传播频率，不强制覆盖源时钟属性。最终冻结地址必须以新 link HWH 和实际板端访问核验为准。

| 偏移 | 寄存器 | 访问 | 含义 |
|---|---|---|---|
| `0x00` | IP_ID | RO | 固定 `0x41555241`（AURA）。 |
| `0x04` | ABI_VERSION | RO | `0x00010000`，主版本 1、次版本 0。 |
| `0x08` | BUILD_ID | RO | 源码与配置摘要的前 32 位；完整摘要在 `evidence/build_identity.json`。 |
| `0x0c` | SCRATCH | RW | 复位为 0，支持 WSTRB 逐字节写入；只用于受控读写核验。 |

访问为 32 位、4 字节对齐。保留偏移、非对齐地址的读返回 0 和 SLVERR；对只读寄存器或保留偏移写入返回 SLVERR，状态不变。零 WSTRB 的合法 SCRATCH 写入返回 OKAY，数据不变。写地址和写数据独立接收，均收到后提交；读写响应在反压期间保持稳定。读写 SCRATCH 同拍时，读取得更新前的值。

同步低有效复位清除 pending、响应和 SCRATCH；只读身份常量不变。当前不根据 AWPROT/ARPROT 设置额外访问策略，上层访问权限需由 Linux 和访问程序管理。

BUILD_ID 标识该最小模块及所记录配置的源码版本，不是整个 BIT 的 SHA-256，也不能替代完整工件校验。修改源码后须重新生成身份并重建。

## 构建和验收顺序

1. `bash run_m3_build.sh ip`：生成身份、打包自研 IP、进行最小 OOC 综合。
2. `bash run_m3_build.sh platform`：在独立工程生成包含 M3 模块的新平台 XSA/XPFM。
3. `bash run_m3_build.sh overlay`：使用该新平台连接原配置 DPU，生成完整新硬件。
4. 从最终 routed DCP 审阅实际资源、时序和 DRC；核对 HWH、地址、架构与运行包的一致性。
5. 新工件审阅后，在独立测试卡验证身份、SCRATCH 访问与同模型同图片的 DPU 推理，保存并恢复对照。

本地综合与构建通过不等于 M3 已在板端通过。板端访问工具、设备树/映射方式需在最终地址与目标 Linux 能力确认后冻结。AXI 协议行为尚未经过专门仿真，不以综合通过代替协议验收。

协议及封装资料：[ARM AXI 规范](https://documentation-service.arm.com/static/67ab5a186dbc975ccea91734)、[AMD 2022.2 IP 接口封装](https://docs.amd.com/r/2022.2-English/ug1118-vivado-creating-packaging-custom-ip/Using-a-New-Interface-Definition)。
