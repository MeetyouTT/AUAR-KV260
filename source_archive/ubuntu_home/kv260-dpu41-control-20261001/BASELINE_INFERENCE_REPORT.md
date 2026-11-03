# 备用卡官方 ResNet18 基线复测

状态：**备用卡上的官方基线复测完成：分类、输入文件核验、预热、六轮正式性能复测及测试后状态核对全部通过。** 本报告保留官方对照数据；之后候选实际加载、同输入测试及官方恢复也已完成，见 [CANDIDATE_BOARD_TEST_REPORT.md](CANDIDATE_BOARD_TEST_REPORT.md)。最后实测仍为官方 app active slot 0，候选 inactive。

## 测试对象及固定输入

测试在已烧录官方 PetaLinux 2022.2 / Vitis AI 3.0 镜像的独立 32 GB 备用卡上执行。当前应用为 `kv260-benchmark-b4096`，DPU 4.1、B4096、1 CU、300 MHz、地址 `0xa0010000`，硬件和原模型指纹均为 `0x101000056010407`。详见 [TEST_CARD_BASELINE_REPORT.md](TEST_CARD_BASELINE_REPORT.md)。Win11 SSH 已由用户实际登录确认；自动测试使用 Ubuntu 串口。

| 输入 | 实测 SHA-256 |
|---|---|
| 固定 JPEG，661,378 bytes | `f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a` |
| ResNet18 XMODEL | `4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef` |
| ResNet18 `.prototxt` | `691c393b15ae87976060a125067534334bd034c3a5193a96f6f5db3f4da3729c` |
| 分类程序 | `322dd07736f409cba02416782475c0dc2b5951435ddbb6d0671d3cda8fac0c0e` |
| 性能程序 | `b9f52e4fd21d6526a8ac1e73b6e839b28308368451c4bb30e845a9f96343f1b4` |
| 单图列表 `samoyed.list` | `bf02d74370fbfdd8d008c7916109a14be3a5b33bd6057522fbb14e95ac2e9caa` |

