# 可选 DPU 正常路径计时扩展

状态：软件候选，45项回归通过；未访问板卡、UART、生产服务或共享目录。本目录基于 `/home/ghmd/aura-dpu-audio-diagnosis-20261022/candidate/aura` 的四源码，仅修改 `board/vision/pipeline_metrics.py`。另外三个源码逐字节保持，用于完整部署清单。

原120秒诊断有295次成功wait且fault为0，只留下VART wall阶段统计，缺少正常调用线程CPU证据。本扩展保留每模型正常成功调用的六组累计数值：`execute_wall_ms`、`execute_thread_cpu_ms`、`wait_wall_ms`、`wait_thread_cpu_ms`、`optional_wall_ms`、`optional_thread_cpu_ms`，每组为 `count/sum_ms/min_ms/max_ms`。

入口仍为 `dpu_schedule.optional_diagnostics`，以及 `pipeline_metrics.optional_diagnostics` 的同一实例快照。新增 `normal_success_timings` 和 `maximum_normal_trace`。旧 `schema_version=aura-optional-diagnostics-1` 保留，新增扩展版本 `normal_timing_schema_version=aura-optional-normal-timings-1`。

正常成功定义：真实native wait已返回status 0、body未失败、未超过30ms占用或YOLO guard。拒绝、仅准入未调用native、原生失败、业务异常和真超限均不进入正常统计；初始估计偏差但未真超限仍可进入。全局只保留一份optional wall最大正常trace，跨YuNet/SFace共享容量1，等大保留先前记录；原fault ring容量8保持。按模型各6组累计数值，存储量与调用次数无关，不增加逐次历史、线程、日志或推理I/O。

trace增加 `calling_thread_native_id`；Python接口缺失或异常时为-1。线程CPU接口缺失时，trace仍为-1，CPU聚合count为0、sum为0、min/max为null，避免把缺失当负样本。快照返回独立副本。native成功/失败终结和finish防重复计数；新增统计失败会清理活动trace，并由原诊断错误计数处理，不替代业务结果或原异常。

默认仍关闭，需同时开启 `AURA_PIPELINE_METRICS=1` 与 `AURA_DPU_DIAGNOSTICS=1`。原30ms上限、YOLO guard、预算自适应及禁用/回退策略完全不改；scheduler/runtime/UI三个文件SHA与基线一致。计时边界沿用原诊断，因此normal统计汇总本身在finish尾部发生，不包含在已采样的optional wall里；它仍有少量调用开销，需要上板测量，不能声称零开销。

wall包括调用、等待、抢占、GIL等；调用线程CPU排除其他VART/runtime/内核线程。**wall减thread CPU不是DPU硬件时间**。本扩展没有硬件计时或抢占能力，native永久挂起时无法保证finish事件出现。

验证命令：`python3 run_tests.py`，Docker只读挂载现有依赖且断网，Vitis AI Python 3.7环境。最终45项通过：原诊断/计时/runtime 29项、原日志过滤6项、新正常路径10项。新增覆盖精确统计、跨模型最大trace、失效/超限排除、native_id可用/缺失/异常、重复终结、1000次有界存储、统计异常不破坏成功及清理。第一次新测试错误地假设Python3.7有get_native_id，已修正测试兼容逻辑；实现原本已支持缺失回退。

`candidate.patch` 只包含相对此次基线的差异；`patch-manifest.json` 给出四源码基线及候选SHA；`FILES.sha256` 冻结本目录交付。此候选未包含CPU减拷贝改动、SFace供给/身份迁移或音频维护协议，集成由主任务统一完成。正式日志与共享回执由主任务汇总，避免并行编辑。
