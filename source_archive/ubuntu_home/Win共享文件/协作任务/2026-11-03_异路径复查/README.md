# 工程包在本机不同路径复查

**后续空间状态更新：** 用户授权清理后，已从 RAR 恢复一份约36GB异常膨胀的旧解压报告，释放33.626GiB，当前分区可用约34.389GiB。三个正式RAR保持原SHA，新的异路径构建仍未执行。详见[清理结果](../2026-11-03_磁盘清理/README.md)。下文786MB为清理前的检查快照。

可以在同一台电脑的全新目录完成第一轮复查。应从最终 RAR 重新解压，只使用解压后的源码和包内构建入口，输出放在源码之外的全新目录。这能检查对原工程路径和旧构建结果的依赖；同机仍共享已安装工具、IP 和许可证，因此不等于全新电脑的环境验证。

## 本轮已核对的实际状态

- 本机最新角色素材版：`/home/ghmd/下载/AUAR_角色素材补全_9a4f_20261103/auar_xuefei_character_enhanced.rar`。
- 实读大小 59,110,767 字节，SHA-256 `f4712f0d2b52ab4003f0f0e2362b4ac8947cb90865e798f1e99c466c0f562949`，与既有归档回执一致。
- 当前已解压树执行 `sha256sum --quiet -c checksums.sha256`，退出码 0；清单覆盖 1757 项。
- 实际工具为 Vivado 2022.2，SW Build 3671981、IP Build 3669848；本机 Vitis `2022.2/data/ip` 目录存在。
- `build/reproduce.py --help` 返回 0。检查入口源码确认：它实际调用 Vivado 和 Tcl；RTL 回执绑定源码指纹，硬件输出要求在源码树之外，已有阶段日志或回执拒绝覆盖。
- 检查 `build/build.tcl`、`build/reproduce.py` 和 `src/fpga` 的 Tcl：未发现 `/home/` 或 Windows 盘符绝对路径；`read_checkpoint` 仅见“不使用旧检查点”的注释，实现后打开的是本轮新生成的检查点。
- 检查时 `/home/ghmd` 所在分区只剩约 786 MB，`/tmp` 在同一分区。因此本轮没有启动新的 RTL、综合实现或异路径完整重建，也没有访问实板。

## 先准备空间和目录

完整构建建议预留至少 20 GB 可用空间。这个数是操作留量建议，不是脚本声明的最低要求。当前分区空间不足，先自行腾出空间，或者把源码和输出放在另一块实际挂载且空间充足的磁盘；仅在同一分区换目录不会增加空间。

下面按当前 Ubuntu 环境写。Windows 原生命令及工具适配尚未在本轮验证。

腾出足够空间后，用归档管理器将最终 RAR 重新解压，使目录如下；不要把旧 `.runs`、`.cache`、`.Xil` 或旧输出拷入新目录：

```text
/home/ghmd/auar_review_01/
  src/auar_xuefei/       # 从最终 RAR 重新解压
  out/                  # 事先不要创建，由脚本生成
```

若改用其他磁盘，下面的源码路径和 `AUAR_OUT` 一起改成实际路径。重复整轮验证时，换用 `auar_review_02` 等新目录，保留前一轮日志。

## 分阶段验证，推荐使用

在 Ubuntu 终端执行，先检查文件和工具，再依次运行三个阶段。每一步通过后再执行下一步：

```sh
cd /home/ghmd/auar_review_01/src/auar_xuefei
sha256sum --quiet -c checksums.sha256

export AUAR_VIVADO=/home/ghmd/Xilinx_2022.2/Vivado/2022.2/bin/vivado
export AUAR_VITIS=/home/ghmd/Xilinx_2022.2/Vitis/2022.2
export AUAR_OUT=/home/ghmd/auar_review_01/out

"$AUAR_VIVADO" -version
df -h /home/ghmd/auar_review_01

python3 -B build/reproduce.py --out "$AUAR_OUT" --stage rtl --vivado "$AUAR_VIVADO"

python3 -B build/reproduce.py --out "$AUAR_OUT" --stage prepare \
  --vivado "$AUAR_VIVADO" --vitis-root "$AUAR_VITIS" \
  --rtl-results "$AUAR_OUT/rtl/result.json"

python3 -B build/reproduce.py --out "$AUAR_OUT" --stage implement \
  --vivado "$AUAR_VIVADO" --vitis-root "$AUAR_VITIS" \
  --rtl-results "$AUAR_OUT/rtl/result.json"
```

| 阶段 | 验证范围 | 本轮通过证据 |
| --- | --- | --- |
| `rtl` | 四个真实测试台，各自执行 xvlog、xelab、xsim | `out/rtl.receipt.json` 为 PASS，`out/rtl/result.json` 有完整实际结果，日志包含 `AUAR_RTL_PASS` |
| `prepare` | 从源码封装自研 IP，重建 BD、校验连接、生成 wrapper 和工程 | `out/prepare.receipt.json` 为 PASS，日志包含 `AUAR_PREPARE_PASS`，存在 `out/hardware/project/platform.xpr` |
| `implement` | 综合、布局布线、时序和 DRC 检查、导出 BIT/XSA | `out/implement.receipt.json` 为 PASS，日志包含 `AUAR_IMPLEMENT_PASS`，新 BIT/XSA 非空 |

`prepare` 通过只代表工程重建完成。要说明硬件构建完整通过，还须完成 `implement`。

最终查看本轮 `out/hardware/reports/` 下的 `timing.rpt`、`route.rpt`、`drc.rpt`、`implementation.json`：setup WNS、hold WHS 不小于 0，TNS/THS 和违规端点为 0；可路由网络全部布通、路由错误 0、DRC Error 0。关注并说明实际警告，不以“无 Error”代替报告检查。新产物应为 `out/hardware/auar_source.bit` 和 `auar_source.xsa`。

每阶段命令应返回 0。失败时查看 `out/<阶段>.console.log` 和 `out/<阶段>.vivado.log`；RTL 还保留各测试台的工具日志。保留失败证据，修复源码后重新做完整的源码指纹配套验证，不手改 PASS 回执。

## 一次执行的替代方式

如果不分阶段，直接从全新输出目录运行：

```sh
python3 -B build/reproduce.py --out "$AUAR_OUT" --stage hardware \
  --vivado "$AUAR_VIVADO" --vitis-root "$AUAR_VITIS"
```

它顺序执行 `rtl → prepare → implement`。与上面的分阶段流程二选一，不能在已有完整阶段输出的目录再跑一次。

若还要检查离线框架和比赛 Skill，将 `hardware` 改成 `all`，同样使用新输出目录。`all` 的范围是框架、Skill、RTL、建工程和综合实现；模型重编译、原生库交叉编译、固件安装及实板业务仍有各自入口，不能据此一并宣布通过。

## 判定边界

包内 `report/validation_summary.md` 和既有 `archive_verification.json` 是保存的历史证据。新一轮结论以新的 `AUAR_OUT` 中实际生成的日志、退出码、源码指纹、阶段回执和报告为准。即使本轮完整构建通过，真实 KV260 冷启动、推理、声音、显示和转轴业务仍须单独验收。

官方方法依据：[Vivado 2022.2 从 Tcl 重建工程](https://docs.amd.com/r/2022.2-English/ug892-vivado-design-flows-overview/Creating-a-Tcl-Script-to-Recreate-the-Project)、[Vivado 2022.2 批处理执行 Tcl](https://docs.amd.com/r/2022.2-English/ug895-vivado-system-level-design-entry/Launching-the-Vivado-Tools-Using-a-Batch-Tcl-Script)。本包阶段参数以包内脚本实际实现为准。
