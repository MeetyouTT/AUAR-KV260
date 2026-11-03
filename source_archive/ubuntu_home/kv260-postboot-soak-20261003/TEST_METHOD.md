# 冷启动后采样复测记录

本次在已持久启用修复运行时的备用 SD 卡上进行。官方应用 `kv260-benchmark-b4096` 保持活动，不执行应用切换。开始时 boot ID 为 `0251d729-0d3c-44e8-abb9-27121306c081`，manager PID 为 `1012`，修复 ZOCL srcversion 为 `9BDC942A6014BCCBD1DCB78`。

## 实际测试方法

板端后台 shell PID `2461` 顺序执行 60 次单图片分类，相邻调用间等待 30 秒。每次保存完整输出及返回码，随后记录 manager PID、ZOCL refcnt 和 MemAvailable。它属于约 30 分钟的间隔功能观察，不等同持续满负载压测或 FPS 基准测试。

分类命令：

```sh
/home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification \
  /usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel \
  /home/root/kv260-test-20261001/pytorch-resnet-dog.jpg
```

原模型、图片和程序的 SHA-256 在启动循环前分别确认：

- XMODEL：`4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef`
- 图片：`f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a`
- 程序：`322dd07736f409cba02416782475c0dc2b5951435ddbb6d0671d3cda8fac0c0e`

判断标准是 60 次返回码均为 0、每次完整 Top-5 的类别编号及分数与基线一致、manager PID 和 boot ID 稳定、修复模块仍在、最终 DPU query 成功且架构指纹符合预期、原 26 项文件校验通过。MemAvailable 仅作为采样观察，不据此宣称排除了内存泄漏。

板端原始证据目录：`/home/root/kv260-runtime-persistent-backup-20261003/postboot-soak/`。`scripts/collect_soak.py` 经压缩/base64 经 UART 传入，回读 SHA-256 匹配后启动；只观察现有循环并采集状态。

## 计时与采样限制

板端日期未同步，日志显示 2021-11-19。本次使用 `/proc/2461/stat` 中启动 ticks 和 `/proc/uptime` 计时，记录 boot ID；主机采集日期为 2026-10-03。监测程序在循环约第 10 分钟启动，内核起始快照不是循环开始时的快照，因此内核增量覆盖范围需要按实际记录说明。

`summary.csv` 的 Top-1 字段包含未转义逗号；返回码由每行前三个字段读取，完整 Top-5 以逐轮 `run-NN.log` 为依据。

准备阶段曾尝试 `test_jpeg_classification --help`，该程序把 `--help` 当模型名，报 `VAILIB_DPU_TASK_NOT_FIND`。随后使用上述实际模型/图片命令成功。这次诊断调用发生在长测开始前，不计入 60 轮。

验收结论以完成后的独立报告和封存摘要为准。
