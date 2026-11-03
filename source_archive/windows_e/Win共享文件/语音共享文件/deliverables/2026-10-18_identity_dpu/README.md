# SFace DPU身份候选

当前状态：**SFace INT8工程候选已完成B4096整图编译、实板执行和同进程双模型固定图短测；真人身份精度及正式业务接入尚未验收。** 用户回复“可以”并要求“继续”后已恢复执行，先前暂停记录保留为历史。

本轮没有改生产模型、业务源码、相机/GTK/语音配置或FPGA位流，也没有登记用户。为释放独占DPU做了三次受控相机服务停止/恢复，均有finally及70秒定时恢复保护；GUI PID保持。最后20秒恢复检查通过，相机检测约9.89Hz、无相机/检测错误，流式状态仍启用，身份业务仍未启用。

## 已有结果

- 原SFace学习参数保留，沿用已核对的等价PReLU/分组空间FC改写。
- 公开参考图做32种光度/镜像变化，实际执行Vitis AI3.0 PTQ校准、测试与xmodel导出。这只验证工程链路，不能代替代表性真人校准集。
- `vai_c_xir`整图编译成功，产物10,796,371字节，SHA256 `bee245f2a94e4d28cc00d7f367fa08c7c375feee2081267c8e414033067df3d8`。
- 实际XIR为1个DPU计算子图；其他为输入data-fix和CPU输出fix2float。核心计算没有回退CPU。目标指纹 `0x101000056010407`。
- DPU输入NHWC INT8 `[1,112,112,3]`、fix_point=7；输出INT8 `[1,128]`、fix_point=5。输出反量化及L2归一化仍由CPU完成。
- 公开参考人脸的FP32/量化特征余弦约0.97035；黑/灰/随机对照更低。该数字不是识别准确率，仍未验证同人/异人、陌生人拒判或阈值。
- 编译工件哈希、非DPU分区、4组INT8测试向量形状/类型及6份源文件语法检查通过。

## 传输与实际板测

板端VART/XIR及模型加载可用。最初独立Runner与 `xdputil query`均出现超时；分阶段诊断明确停在Runner创建，日志为等待其他进程释放 `DPU_0`，当时YOLO相机进程持有该资源。未据此重载DPU或更改位流。随后采用受控停止相机、独立/同进程测试、自动恢复方式，证实模型可执行。

首次460800/768字节串口传输在ACK2097处中断，留下1,610,496字节partial。主机与板端该前缀SHA一致；改以230400/384字节、有限重试续传，实际零重试，526.737秒完成剩余数据。整包7,779,554字节及最终SHA通过，终端波特率115200和回显恢复通过；解包后模型/测试载荷逐项SHA再次核对。

| 实际验证 | 结果 | 范围 |
| --- | --- | --- |
| SFace独立DPU执行 | 4组INT8输出与主机量化参考逐字节一致，最大整数差0 | 黑/灰/随机/公开参考；单次提交等待7.515—7.807ms，不含YuNet/对齐 |
| 同进程YOLO基线 | 50次调用，中位6.542ms，P95 7.134ms | 固定公开人体图，100ms调度周期，无周期超时 |
| 同进程YOLO+SFace | 100次YOLO、20次SFace，预定检测10Hz/身份2Hz；周期超时0，20次身份输出仍逐字节一致 | 约10秒固定输入，非真实相机/跟踪流程 |
| 混合时模型调用 | YOLO中位6.554ms；SFace中位7.677ms、P95 8.093ms | 包含提交/等待或本机封装耗时，不是纯硬件忙时/利用率 |
| 原服务恢复 | 最后20样本相机约9.895Hz、帧龄最大151ms，无错误；GUI PID保持，main/IDLE/IDLE_READY，streaming=true | 原配置、boot保持，恢复定时器已清理；没有新语音播放/听音验收 |

首轮受控独立测试因VART Python接口用法不匹配失败：实际 `execute_async`返回元组，`wait`只接受该元组。修正后通过；失败及每次恢复均保留。相机最终PID141309/新代次，原PID987不能再作为当前进程引用。

这些是工程执行及固定输入模型切换验证，不是正式统一相机DPU调度、长稳、真人身份准确率或界面登记闭环。不能把固定图10Hz/2Hz结果当成相机多人负载承诺，也不能把CPU旧整链395.91ms与本轮SFace调用约7.7ms直接相除作为加速比。

