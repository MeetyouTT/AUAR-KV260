# KV260：指纹阻断的处理方案

2026-10-01 主机侧核查结果：原样参考构建成功；其 DPU 版本与原板模型对应的版本不同。Vivado/Vitis/PetaLinux 不需要因此重新安装。原始源码 commit 与构建工件保持原样，板端未操作。

## 已确认的差异

| 项目 | 已构建参考工程 | 原板基线 |
|---|---|---|
| DPU 版本 | 4.0：HWH `SYS_IP_VER=0x00000040` | 4.1：此前板端 query 记录 |
| 架构指纹 | `0x101000016010407`（生成的 arch.json） | `0x101000056010407`（此前硬件 query 与原 ResNet18 XMODEL） |
| XOR | 两者为 `0x40000000`，仅 bit 30 不同 | 同左 |
| bit 30 的定义 | Vitis AI 3.0 target factory 的 `SV_AM` / `save_engine.argmax` 为 false | 为 true |

证据：

- [fingerprint_diagnosis.json](evidence/deployment_review/compatibility_diagnosis/fingerprint_diagnosis.json) 给出 XOR、HWH 参数和原模型文件哈希。
- 本机已有官方 `Vitis-AI-3.0.zip` 中的 `create_target_DPUCZDX8G_ISA1.cpp:53` 解码 bit 30，`:121` 设置 SAVE engine 的 Argmax；已将原文提取到 `evidence/deployment_review/compatibility_diagnosis/official_vitis_ai_3_0_sources/`。
- 同一官方归档的 `README_DPUCZ_Vitis.md` 说明 DPU TRD v4.1 对应 Vitis AI 3.0/Vitis 2022.2，v4.1 增加 Argmax；v4.0 对应 Vitis AI 2.5。
- VART 3.0 的 `dpu_runner_base_imp.cpp` 对非零 model/hardware fingerprint 做相等检查。因此即使当前 ResNet18 不使用 Argmax，也不能把一个 feature bit 的差异当成可以跳过的检查。

当前新硬件的 fingerprint 尚未通过板端寄存器查询实测；这里比对的是新 arch.json/HWH 与既有板端查询/模型证据。不能仅修改 arch.json、XMODEL 的 fingerprint，或关闭检查来证明兼容。

## 推荐路径：保持原 XMODEL，另建 DPU 4.1 对照

如果目标仍是用原 `.xmodel`、原图片与原板直接比较，优先采用这一条：

1. 保存原样参考工程和成果，在另外的工作目录准备兼容性工程；继续以同一 Kria platform 固定 commit 为基底，单独记录 DPU 依赖变更。这是一个新的对照工程，不能称为固定源码原样重建。
2. 使用 Vitis AI 3.0 官方 DPU 4.1 TRD 的 DPU IP、Vitis wrapper、封装脚本和 fingerprint 模板作为一组依赖；记录下载 URL、归档 SHA-256 和来源。不能只换一个 ttcl 或只改版本标记。
3. 保持 KV260 平台、B4096、单 CU、`0xa0010000` 地址和原内存连接，逐项核对 v4.1 参数及接口。先验证 XO 封装与生成的 arch.json 为目标 `0x101000056010407`，再完成 link/实现；不加入自研运动 IP。
4. 收集新的 HWH/XCLBIN/BIT/arch、DRC/时序/资源报告，并核对 DTBO 与目标 PetaLinux/XRT/FPGA manager 的加载路径。所有这些文件必须来自该对照构建，不能混用原板的预编译 BIT。
5. 主机侧审阅通过后，再按独立测试卡流程验证实际硬件指纹、同一 XMODEL 和同一图片。本轮尚未执行第 1–5 步中的兼容性构建或板端操作。

官方来源已在本机归档中核对：`dpu/README.md` 指向 `DPUCZDX8G_VAI_v3.0.tar.gz`，并说明它支持 MPSoC/Kria K26、使用 Vivado/Vitis 2022.2 验证。下载内容、与当前 wrapper 的具体差异尚未验证，不能提前保证更换成功。

## 另一条路径：保留当前 DPU 4.0，重新编译 ResNet18

使用本次真实生成的 arch.json，将相同 ResNet18 的量化源模型重新编译，输出到新目录；保留原 `.xmodel`。这样可以验证当前参考硬件，但生成的 XMODEL 文件将改变，属于“相同网络/权重、重新编译”的对比，不能声称使用原文件原样复测。

主机已安装 `xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106` Docker 镜像。关闭网络、只读容器文件系统后，加载其 `vitis-ai-pytorch` Conda 环境，`vai_c_xir --help` 和 `vai_c_caffe --help` 均成功，日志见 [compiler_after_activation.log](evidence/deployment_review/compatibility_diagnosis/compiler_after_activation.log)。未安装新软件、未拉取镜像。

编译器支持 `vai_c_caffe -p <quantized.prototxt> -c <quantized.caffemodel> -a <new arch.json> -o <new output> -n resnet18`，或 `vai_c_xir -x <quantized.xmodel> -a <new arch.json> -o <new output> -n resnet18`。当前查找尚未发现对应的量化源模型；只持有已编译的板端 ResNet18 XMODEL，不能假定它等价于可重编译的量化输入，也没有执行伪造 target 的“修复”。

## 同时修正的审阅项

- CLB site 99.58% 表示大部分站点已经放置至少一个单元；已占用 CLB 仍可能有空余 LUT/FF。不能据此认定无法增加小型 AXI-Lite/PWM。实际是否能放下，需要集成后的布局布线与时序证明。已将原审阅中的过强表述修正。
- 原实现全局垂直/水平路由使用率分别为 48.0865%/40.9205%，无 failed/unrouted/partially routed nets；这些数值也不能代替新增逻辑的局部拥塞评估。
- 已只读提取原镜像的 DTBO 和 ResNet18 XMODEL，哈希与既有基线记录一致。DTBO 的 [差异文件](evidence/deployment_review/compatibility_diagnosis/dtbo_difference.diff) 显示候选缺少 `fpga-config-from-dmabuf` 且节点布局不同；不能只核对 basename 就批准加载。
- 新 BIT/XCLBIN 哈希与基线不同是重新构建的预期结果；真正的兼容门槛是接口、版本、模型指纹、设备树和加载方式匹配。
- 修正了 DRC TSV 的换行/制表符格式，并生成原报告引用但缺失的 bundle manifest。旧报告、旧 TSV 和旧哈希清单已归档到 `compatibility_diagnosis/previous_review/`。

当前建议先做 DPU 4.1 独立兼容性对照，原样参考成果继续保留；在匹配原 ResNet18 的硬件复测通过后，再另开自研 IP 集成阶段。
