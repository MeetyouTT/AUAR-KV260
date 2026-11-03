# KV260 审计交付物索引（DeepSeek）

> **本目录及其全部内容由 DeepSeek 完成**（只读取证 + Vivado 只读对象查询 + 分析与撰写）。
> 生成时间：2026-09-26 22:34（本机本地时间）｜来源：`/home/ghmd/kv260_full_image_audit_20260926/`（原始诊断目录，内容完全相同）

## 主要交付物

| 文件 | 内容 | 行数/大小 |
|---|---|---|
| `SUMMARY_DEEPSEEK.md` | **摘要（建议先读）**：一句话结论、reset 差异分阶段证据链、产物与来源链、官方镜像结论、可上板性判定、least-effort 补证清单 | 86 行 / 7.6 KB |
| `REPORT.md` | **完整审计报告**：摘要、命令与只读性、A 文件与来源清单、B 官方配套镜像、C 逐项对比、D reset 网表差异与阶段定位、E 板端只读取证、根因候选、最少补证、最终结论、附录 | 326 行 / 43 KB |
| `COMMANDS.txt` | 本轮运行过的全部命令（标注只读性；含 3 个 Vivado 只读查询脚本的调用方式） | 77 行 |
| `SHA256SUMS.txt` | 本目录全部文件（含 `logs/`、`extract/`、`reports/` 与本索引）的 SHA256，共 78 项，`sha256sum -c` 全通过 | 78 行 |

## 证据目录

- `reports/`：结构化查询结果（新旧 routed DCP 查询、IP OOC 拓扑、opt 阶段定位、悬空集合比对结论、本机哈希清单）
- `logs/`：Vivado 原始日志（3 次只读查询的 `.log/.jou/.stdout`）、shell 采证输出、串口被动采样记录
- `extract/`：证据摘录（BD/综合 HDL 行段、IP sim_netlist 上下文、IP changelog、加密检查、启动日志关键行、0 字节串口原始文件）
- `query_*.tcl`：3 个只读查询脚本（`open_checkpoint`/`open_project` 后仅读取对象属性，不写回）

## 复核方式（只读，可重放）

```bash
cd <本目录>
sha256sum -c SHA256SUMS.txt          # 校验全部 76 项证据文件
less SUMMARY_DEEPSEEK.md             # 先读摘要
less REPORT.md                       # 再读完整报告
cat COMMANDS.txt                     # 查看为每个结论运行的原始命令
```

## 边界声明（重要）

- 全程只读：未修改源工程/BD/XPR/模型/镜像/设备树/驱动/板卡配置；未烧写、未加载 bitstream、未复位、未写寄存器、未加载模块；未下载镜像。
- 串口仅一次**被动**采样：`timeout 5 cat /dev/ttyUSB{0,1}`，**0 字节，未写入任何字节**。
- 结论核心：**routed DCP 中 DPU 两路 reset 的 `IS_CONNECTED=0` 已定位为"IP 交付物内部不使用该输入 → 无负载网在 `opt_design` 被清理"，新（9/26）旧（9/19）两代实现逐名完全一致（196/196 `IDENTICAL_SET`），不是本次重建的回归**；但当前 bit/XSA 仍判定为**不可确认可上板（保守：不可上板）**，理由与 reset 无关，详见 `SUMMARY_DEEPSEEK.md` 第 5 节。

---

> 本文件由 **DeepSeek** 生成。
