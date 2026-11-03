# 板载 CPU / DPU 占用实测与模型迁移分析

日期：2026-10-21（America/Los_Angeles，UTC22日）。本轮实板监测现有业务，未增加推理任务、修改生产源码/配置、切换位流、重启服务或发运动指令。

**实测：四核 ARM CPU 两段约15秒窗口分别为75.03%、82.63%；DPU计算单元的XRT驱动忙时约4%～5%，加权平均4.07%。目前更明显的负载在ARM侧。** 这是当前画面/界面状态下的短时结果，不代表所有交互场景的峰值，也不等于DSP乘加阵列效率或FPGA逻辑资源使用率。

## CPU：以四核合计100%计

第一段采样15.179秒，`/proc/stat`按各核前8项求总量，扣除idle和iowait；guest不重复加入。进程用utime/stime增量除以实际时间和4核。第二段为DPU统计同时采样15.004秒，监测本身可能有开销，未做严格的开销隔离。

| 项目 | 第一段 | 第二段 |
| --- | ---: | ---: |
| 全板CPU | 75.03% | 82.63% |
| 相机/检测/跟踪/身份进程1017 | 39.89% | 37.77% |
| 玩偶界面进程1460 | 23.92% | 23.93% |
| Xorg1160 | 3.89% | 3.93% |
| 常驻音频进程1528 | 3.85% | 3.92% |

第一段四核分别78.66%、72.78%、73.71%、74.90%，iowait约0.02%。相机约占1.60个核，界面约占0.96个核；top采用单核100%时会显示约160%与96%，不能与本表的全板百分比混淆。表中几个进程不能覆盖内核线程、IRQ和全部系统负载，不能强求相加等于全板占用。

相机进程包含采集、缩放/预后处理、跟踪、身份准备等；本轮没有逐函数CPU剖析，不能把它的全部CPU用量归给YuNet。界面、音频、跟踪和图像搬运开销也不会因为迁移一个网络就自动消失。

## DPU：实读XRT驱动任务忙闲统计

实际设备为`/sys/devices/platform/axi/axi:zyxclmm_drm/CU.3.auto`，cu_info确认单个DPUCZDX8G、地址0xa0010000、CTRL_HS。`kds_custat_raw`中的usage是任务次数，不能直接当百分比。

