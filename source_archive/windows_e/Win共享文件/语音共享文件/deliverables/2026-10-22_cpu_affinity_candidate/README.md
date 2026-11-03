# CPU核分配单变量候选：只准备、未上板

2026-10-22。用户最新允许两个终端；本终端只在本目录制作候选与本机验证，主任务独占UART、板卡和共享入口。没有启动DPU、相机或音频，没有修改生产配置、模型、GUI、内核或共享回执。候选默认关闭，尚无板卡性能收益或稳定性结论。

目的：在原5ms解释器线程切换设置下，单独检验推理调用线程与图像准备线程的核分配，是否影响YuNet偶发的30ms墙钟占用长尾。CPU亲和性不消除GIL、VART/硬件等待，也不保证操作系统调度期限。

## 文件与精确作用范围

- `affinity_camera_launcher.py`：包装固定SHA的原`tools/board_camera_motion.py`；显式环境开关`AURA_EXPERIMENT_AFFINITY=1`才启用。未设置或为`0`时不安装线程hook、不设置mask、不创建日志，继续原入口和参数。
- `thread_affinity_trial.py`：校验CPU集合、建立启动屏障、应用/读回/恢复mask、记录进程与线程身份。所有写亲和性调用均为`sched_setaffinity(0, mask)`，由被绑定线程自己执行；不会向其他PID或TID发写操作。
- `example_policy_kv260.json`：仅为待审核策略，推理角色使用`[2,3]`，准备角色使用`[0,1]`。不是已验证的最佳分配；不能凭此前3秒CPU快照声称某核空闲。
- `source-reference/aura/`：6份冻结源码用于SHA与AST角色审查；测试不导入这些业务模块，不执行其中的设备或模型代码。
- `test_affinity_trial.py`、`evidence/owned-child-affinity.json`和`test-results-final.txt`：软件验证、仅数字的本机自有子进程证据及最终27项结果。

精确匹配Python线程名称、目标函数源码路径和`__qualname__`，并在进入原入口前核对源码SHA。不得仅按Linux截断后的comm猜角色。

| Python线程名 | 已核实目标函数 | 本候选分组 |
| --- | --- | --- |
| `camera-detection` | `ui_camera_service.run.<locals>.inference` | YOLO预后处理及DPU调用线程 |
| `camera-face-targets` | `FaceTargetService.work` | YuNet预后处理及DPU调用线程 |
| `camera-live-preview` | `ui_camera_service.run.<locals>.preview` | 画面绘制、JPEG编码和发布 |
| `camera-identity` | `IdentityService.work` | 人脸对齐、PNG编码和原Windows请求 |

本轮只接受上述双模型4角色。`sface-dpu-shadow`和`sface-crop-prepare`名称保留在识别表中，用来发现意外启用后拒绝启动；策略不允许给它们配置mask。三模型6角色一起等待会形成依赖环：`camera-identity`的factory中才创建shadow和producer，故三模型须另行设计，不能直接扩大本屏障。

## 准入、失败与恢复

启动时必须显式提供绝对、非符号链接的JSON策略文件；其`expected_process_cpus`须与当前进程`sched_getaffinity(0)`完全一致。每个角色的mask必须非空、不含重复/布尔/负数/越界CPU，且为当前允许集合的子集；推理与准备分组必须不相交。每次设置前再次读取调用线程mask，设置后立即读回，内核裁剪或CPU条件变化均视为失败。

4个角色先各自设置并读回，全部成功后才同时放行原目标函数。第一个角色进入后8秒内缺少任何角色、来源/名称不符、旧mask不允许所选CPU、设置/读回/日志失败，都不会放行部分目标函数。已尝试设置的角色各自在自己的finally中恢复旧mask并读回；随后明确退出本实验进程，退出码70。恢复无法确认、或其他线程未及时退出时，也退出本实验进程，避免悄悄继续半配置。这个屏障约束选中的Python目标函数，原主线程仍可能已创建GStreamer对象。

日志以独占创建、0600权限的`affinity-<PID>.jsonl`保存：进程PID/启动计数、当前TID/线程启动计数、角色、旧mask、请求mask、实际mask、恢复结果、提交/失败事件。写操作始终只针对当前线程；没有在事后拿旧TID重新绑定的路径，因此不对已退出或被复用的TID操作。进程返回时恢复`sys.argv`和`threading.Thread.run`；仍有选中作用域未退出则有界等待并退出本实验进程。原目标函数自己的异常在恢复mask后按原样传播。

