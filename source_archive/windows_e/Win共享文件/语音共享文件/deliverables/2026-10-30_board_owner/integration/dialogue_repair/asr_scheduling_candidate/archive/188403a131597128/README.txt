原OfflineParaformer3线程调度ABBA（仅探针候选，不是正式actor）

默认inspect，仅已有guard读取配置、/proc和状态/health；显式--run固定四槽nice[0,-5,-5,0]。每槽fresh child、原模型、原0.wav、num_threads=3，没有可修改线程数或扩大nice的参数。父进程始终nice0；正式GUI/相机/前端/affinity、模型、队列、身份、记忆不改，不打开麦克风/播放/私库。

输入钉住：guard210925ca…；旧public pipeline ac0af16c…（只复用ProbeProcessPriority，绝不调用其模型探针）；当前BoardParaformer源4edb8658…；model f36a0433…、tokens59aba887…；公开0.wav SHA1a6bf940…，5.614625秒16kHz/monoPCM16。完整SHA见HANDOFF。

每槽：nice0 guard→加载模型→headroom与nice0 guard→数值计数before→仅本child的已建ORT及新任务使用原ProbeProcessPriority(0或-5)→一次warmup→一次计时transcribe→恢复并确认→数值计数after→nice0 guard。load、warmup、timed decode各列，只有timed decode进入两组中位数。计数区间围绕warmup+decode及邻近metadata，排除模型加载，不等于物理渲染FPS。

每槽新的session/PGID；最多120秒，退出前核PID/birth及PGID==PID且不是父组，才可SIGKILL本槽。成功及异常后核组已不存在；失去leader归属而仍有残组只报告owned_group_remaining并停止ABBA，不猜测或信号其它进程。外层root总期限应覆盖4×120秒加metadata/清理上限；若外层强杀父探针，root也需按记录清理这四槽中仍存在的独立PGID，不能只杀父组。正常期望约2–3分钟，不保证重载下固定时长。

报告：slot前后memory/model忙状态、组归属/恢复记录、固定公开结果的hash/字数（不输出文本）、时延/CPU/RSS。GUI只白名单avatar_display.frames/paint_at/target_fps；root可明确传--camera-health-port 8790，读取/health的capture_frames/detected_frames/preview_frames/observation_frame_id/capture_age_ms/observation_age_ms/capture_hz/detection_hz/preview_hz/last_inference_ms。无字段就标unavailable，不取identity/people/图像或猜测FPS。整体前后memory变化也记录，覆盖槽间摘要活动。

任一后台变化、warmup/实测转写不一致、跨槽输出hash不同、槽不完整，均NO_GAIN；失败保留已完成rows，无自动重试。中位数与descriptive_reduction_percent仅描述，causal_gain_claimed永远false；不声称真人首声/整机收益。

root调用（已有守护/公开资源不复制模型）：
python3 -B probe_asr_scheduling.py --pipeline-source <已钉住ac0af16c公共pipeline文件> --startup-sha256 <fresh startup> --boot-id <fresh boot> --ui-pid <supervisor PID> --ui-birth <start_ticks> --camera-pid <camera PID> --camera-birth <start_ticks> --camera-health-port 8790
上行先inspect；加--run执行四槽。guard-source默认原已部署210925路径，可明确改为同SHA文件。默认MemAvailable门1500MiB，root选择的门不能低于512；模型加载后再次检查。

本地10主测试通过，8个非法nice输入子例。假API验证原priority helper只改自有任务、异常及新ORT任务恢复、权限失败回滚；实际slot函数验证model在0构造、warm/decode在-5、guard在恢复后；核PID/birth/PGID拒错、固定3、精确数值白名单、部分结果保留和NO_GAIN口径。仅临时公开fixture/假模型，无ARM/真实模型或设备测试。
测试：python -m unittest discover -s <本目录>/tests -p test_probe.py -v
