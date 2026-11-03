# 项目11435的fit启动配置候选：未应用

本轮只准备候选与纯mock验证，没有执行ensure、重启、终止或模型加载。原文件位于`deliverables/2026-10-18_board_dialogue/project_ollama.py`，不在aura/tools；原始SHA256为`af3468333d92694525d9994934087d50932440ac3f4b755c26e19715a9a61ee9`，副本保留在before。上级6个核心候选中仅父侧授权的gpu_coordination.py曾修审阅问题，其余5个字节不变，之后重新冻结。

父侧已按现役Ollama 0.40.13及安装llama-server帮助确认`LLAMA_ARG_FIT_TARGET`单位为MiB；当前`GPU_OVERHEAD`不足以证明该路径实际预留。出处与版本限制见../../2026-10-29_conversation_research/OLLAMA_VRAM_RESERVATION.md。本候选不写GPU_OVERHEAD、不改全局环境，不设置未经测量的4GiB或其他生产初值。

## 集成位置与配置

本目录candidate使用**相对项目根**的路径。父侧应审阅并替换原`deliverables/2026-10-18_board_dialogue/project_ollama.py`，而不是复制到aura/tools。该模块仍由原launch_models.py导入ensure，默认HOST固定127.0.0.1:11435、D盘模型库、NO_CLOUD、单parallel/单loaded model、ctx2048；其他原环境和声线/模型参数不变。

可选配置路径为`aura/config/ollama_runtime.local.json`。文件不存在时，健康的11435仍直接复用，不增加GPU/CLI/CIM查询或自动重启。存在时只接受：

- schema_version=1。
- fit_target_mib：实际测量后确定的正整数MiB，必须小于当前GPU总量；本交付没有生产值。
- calibration_id：测量报告ID或哈希，不能为空，限定可审计字符。
- gpu_uuid：校准的物理GPU UUID；目前策略仅支持原单GPU主机，多GPU需另做布局校准。
- ollama_version：校准时本机精确版本；同时核对当前daemon/API和将启动的CLI版本。

结构见ollama_runtime.schema.json。父侧应基于TTS真实增量峰值、LLM加载/解码及额外余量确定值，写入实际来源ID；没有提供可误装的带数值生产配置。测试中的512MiB、GPU UUID和calibration_id全是mock夹具。

## 应用状态必须区分

新创建项目daemon时，仅在传入`Popen(env=...)`的项目环境副本增加`LLAMA_ARG_FIT_TARGET`。不会写用户/系统环境、调用11434或重启其他模型。继承的FIT若关闭，或CUDA选择与校准GPU冲突，会明确拒绝，不悄悄覆盖其他开关。

如果11435已健康，ensure只返回REUSED及`needs_controlled_restart=true`，不停止或重启它；保存配置并不改变旧进程环境。`launch_environment_applied`对复用进程始终为null。只有PID/创建时间/完整命令/可执行文件/监听与本启动器旧记录及同一配置全部相符时，才报告`policy_recorded_for_current_process_creation=true`，其含义仍只是“匹配创建记录”，不是重新读取了当前环境块。

新创建的daemon可以报告环境已传入；`effective_runner_budget_verified`仍固定false，父侧必须用实际27B runner、offload布局、模型驻留、峰值与延迟证明fit效果。该目标不是物理VRAM隔离。

## 父侧受控重启所需所有权和检查

代码提供只读inspect_ownership：固定查询11435，返回PID、CreationDate UTC、exe、完整command line、parent PID、监听地址/端口/owner，并要求唯一127.0.0.1:11435。新创建记录还绑定exe SHA和GPU/版本、配置SHA、calibration_id。仅PID文件不构成可终止凭据。

`inspect_restart_ownership.py`是父侧可选只读助手，只调用所有权、/api/version与/api/ps，不调用ensure；本子代理尚未实际执行它。执行父侧操作前，应再次核对这四类字段与当前独立基线及历史项目入口：

1. PID、CreationDate与完整exe/serve命令保持；监听11435唯一且属于该PID。任何并行变化都退出重查，不按旧PID操作。
2. 原UI空闲、IDLE_READY、监听/麦克风/跟随关闭；语音host不忙，所属TTS已结束或完成原暖态取消交接。保留其他模型进程、11434的PID/创建时间及其/api/ps快照。
3. 若确有校准配置变更，由父侧只处理已确认所属11435及其可验证runner。不能按llama-server.exe名称批量处理，CPU VLM8810也用这个程序。
4. 新daemon创建后比对新PID/CreationDate/exe与唯一11435，确认API版本和创建记录、配置SHA。再以原27B/量化/ctx2048/单slot公开非缓存问答读取实际GPU层/CPU与GPU buffer、min free和TTS峰值；比较时延代价。不要凭“env存在”或“加载成功”填fit验收通过。
5. 其他模型、11434、D盘路径、数据库和板端状态保持。若常规对话因低余量持续拒绝，容量/布局还没解决，不能把有界失败当优化完成。

本候选没有终止/重启实现；受控操作由父代理完成。环境传递与fit的作用边界应结合官方版本研究验证，不暴露完整环境块或私有模板。

## 验证

extras/tests.xml与tests.log：27项纯mock通过，覆盖无配置健康复用、新配置只标待重启、相同创建记录、PID重用、版本/GPU/容量/继承开关错配、只给项目子进程的环境、原flags/D盘保持、端口占用、新端点归属、只读所有权字段。没有真实重启、模型加载或峰值测试。上级核心79项结果单列，不与本组简单累计。