**内核继承边界：** 由主线程创建的未知线程保持主线程宽mask；由已绑定角色后来创建的Python或native线程，可能继承创建者的窄mask。本机自有子进程已明确演示两种情况。候选不猜这些线程的职责、不向它们写mask，也不能保证继承者跟随创建者恢复。实际OpenCV/VART/GStreamer后代线程是否存在须在隔离板测中观察；退出实验进程会结束其全部线程。不能把这个方案称为给DPU或推理“独占CPU核”，其他进程、内核线程和本进程未绑定线程仍可能使用这些核。

本包装不切换服务、不承担外部回退，正式试验仍须由主任务现有独立回退定时器和RuntimeMax保护。GIL实验启动器不能与其叠加；检测到`AURA_EXPERIMENT_GIL_MS`环境变量、或实际解释器间隔不是原5ms即拒绝，候选本身不修改GIL。

## 主任务后续接入点：尚未执行

1. 维持原5ms解释器设置，复制现有14源诊断候选到独立`/home/root/aura-dpu-vision-20261021/affinity-live/<release>/runtime/aura`；保留模型、原Windows正式身份库、30ms硬上限和5ms guard。不要覆盖活动版本。`source-reference`只作审查，不能拿整目录当部署补丁。
2. 将两个新模块放在同一独立发布目录；在候选服务中设置`AURA_EXPERIMENT_AFFINITY=1`及`AURA_EXPERIMENT_AFFINITY_POLICY=<绝对策略路径>`，以`python3 affinity_camera_launcher.py <候选aura/tools/board_camera_motion.py> --config <候选配置>`启动。固定入口SHA为`1e0e6f0b8881c2d4d4cf81a2527e79d063e673eeba1d069e33bdde2608303005`；角色SHA见启动器和`source-provenance.json`。
3. 启动前只读确认板端允许CPU集合、同版角色及两模型配置；策略的`[0,1,2,3]`不匹配实际集合时必须重新审核，不自动选核。启动后检查4个APPLIED、ALL_ROLES_COMMITTED及TID/旧新mask，再进入稳态测量窗口；启动屏障带来的初始加载时序变化不能冒充稳态加速。
4. 先120秒，同一输入/窗口尽量对照原5ms基线，测YOLO≥9Hz、YuNet完成数、30ms真实超限、CPU核秒、帧龄和新USB告警；通过再考虑600秒。主线GIL 600秒虽无真超限，但稀疏样本发现3次face age≥1000ms，亲和性实验必须独立报告TTL时效，不能只看“无超限”。
5. 结束后恢复原服务，核验原源/配置/模型/身份库、GUI及Xserver PID、相关timer和XRT统计关闭。保存本候选的RESTORED/CLOSED或明确失败退出记录。不要同时启用1ms GIL、SFace影子或新音频维护。

以上均为接入计划，本目录未执行任何一条板卡操作。主线GIL成功证据归主任务，本候选不据此预报亲和性收益。

## 软件验证

本机命令：`python3 -B -m unittest -v test_affinity_trial`，最终27项通过。覆盖严格CPU集合、启动事务、缺角色期限、部分设置失败、内核mask裁剪、记录失败、原mask恢复失败、身份变化、原目标异常、重复角色和退出期间活动作用域。

真实启用接线使用本机自有短子进程：临时固定SHA入口与4份精确函数绑定，走`launch → Thread.run hook → 4角色屏障 → 原target → 各自恢复`；核对父进程、子进程主线程、主线程创建的未知线程mask不变，以及`sys.argv`/hook/GIL恢复。另一个自有子进程故意缺1角色，3份mask全部恢复后退出70，没有放行选中目标。未知后代的mask继承边界另有实际记录。两次运行都是本机合成夹具，不是KV260、DPU或模型验收。

`test-results.txt`是收紧三模型范围前同27项的中间成功记录；最终以`test-results-final.txt`为准，不叠加计数。只做了必要变化后的复跑，没有重复业务模型回归。
