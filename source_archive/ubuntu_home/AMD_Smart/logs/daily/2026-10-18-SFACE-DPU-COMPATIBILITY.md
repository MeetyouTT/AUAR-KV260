# 2026-10-18 SFace 到 B4096 的兼容性实查

用户在DPU余量讨论后询问接下来做什么。本轮实际推进Ubuntu离线模型兼容性检查，未改运行配置或位流。读取ZIP入口、现行计划、最新日志和共享入口/回执；语音AGENTS新增“不加语音FPGA模型”、流式播放及延迟优化的最新基线，已保留并纳入后续版本提醒。

## 实际环境与处理

Docker在沙箱中被拒，经工具批准读到现有 `xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106`（8b2d3517c0a9）。加载conda后为Python3.7.12、PyTorch/NNDCT/XIR和vai_c_xir可用，但缺ONNX。首次读图因此失败，没有据此判断模型不兼容。ONNX1.12.0轮子沙箱下载失败，获准从官方PyPI取回后仅解入独立核查目录，未安装进原环境。后续禁网容器、只读根/源模型/目标架构，工作目录可写。

核对两份ONNX checker和原权重SHA，通过。目标arch指纹为0x101000056010407。SFace线性图88节点，含27Conv、29BN、27PReLU及末端50176→128Gemm等。

## 核心发现及验证

- 从固定ONNX逐层复原等价PyTorch网络，四组原OpenCV输出对照通过，未训练/修改原权重。CPU输入归一化边界同样对照通过。
- 实际VAI Inspector原图：30DPU/28CPU/1输入；27PReLU不支持PRELU，1FC参数缓冲需求3136大于2048。
- 第一版等价改写：141DPU/32CPU/1输入，保留独立ReLU、切片/布局限制，未当作全DPU成功。
- 第二版用残差PReLU和分组空间FC：**139DPU/0CPU/1输入**。四组浮点余弦最低约0.99999999947、最大绝对误差约1.987e-5；3项边界/分区/偏置测试通过，0.388秒。
- 原模型SHA未变化，原CPU身份与界面候选保留。本轮没有生成生产INT8模型或完整可部署xmodel；Inspector内部调用编译器不等于整图正式编译完成。

共享[结果与下一步](/home/ghmd/Win共享文件/协作任务/2026-10-18_双机联调/DPU身份模型_兼容性结果与下一步_20261018.md)及[核验摘要](/home/ghmd/Win共享文件/协作任务/2026-10-18_双机联调/evidence/ubuntu/identity-dpu-check-20261018/verification.json)已发布，24份脚本/摘要/报告总约1.40MB，复制哈希通过，不含参考图、输入/输出数组、身份库、权重或依赖目录。原始工作区 `/home/ghmd/aura-identity-dpu-check-20261018`。

## 下一步与边界

缺少已冻结的代表性身份校准/独立评测数据，四个对照样例不可替代。下一阶段准备真实授权样本，做INT8量化/精度比较及整图编译，再接单DPU所有者，低频身份与YOLO混跑。量化后模型ID/模板版本独立，阈值须标定。

离线阶段未连板；随后完成下列只读复核。本轮未真人登记、未测DPU利用率/混跑性能、未发起语音或部署服务。Windows的新流式GUI已较身份候选更新，上板需回读新目录与启动清单后合入，避免覆盖已接受语音成果。

## 串口结论纠正及实板只读复核

之前在沙箱内看不到ttyUSB，误写为板卡未连接；主机实际识别4路Xilinx UART，获准检查发现无其他串口占用。复用既有受审UART传输，UTC2026-10-19 01:43:26—01:43:30确认root、aarch64及原SD CID，完整响应SHA通过，终端回显已恢复。未发送部署、录音、播放或重启命令。

GTK PID1457/active，运行 `/home/root/aura-stream-playback-20261018/candidate-ec77f48a63de/runtime/aura`；相机PID987/active，旧相机运行根继续服务；快照detection_hz9.95、observation_age_ms78、last_inference_ms32.45、identity_recognition=false。快照不是DPU利用率或稳定性测试。当前身份确实尚未部署，连接不是阻塞点。

四份过滤状态/检查脚本已单独复制哈希核对，见共享证据 `identity-dpu-check-20261018/board-readonly/verification.json`。串口原文仅在本轮私有工作目录保留，无对话/图片/身份特征发布。

执行顺序更新：先基于实际新版流式界面合入CPU身份并完成真人闭环，得到基线及授权校准/独立评测数据，再推进INT8、整图编译、单DPU调度和混跑。当前只读状态核对不属于身份板级验收。
