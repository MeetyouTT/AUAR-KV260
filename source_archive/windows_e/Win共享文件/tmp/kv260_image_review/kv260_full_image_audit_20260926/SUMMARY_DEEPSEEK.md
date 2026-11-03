# KV260 ResNet50 审计结果摘要（DeepSeek 版）

> **作者：DeepSeek**（本文件与同目录 `REPORT.md` 均由 DeepSeek 完成：只读取证 + Vivado 只读对象查询 + 分析与判定）
> 完成时间：2026-09-26 22:20（本机本地时间）
> 完整版：`REPORT.md`（318 行）｜命令清单：`COMMANDS.txt`｜哈希清单：`SHA256SUMS.txt`（74 项，`sha256sum -c` 全通过）
> 操作边界：全程只读。未修改源工程/BD/模型/镜像/设备树/驱动/板卡配置；未烧写、未加载 bitstream、未复位、未写寄存器；未下载镜像；串口仅做一次被动采样（**0 字节，未写入任何字节**）。

---

## 1. 一句话结论

**你要求优先复核的 "routed DCP 里 DPU reset pin `IS_CONNECTED=0` 而 HWH 仍称已连接"，已被定位为"IP 交付物内部不使用该输入 → 无负载网在 `opt_design` 被清理"的既有现象，新（9/26）旧（9/19）两代实现逐名完全一致，不是本次重建引入的回归、也不是实现断线事故。但当前 bit/XSA 仍判定为不可上板，理由与 reset 无关（见第 5 节）。**

---

## 2. reset 差异：分阶段证据链（可直接复核）

| 阶段 | 证据 | 观测 |
|---|---|---|
| IP 明文 wrapper RTL | `kv260_dpu.gen/…/ip/kv260_dpu_bd_dpu_0_0/synth/kv260_dpu_bd_dpu_0_0.sv:703,705` | `.dpu_2x_resetn(dpu_2x_resetn)`、`.m_axi_dpu_aresetn(m_axi_dpu_aresetn)` 传递正常 |
| IP 核心 RTL | `hdl/DPUCZDX8G_v4_1_0_vl_top.sv`、`inc/arch_para.vh` | IEEE-1735 密文，**不可读**（这就是"IP 内部为何不用该 reset"无法确认的原因） |
| BD 生成 HDL | `kv260_dpu.gen/…/synth/kv260_dpu_bd.v:689,691,819-832` | 两路 reset 接到 `rst_dpu_dsp`/`rst_dpu_clk` 输出（连接**存在**） |
| BD HWH | `…/hw_handoff/kv260_dpu_bd.hwh` = `0fed493c…` | 仍描述两路 reset 连到 DPU |
| **IP OOC DCP（新 9/26）** | `reports/ip_ooc_and_new_routed_reset_topology.txt:1-18` | IP 顶层两路 reset 端口 `FANOUT=0`；`inst/dpu_2x_resetn`、`inst/m_axi_dpu_aresetn` → 常量网 `<const0>`；`s_axi_aresetn` 正常；`RESET_PIN_TOTAL=44 CONNECTED=44 CONST_TIED=2` |
| **IP OOC DCP（旧 9/19）** | 同上 `:44-61` | 与新版**逐字段相同** |
| IP 单独综合日志 | `…/kv260_dpu_bd_dpu_0_0_synth_1/runme.log` | `dpu_2x_resetn`/`m_axi_dpu_aresetn` 相关行 **0 条**；`8-7129` 共 103/104 条全部为 `regs4.prof_value` → 不是"漏连告警" |
| top 综合 | synth 日志 `:51-57,69-79` | `Synth 8-7071` 的 `dpu_0` 悬空端口清单**不含**这两路 reset → 外部连接确实进入了综合 |
| top synth DCP | `reports/synth_dpu_reset_connectivity.txt` | `dpu_0/dpu_2x_resetn` `IS_CONNECTED=1`，但 `inst/dpu_2x_resetn` 已是 `<const0>` |
| **impl `opt_design`（阶段定位）** | `reports/opt_stage_and_orig_dangling.txt`、`impl_1/runme.log:124,132,139` | `*_opt.dcp` 中两路 reset 已 `IS_CONNECTED=0`、`OPT_RST_DPU_DSP_CELL_COUNT=0`、`NET_COUNT=0`；常量传播移除 1575 cells、Sweep 移除 1246 cells → **`IS_CONNECTED` 由 1 变 0 发生在 `opt_design`** |
| routed DCP | `reports/final_routed_reset_gate.txt` | 两路 reset `IS_CONNECTED=0`；`rst_dpu_clk_peripheral_aresetn` fanout=2（仅 reset controller 输出 + `axi_mem_intercon_2/S00_ARESETN`） |
| **新旧对照（最强证据）** | `logs/dangling_set_compare2.txt` | 旧 routed 与新 routed 的 DPU 顶层悬空输入**各 196 个、逐名 `IDENTICAL_SET`**，集合内即含 `dpu_2x_resetn`、`m_axi_dpu_aresetn` |