核对[XRT 2022.2 xrt_cu.c](https://github.com/Xilinx/XRT/blob/2022.2/src/runtime_src/core/common/drv/xrt_cu.c)与[cu.c](https://github.com/Xilinx/XRT/blob/2022.2/src/runtime_src/core/edge/drm/zocl/cu.c)后，通过驱动提供的`stats_begin` / `stat` / `stats_end`进行一次临时监测。读取stats_begin会开启软件统计，并非完全无副作用的普通文本读取；本轮没有直接读取或写入DPU控制寄存器。该统计将驱动队列/任务阶段的非空时间视作忙时，包含调度边界，不是独立的硬件周期计数器。

- 先确认无既有活动统计，再开启；预热1.1秒并丢弃首值。
- 15个约1秒有效窗口：idle=95%一次、96%十四次，busy=4%～5%，按窗口时长加权4.0669%。驱动输出为整数百分比，只报告约4%～5%，不暗示小数点后的精度。
- 有效窗口完成149个任务，约9.93次/秒；相机健康接口持续报告9.91Hz。
- 各观测点in_flight=0，末次Pending/Running/Submitted/Completed队列均为0，Bad state=0。它们表示观测点状态，不保证窗口内从未有排队。
- finally中读取stats_end关闭统计，之后完成计数停止增加；原生产相机/界面服务保持active、PID1017/1078不变、NRestarts=0，相机/检测错误为空。

这次DPU百分比来自独立的驱动忙闲统计，**没有用“推理调用耗时÷100ms”替代**。第一段16个相机遥测点的调用耗时中位15.01ms、范围11.21～30.58ms，包含CPU侧工作，不能当作DPU单次硬件时间。当前约96%驱动空闲支持进一步评估分时增加视觉模型，不代表整机吞吐可以提高25倍；CPU、DDR、调度时效仍可能先达到限制。

## 哪些模型适合迁到当前DPU

以下仅针对现有KV260、DPUCZDX8G/B4096、指纹0x101000056010407与Vitis AI3.0。模型兼容性依赖算子及其排列，不能仅按文件大小或ONNX格式判断。[AMD模型开发流程](https://xilinx.github.io/Vitis-AI/3.0/html/docs/workflow-model-development.html)

| 模型 | 结论 | 实际依据与下一道验收 |
| --- | --- | --- |
| YOLOX-Nano | 已在DPU，继续保留 | 当前9.91Hz人体检测；无新增迁移任务 |
| SFace | 最接近可正式接入，建议先完成 | 现有10.80MB工程xmodel已编译并实板执行。历史同进程固定图YOLO10Hz+SFace2Hz短测：100次YOLO、20次SFace，SFace中位7.68ms，无周期超时，输出与主机量化参考一致。仍需代表性人脸校准、独立真人准确率和真实相机调度验收 |
| YuNet | 值得评估卷积部分 | 本轮实读ONNX为43Conv/18Relu/5MaxPool，另有Shape/Gather/Reshape/Slice/Softmax等；尚无本模型B4096量化编译及板测。需冻结符合实际相机配置的输入尺寸，解码/NMS和坐标回映射保留CPU。能否降低当前板载CPU需同输入实测 |
| Light-ASD | 暂不做整网迁移 | 当前未接入；原论文包含2D/3D卷积与GRU，对当前卷积DPU需要拆分/改写验证，不因模型轻量就假定可直接部署 |
| GTCRN、Silero VAD v5（后续补查） | 当前配置保留Windows CPU | 最新活动语音前端已配置8795服务，分别做降噪与语音活动检测；此前表格漏列，未做当前DPU目标适配。本轮后续健康查询超时，不确认当前在线。详见[全模型概览](../2026-10-21_model_inventory/全模型概览_当前.md) |
| Paraformer | 本阶段保留Windows CPU | 当前语音链已形成，没有本目标可用xmodel和本项目迁移验收。用户既有约定为不新增板端语音模型/语音FPGA加速 |
| 27B对话模型 | 保留Windows GPU | 当前生成式27.3B/IQ4_XS执行路线不适配现有B4096工具链，没有可直接上板的实现；DPU空闲不改变这一点 |
| OmniVoice | 保留Windows GPU | 当前16步语音链已有接受记录，没有本目标DPU实现；不扩大到语音迁移 |
| ByteTrack、对齐/匹配、SQLite、UI/口型 | 继续CPU/现有路径 | 它们不是可以直接交给DPU执行的独立神经网络权重 |

Light-ASD结构依据[原论文](https://arxiv.org/abs/2303.04439)；最终算子支持按[AMD Vitis AI3.0目标算子表](https://docs.amd.com/r/3.0-English/ug1414-vitis-ai/Currently-Supported-Operators)及本目标Inspector/编译结果判断，不套用其他DPU/NPU的能力。

### 如何理解SFace与YuNet的优先级

当前活动代码明确：YuNet在板端检测，112×112对齐人脸PNG发往Windows的`/v1/identity/face-features`，SFace特征由Windows CPU返回。因而SFace迁回DPU的主要潜在收益是减少远程依赖和身份请求的网络波动，不是卸掉一个当前正在占ARM的SFace网络；它还会增加板端搬运/调度。当前Windows服务延迟和新方案端到端收益本轮未测。

若目标是尽快完成第二个DPU业务模型，先SFace；若主要目标是降低ARM负载，应优先测清YuNet、相机预后处理和界面的占比，再按收益排序。现有数据不支持承诺“迁SFace后CPU下降几十个百分点”。

SFace历史工程量化只使用有限公开参考，不是代表性校准；保存记录的单参考余弦约0.9703不能替代独立身份准确率。不能把固定图量化逐字节一致写成人脸身份精度已验收。生产登记库的浮点模板与新INT8特征是否兼容也需评估，必要时重新登记/标明模型版本。本轮未采集真人、修改数据库或上线候选。

后续建议在现有DPU所有者内统一调度，保持YOLO10Hz优先，SFace低频（先评估2Hz），有界队列并丢弃过期人脸任务；比较检测帧龄、CPU、DDR、身份延迟及真人准确率。历史固定图混跑不能替代这个当前业务验收。

## 工具异常、恢复和证据范围

`xdputil query`和`xdputil status`各等待12秒后超时，原因未确认；不能据此判DPU故障。相机仍正常推理。进一步检查发现工具包装器退出后遗留了两个孤儿查询进程；已核对准确PID、动词及父进程为1，仅终止本轮创建的这两个查询，未终止业务。事后服务PID/零重启/9.91Hz及错误为空保持。

原始UART、活动源码片段留在Ubuntu私有`/home/ghmd/aura-model-inventory-20261021/`。共享过滤证据见[cpu.json](cpu.json)、[dpu.json](dpu.json)、[verification.json](verification.json)。历史模型依据为[既有固定图混跑结果](../2026-10-18_identity_dpu/engineering-bee245f2a94e4d28/evidence/mixed-fixed-input/response.json)和[原量化限制](../2026-10-18_identity_dpu/engineering-bee245f2a94e4d28/quantized-metrics.json)。本轮无新量化/编译/部署/精度测试；Windows同步以其独立回执为准。
