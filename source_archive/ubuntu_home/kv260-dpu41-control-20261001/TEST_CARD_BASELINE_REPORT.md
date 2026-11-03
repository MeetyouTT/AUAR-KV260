# KV260 备用卡启动及官方运行环境检查

状态：**备用卡已启动；Win11 SSH 登录成功；官方应用、DPU 与模型核验、固定图片分类及单/双线程各三次 60 秒性能复测全部通过。后续候选加载与同输入测试也通过，并已恢复官方应用。** 本报告保留官方基线检查，候选和恢复证据见 [CANDIDATE_BOARD_TEST_REPORT.md](CANDIDATE_BOARD_TEST_REPORT.md)。

用户确认备用卡已开机后，通过已识别的 Xilinx UART interface 01（115200、8N1、无流控）连接 root 终端。证据保存在 [test_card_board_20261001](evidence/test_card_board_20261001/)，保留每个命令、返回码、完整串口流、解码输出和 SHA-256。

## 已确认

| 项目 | 实测结果 |
|---|---|
| 板型与系统 | `ZynqMP SMK-K26 Rev1/B/A`；PetaLinux `2022.2_release_S10071807`，kernel `5.15.36-xilinx-v2022.2` |
| 实际根分区 | `/dev/mmcblk1p2`，SD 卡约 29.7 GiB；启动日志显示根文件系统从 2,295,811 blocks 扩展到 7,772,419 blocks，根分区约 29.6 GiB |
| 与原卡区分 | 新卡名称 `SE32G`，容量约 29.7 GiB；保存的原卡记录为 119.1 GiB。本次检查针对用户确认已插入的备用卡 |
| 官方活动应用 | `kv260-benchmark-b4096`，active slot 0；`dfx-mgr` active |
| 官方固件一致性 | BIN、DTBO、XCLBIN 的 SHA-256 均与保留的官方镜像/原基线记录一致 |
| 运行时 | XRT/ZOCL `2.14.0`；VART、Vitis AI Library 和 target-factory `3.0.0` |
| 实际 DPU | `xdputil query` 返回 1 个 `DPUCZDX8G_ISA1_B4096` CU，DPU `v4.1.0`，300 MHz，控制地址 `0xa0010000`，指纹 `0x101000056010407` |
| 实际注册 XCLBIN | 内核日志显示官方 UUID `eedb44e9-3f77-0244-9ea9-23b953894638`，`zocl_xclbin_read_axlf` 返回 0 |
| ResNet18 | XMODEL SHA-256 为 `4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef`；DPU 子图 `dpu_fingerprint=0x101000056010407`，与硬件实际指纹相同 |
| 固定图片分类 | Top-1 `Samoyed, Samoyede`，分数 `0.949879`；图片 SHA-256 已在主机和板端核对 |
| 性能复测 | 单/双线程各三次 60 秒，均成功；FPS 中位数 `214.961` / `238.777` |
| 测试后状态 | 官方 app 仍 active slot 0；BIN、DTBO、XCLBIN、模型及图片哈希一致；DPU 指纹及地址保持一致 |
| 当前网络 | Win11 `192.168.50.1/24`（用户提供）；板卡 `192.168.50.2/24`（实测）；网口 1000 Mb/s、Full Duplex、Link detected: yes |
| SSH 服务 | `dropbear.socket` 监听 22；板端连接 `127.0.0.1:22` 收到 `SSH-2.0-dropbear_2020.81`；Win11 SSH 登录成功由用户确认 |

官方基线阶段的 DPU 实际查询显式指定当时活动 app 的 XCLBIN。该查询会注册官方 XCLBIN、访问硬件；该阶段没有加载候选 DPU 4.1 bundle。查询和内核证据见 [dpu_query.output](evidence/test_card_board_20261001/03-runtime.dpu_query.output)、[sample_images.output](evidence/test_card_board_20261001/03-runtime.sample_images.output)。模型子图的最终检查见 [model_arch.output](evidence/test_card_board_20261001/04-confirmation.model_arch.output)。

官方运行 BIN SHA-256：`7d12c877e0fde40a243d2350b1a2227f565788bf9e2dcae4439d07f213d40a3f`；DTBO：`36338937904e5ec988566d7341f6504edba34c01bd7e2e3f2025ab0069337e35`；XCLBIN：`fc3abb934eec544e49a17c484336cf177258f475522cefc994ec458b726f69ac`。样例程序和 `.prototxt` 当前哈希已记录在 [resnet_files.output](evidence/test_card_board_20261001/02-baseline.resnet_files.output)，供后续相同条件比较。

## 检查过程与已解决问题

最初网口为 **NO-CARRIER**，无 IPv4。用户插入网线后链路恢复，但 DHCP 未获得地址；随后用户明确网线直连 Win11，并提供以太网 IPv4 `192.168.50.1`、掩码 `255.255.255.0`。此网络阻塞已解决。历史诊断保留：[network_details.output](evidence/test_card_board_20261001/03-runtime.network_details.output)、[network_config.output](evidence/test_card_board_20261001/04-confirmation.network_config.output)。