## 后续仍需

1. 确认授权真实人脸校准数据及独立评测来源；本轮尚未采集/保存真人样本。
2. 用代表性数据重新校准，评估同人/异人、拒判、多人及INT8阈值；保持独立模型ID，不能直接混用CPU模板。
3. 完成同进程DPU调度、YOLO优先/身份低频混跑，测帧龄、等待、CPU和DDR。
4. 合入当前流式界面，补多样本登记和多帧一致性，验登记、重返、陌生人、删除与换轨迹。

当前工作区 `/home/ghmd/aura-identity-dpu-check-20261018`；编译采用现有 `xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106` 禁网容器和固定B4096 arch.json。本轮正式源码未修改。参考输入数组、身份特征库和串口原文不作为共享工件。

## 可复核工件与重建方式

- [已编译工程模型](engineering-bee245f2a94e4d28/sface_engineering.xmodel)、[实际XIR分区/布局](engineering-bee245f2a94e4d28/compiled-result.json)、[工件哈希摘要](engineering-bee245f2a94e4d28/verification.json)。
- [编译日志](engineering-bee245f2a94e4d28/logs/compile-engineering.log)、[量化有限对照](engineering-bee245f2a94e4d28/quantized-metrics.json)、[量化配置](engineering-bee245f2a94e4d28/quant_info.json)。
- [量化脚本](engineering-bee245f2a94e4d28/source/quantize_sface.py)、[导出/编译与分区检查](engineering-bee245f2a94e4d28/source/export_compile.py)、[最终独立板测控制器](engineering-bee245f2a94e4d28/source/board_standalone_sface.py)、[同进程双模型短测](engineering-bee245f2a94e4d28/source/board_mixed_benchmark.py)。旧独立并行进程示例作为失败证据保留，实际集成必须处理同一进程内的DPU所有权和调度。
- [独立板测结果](engineering-bee245f2a94e4d28/evidence/standalone-board-retry/response.json)、[双模型固定图结果](engineering-bee245f2a94e4d28/evidence/mixed-fixed-input/response.json)、[恢复后20秒](engineering-bee245f2a94e4d28/evidence/recovery-postcheck/response.json)。最终58份工件逐项长度/SHA核对通过。
- [参考输入生成器](engineering-bee245f2a94e4d28/source/create_reference.py)的9个输入/输出数组与原工件逐项、整NPZ字节复核一致，见[复现核验](engineering-bee245f2a94e4d28/reference-generator-verification.json)。输入图和数组仍留在私有测试目录。

复现使用原SFace/YuNet固定SHA权重，以及CPU参考OpenCV/NumPy环境。先以 `create_reference.py --aura <aura目录> --image <授权参考图> --output <私有工作区>/reference-parity.npz` 产生数值测试输入，再把核心源码和该NPZ放入容器 `/work`。当前只支持固定的单张参考图工程校准，不是通用真人数据集量化工具。

容器以既有Vitis AI3.0镜像加载 `vitis-ai-pytorch` conda环境，另需固定ONNX1.12.0依赖（本轮只从独立工作目录加载）。源模型只读挂到 `/models`，目标arch只读挂到 `/target-arch.json`，工作目录可写。在容器内依次执行：

```bash
python -B /work/quantize_sface.py --mode calib
python -B /work/export_compile.py
```

原模型SHA和浮点改写说明见前期兼容结果；本轮已修正导出脚本显式指定输出目录，并从实际XIR的 `dpu_fingerprint` 字段核对目标。首次脚本目录判断、字段判断的失败日志保留，不能将它们误写为编译器失败或目标硬件不兼容。

串口工具只从私有工作目录运行，避免将原始串口或参考数组写入共享目录；板测控制器绑定本轮boot、SD、模型SHA与隔离路径，换板/重启后须重新核对。最终证据由 `publish_engineering.py` 复制，再由 `finalize_engineering.py` 纳入独立板测、短测和恢复结果；这是固定环境下的复核工具，还不是通用自动部署器。

相关说明：[身份具体做法与缺口](身份识别_具体做法与实际缺口.md)、[DPU模型选择](DPU模型选择建议.md)、[整个项目模型清单](整个项目_模型总清单_20261018.md)。