**结论**：不能把 `IS_CONNECTED=0` 当作"器件内断线/被永久复位"的证据，也不能把 HWH 连线当作 routed connectivity；二者是不同抽象层的正确表述。**禁止**据此判定新 bit 损坏。

---

## 3. 本机产物与来源链（已确认）

- **新重建（2026-09-26）**：bit `d316ee9c…385c` = XSA 内嵌 bit；XSA `76e8d105…363b`；routed DCP `23d16616…9fbd`；synth DCP `87e79b44…6dc4`；HWH `0fed493c…4c63` = XSA 内嵌 HWH；arch.json `ac3853f7…7bdd`（`fingerprint 0x101000056010405`）。链条**无断裂**。
- **旧交付物**：`images/linux/system.bit` = `6a75e223…4aba5`（旧 100 MHz bit），而旧 XSA `08abccc5…` 内的 HWH `ea48b3a0…` 描述的是含 clock wizard 的 BD → **bit 与 HWH/DTB 不同源**（已确认的既存缺陷）。新 clockfix bit **尚未进入启动链**。
- **时钟**：新实现 `clk_dsp` 5.000 ns（200 MHz）、`dpu_clk_wiz_clk_dpu` 10.000 ns（100 MHz），WNS 1.462/3.284 ns，post-route 无违例；旧实现两路都是 `clk_pl_0`（100 MHz）。
- **IP**：DPUCZDX8G v4.1（changelog：`2022.2 / v4.1 / Vitis AI v3.0`），`SYS_IP_VER=0x41`、`GIT_COMMIT_ID=0x07d32c41`。
- **模型/输入**：`resnet50_b2304.xmodel` = `acf77c7f…4def7c`（与提示词中"旧硬件模型"同 SHA）；`cat2.jpg` `03259f0b…`、`input.bin` `46c4aacd…`。

## 4. 官方配套镜像（B 节）

- 本机**没有**任何 AMD 官方 KV260 板级镜像（无 `*.img/*.img.xz/*.wic`）→ **无法做逐字节比对**。
- 官方来源确认：Vitis AI **3.0** 支持 KV260；官方配套镜像名 **`xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz`**（官方要求板级镜像 ≥2022.2）；官方模型包 `resnet50-zcu102_zcu104_kv260-r3.0.0.tar.gz`；官方 GitHub tag `v3.0` 存在。
- 本机仅有的相关物：`Vitis-AI-3.0.zip`（源码，`vitis-ai-source` 副本无 `.git`）、开发容器 `xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106`（**不是**板端镜像）。
- 判定：**版本号层面一致（已确认）／文件层面未比对（未确认）**。

## 5. 可上板性判定

**不可确认可上板（保守结论：不可上板）**，理由：

1. U1：IP 加密核内部为何不使用这两路 reset（复位来源未知）；
2. U2：实际 bitstream 中该输入的 tie 值未取证；
3. U3：板上实际加载的 bit/镜像无哈希读回（既有日志只记录路径；本轮串口 0 字节）；
4. U5：342 条 post-route DRC warning（REQP-1731×288、AVAL-318×48、PDCN-1569×3、DPOP-3/4、RTSTAT-10）未 waiver；
5. 本轮无任何板端功能验收；交付链本身存在 bit↔HWH/DTB 的既存错配。

**注意**：该判定**不再**以"reset 断连"为依据；reset 差异已降级为"已解释的既有现象"。

## 6. 最少只读补证（不动板卡配置）

1. 板端只读一次：`fpga_manager` 状态、`/dev/dpu`、`dmesg | grep -iE 'dpu|fpga|deferred|iommu'`、`vart_version`、`lsmod`+`modinfo`（`vermagic`）、板上 bit/模型/输入 `sha256sum`、`libvart*`/`libxir*` 的 `SONAME`/`build-id`。
2. 官方 `xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz` 及其校验值 + 官方 DPU 参考设计 XSA。
3. AMD 官方 DPUCZDX8G v4.1 文档中 `dpu_2x_resetn`/`m_axi_dpu_aresetn` 的连接语义（回答 U1）。
4. 只读解析 xmodel 元数据，确认其 DPU arch 与 fingerprint `0x101000056010405` 一致。

---

## 7. 附：本摘要涉及的关键哈希

| 对象 | SHA256（前缀） |
|---|---|
| 本摘要 `SUMMARY_DEEPSEEK.md` | 见 `SHA256SUMS.txt` |
| `REPORT.md`（含 DeepSeek 署名，完整版） | 见 `SHA256SUMS.txt` |
| 新 bit | `d316ee9c33bae954…` |
| 新 XSA | `76e8d1056949999e…` |
| 新 routed DCP | `23d166161b9efc33…` |
| IP OOC 拓扑查询结果 | `81ea786422326905…` |
| opt 阶段定位结果 | `45d02862aa3b3cd1…` |
| 新旧悬空集合比对 | `f66fa99e07782bbc…` |

> 本文件由 **DeepSeek** 生成；如需与完整版对照，请阅读同目录 `REPORT.md`。所有结论均可用 `COMMANDS.txt` 中的只读命令重放，并可用 `SHA256SUMS.txt` 校验证据文件。