固定图来自 [PyTorch ResNet 示例](https://pytorch.org/hub/pytorch_vision_resnet/)，原始下载地址为 `https://raw.githubusercontent.com/pytorch/hub/master/images/dog.jpg`。下载后未编辑图片。主机路径为 `downloads/pytorch-resnet-dog.jpg`，板端为 `/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg`。通过串口分 862 帧传输，逐帧确认并核对完整 SHA-256；未覆盖已有板端文件。证据：[18-image-transfer.result.json](evidence/test_card_board_20261001/18-image-transfer.result.json)、[test_inputs.output](evidence/test_card_board_20261001/19-baseline-classification.test_inputs.output)。历史测试图的原始字节哈希仍未确认，分数相同不能证明图片文件相同。

## 分类结果

命令成功返回 0，完整输出经传输校验保存：

```bash
cd /home/root/kv260-test-20261001
env XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin /home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification resnet18 /home/root/kv260-test-20261001/pytorch-resnet-dog.jpg
```

| 排名 | 类别 | 分数 |
|---|---|---|
| 1 | Samoyed, Samoyede | 0.949879 |
| 2 | white wolf, Arctic wolf, Canis lupus tundrarum | 0.00931229 |
| 3 | Pomeranian | 0.00821807 |
| 4 | Great Pyrenees | 0.00498451 |
| 5 | Arctic fox, white fox, Alopex lagopus | 0.00388194 |

证据：[classification.output](evidence/test_card_board_20261001/20-resnet18-classification.classification.output)。Top-1 与用户历史记录一致，本次结果针对上述已固定图片与模型。

## 性能方案及预热

单线程和双线程分别运行一次 10 秒预热；两次都成功返回 0。预热结果为 214.787 / 238.512 FPS，不纳入正式三次统计。

正式命令模板（`N` 为 1 或 2，各重复三次；列表为最后一个参数）：

```bash
cd /home/root/kv260-test-20261001
env XLNX_VART_FIRMWARE=/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin /home/root/Vitis-AI/examples/vai_library/samples/classification/test_performance_classification resnet18 -s 60 -t N /home/root/kv260-test-20261001/samoyed.list
```

已核查板端 `benchmark.hpp`：程序预先读取并缩放图片，测量循环包括模型调用，采用 10 秒报告步长和 `SIGALRM` 停止。此 FPS 不包含逐帧 JPEG 读盘/解码，也不是摄像头、显示或运动控制整条应用的吞吐量。选择 60 秒避免短于报告步长造成统计偏差。源码和实际 CLI 保存在 [performance_source.output](evidence/test_card_board_20261001/20-resnet18-classification.performance_source.output)。单线程输出的 E2E_MEAN 单位由源码确认为微秒。

正式结果如下，六条命令均返回 0、输出传输校验通过：

| 线程数 | 第 1 次 FPS | 第 2 次 FPS | 第 3 次 FPS | 中位数 FPS |
|---|---|---|---|---|
| 1 | 214.986 | 214.949 | 214.961 | **214.961** |
| 2 | 238.709 | 238.777 | 238.863 | **238.777** |

完整命令、执行 UTC、原始串口和输出校验见 [22-performance.results.jsonl](evidence/test_card_board_20261001/22-performance.results.jsonl)。每轮记录 `/sys/class/hwmon/hwmon1/temp*_input` 的前后值（毫摄氏度）。测试前已测得三个节点约 35.204、36.308、34.785 °C；此前 `thermal_zone*/temp` 未找到并不代表不能获取温度。原始节点及 IIO 标签见 [performance_options.output](evidence/test_card_board_20261001/19-baseline-classification.performance_options.output)。不修改 CPU/DPU 频率或调速器。前后采样不能代表测试期间的连续温度峰值。

六轮前后温度采样范围为 **33.961–38.919 °C**。解析器逐条检查命令返回码、完整传输、输出 SHA-256、实际 60 秒/线程数日志及测试后固件哈希后，生成 [baseline_inference_summary.json](evidence/test_card_board_20261001/baseline_inference_summary.json)。历史 FPS 的原测试窗口与完整条件未知，因此此处建立新固定对照，不据此宣称性能提升。

## 测试后状态

`xmutil listapps` 仍显示官方 app active slot 0；BIN、DTBO、XCLBIN、XMODEL 和图片哈希与测试前预期完全一致。网口保持 `192.168.50.2/24`。再次实际查询 DPU 仍为 v4.1.0、1 CU、300 MHz、地址 `0xa0010000`、指纹 `0x101000056010407`。证据：[post_test_state.output](evidence/test_card_board_20261001/23-post-test.post_test_state.output)、[post_test_dpu.output](evidence/test_card_board_20261001/23-post-test.post_test_dpu.output)。

保留测试后内核尾日志：[health_log.output](evidence/test_card_board_20261001/23-post-test.health_log.output)。日志重复出现 `skip kind 29(AIE_RESOURCES) return code: -22`，相邻 `zocl_xclbin_read_axlf` 为官方 UUID `eedb44e9-3f77-0244-9ea9-23b953894638`、最终 `ret: 0`；六轮推理和随后查询也成功。负值日志保留，不将其隐藏或表述为“日志全无异常”。本次只采集尾部 160 行，不宣称覆盖全部历史内核日志。

## 串口恢复及限制

Win11 直连网络和 SSH 登录成功后，Ubuntu 串口曾无响应。用户提供 SSH 内的 `ttyPS1` 进程和终端设置；板端开启 `ixon ixoff`。发送 Ctrl-Q 未恢复，用户从 SSH 临时关闭这两项后，主机收到串口测试标记，root 提示符恢复。证据：[13-uart-link.result.json](evidence/test_card_board_20261001/13-uart-link.result.json)。这支持问题与流控状态有关，未复现具体触发过程。

原速度的长命令输入随后未完整传输，停在补全提示符；保留 [14-inference-preflight.results.jsonl](evidence/test_card_board_20261001/14-inference-preflight.results.jsonl)。清理未完成输入后，采用约 100 bytes/s 的输入节奏，后续前置核验、分类及预热都成功；原采集器与历史日志保留。新的 `collect_checked.py` 会在任何命令非零返回或传输不完整时停止后续步骤。

未重启板卡、getty，未修改启动串口配置。流控变更为运行时变更；测试后在外部命令执行期间读取终端设置，`ixon ixoff` 已恢复，后续采用慢速传输仍正常。原暂停的具体触发过程尚未复现；本阶段实际采用慢速传输和完整输出校验完成采集。板端日历时间尚未同步，证据使用主机 UTC 标记；性能计时使用程序测量窗口。本报告的数据针对官方基线；候选 DPU 4.1 的加载、同输入复测和恢复结果另见候选测试报告。Overlay 引用计数错误、部署 DRC/接口约束问题和后续运动 IP 验证仍未解决。