在备用卡创建 `/etc/systemd/network/10-kv260-win11-direct.network`，设置 `Name=eth0`、`Address=192.168.50.2/24`、`DHCP=no`，执行 `networkctl reload` 和 `networkctl reconfigure eth0` 生效，未重启。配置 SHA-256 为 `49c4ca017d331ca8a159cd9b83fa8eb92263f5910685b7ab61beb31a85d0a7d3`。实测板端 ping `192.168.50.1` 两次均成功、丢包率 0%；IPv4 SSH banner 正常。此配置持久保存，不设置默认网关或 DNS。证据：[configure_direct.output](evidence/test_card_board_20261001/08-win11-config.configure_direct.output)、[windows_peer.output](evidence/test_card_board_20261001/08-win11-config.windows_peer.output)、[ssh_ipv4_banner.output](evidence/test_card_board_20261001/08-win11-config.ssh_ipv4_banner.output)。SSH banner 检查使用板端回环地址；后续 Win11 到板端的密码认证成功由用户提供的 SSH 会话确认。登录步骤见 [WIN11_SSH_GUIDE.md](WIN11_SSH_GUIDE.md)。

首次检查备用卡 `/home/root`、`/tmp`、`/boot`、`/media` 未找到 JPEG/PNG 测试图片，主机也未找到历史原图。随后下载固定 PyTorch ResNet 示例图片，通过串口传到独立目录并核对完整哈希；该图片上的分类和六轮性能复测已完成，详见 [BASELINE_INFERENCE_REPORT.md](BASELINE_INFERENCE_REPORT.md)。历史图片字节哈希及性能测试完整条件仍未确认，本次新固定对照不会把历史 FPS `214.381/238.479` 当作实测值。

检查脚本首次按 `mmcblk0` 读卡标识失败，后续按实际 `mmcblk1` 修正；首次模型检查调用了此版 XIR 不存在的 `children_topological_sort`，后续用实际提供的 `toposort_child_subgraph` 重查通过。`ss` 命令未安装，后续用已有 `netstat` 确认 22 端口监听。初次检查的 `thermal_zone*/temp` 节点不存在，之后已通过 `hwmon1/temp*_input` 获取性能测试前后温度，详见官方基线复测报告。这些失败及修正均保留，不能将复合 shell 命令的最终返回 0 解释为其每条子命令均成功。

板端时钟尚处于镜像的初始日期（日志显示 2021 年）；证据关联使用 Ubuntu 主机记录的 UTC 时间，未主动修改板端时钟。待网络连通后再检查时间同步。

## 后续步骤

Win11 SSH 和备用卡官方 app 的分类、单/双线程性能对照均已完成，完整结果见 [BASELINE_INFERENCE_REPORT.md](BASELINE_INFERENCE_REPORT.md)。后续经用户授权，候选实际加载、同输入测试及官方恢复均已通过，最后实测官方 active slot 0、默认 VART 路径与原 IP 标记已还原，见 [CANDIDATE_BOARD_TEST_REPORT.md](CANDIDATE_BOARD_TEST_REPORT.md)。两次卸载的 overlay 引用计数错误、主机 DRC/时序问题仍保留，后续条件见 [DEPLOYMENT_REVIEW.md](DEPLOYMENT_REVIEW.md)；暂不反复切换。

## 串口恢复历史

下列保留初期失败与修正过程；随后串口采集、官方及候选测试和恢复已完成，不能将某次采集失败解释为当前仍未完成测试。

用户已明确登录成功的是 Win11 SSH；该结果来自用户确认，未保存远程登录会话。尝试通过串口执行 `10-inference-preflight` 时，连接输出仅为换行，未得到 root 提示符；采集器按保护条件停止，未发送清单中的任何检查命令。证据：[10-inference-preflight.results.jsonl](evidence/test_card_board_20261001/10-inference-preflight.results.jsonl)。本次未传图片、未执行分类或性能测试、未切换应用。已保存的内核日志和服务检查显示板端控制台为 `ttyPS1`，对应 `serial-getty@ttyPS1.service`；当前串口会话状态需从已登录 SSH 中检查，未擅自发送 Ctrl-C、重启 getty 或重置板卡。

随后用户通过 SSH 提供进程列表：`ttyPS1` 上为 PID 1298 的 `login` 及 PID 1512 的前台 `sh`，没有 `passwd` 进程。依据此状态，仅发送一次 Ctrl-C 和回车尝试恢复 shell 提示符，结果无输出，未确认 root shell。证据：[11-prompt-recovery.result.json](evidence/test_card_board_20261001/11-prompt-recovery.result.json)。主机只读检查确认稳定 USB 路径仍映射 `/dev/ttyUSB1`，波特率 115200，DTR/RTS 为置位状态。尚不能确认串口故障原因；需从 SSH 获取板端 `stty -F /dev/ttyPS1 -a` 设置，未重启 getty 或板卡。

用户进一步提供完整 SSH 登录及 `stty` 输出，确认密码认证已成功。板端串口为 115200、8N1、`cread clocal -crtscts`，启用 `ixon ixoff`；当时 shell 使用非规范、无回显终端模式，单凭这些模式不能认定配置损坏。保留脱敏用户证据：[ssh-user-confirmation.json](evidence/test_card_board_20261001/ssh-user-confirmation.json)。发送一次 Ctrl-Q 和回车仍无输出，见 [12-flow-resume.result.json](evidence/test_card_board_20261001/12-flow-resume.result.json)。随后用户从 SSH 临时禁用流控并发送串口标记，Ubuntu 收到标记并恢复 root 提示符。原速度长命令输入仍不完整，清理后采用约 100 bytes/s 输入，最终核验、图片传输、分类、预热、六轮正式性能测试及测试后检查全部完成。详细恢复证据及限制见 [BASELINE_INFERENCE_REPORT.md](BASELINE_INFERENCE_REPORT.md)。该官方基线阶段未切换固件；之后的候选切换及恢复另有完整报告。
