# 当前接续：已部署，等待本版集中真人听音

先读README.md、verification.json、PROGRESS.json。不要按CONTINUE.pre_deployment.md的“尚未部署”继续重跑准备或切换。

现役板端根/home/root/aura-audio-animation-20261029/2a62bf25b0994029a1ff0f23f0b9720e/runtime，配置/home/root/aura-audio-animation-20261029/2a62bf25b0994029a1ff0f23f0b9720e/startup/config.json，279组件；CPU画面revision 763d0b05a67a79ff6f8a6d9d5e2a67cc9cc060181499cef7a416bccdf7315bac；Windows语音仍r9/5a4fa28e8679ffd24b61e940455e7dd2341c02c8ae70e8997aa5682c157471f3。本轮只重启所属CPU8796和单板端UI；其他模型、相机进程/epoch、机械字节和已有systemd覆盖保留。

软件与自动验证已通过，听音/真人动作观感待用户反馈。当前监听、麦克风、跟随关闭；不得自动开麦、播放有声内容或启用运动。下一步按README最后的三项集中复测处理实际反馈，不重复无人测试来冒充真人验收。

任何后续变更都重新从/proc/MainPID/cmdline发现实际配置，核对279精确pin和当前pending unit；禁止只看daemon-reload后的unit。修改前两次确认IDLE/IDLE_READY、监听/麦克风false、跟随false且无活动运动，保护其他聊天的并行更新。新root采用startup/config.json布局以保持manual_live_config自己的校验路径。

保留原机械FAULT和null位置。board boot仍605eaf50-c66a-4559-bfc9-5ae177e0f305；benchmark FPGA/VART与wide驱动不匹配，禁止照抄旧boot/1604µs或“修正”绑定来恢复运动。LLM数据只在D盘，不卸载其他模型，不复制私有身份库、原始PCM/现场照片到E盘。

数据基线需每次重新通过独立隐藏WMI备份和对比，真实AppData视图与工具视图可能不同。当前153/311等仅本轮时点，不得覆盖用户后续新增资料。原始来源逐表严格相等；前一service_recovery的过期缓存解释属于旧轮，不套用来忽略本轮新变化。

正常重启画面用项目start_portrait.ps1或本目录start_host.ps1，只复用健康且PID/创建时间/启动命令匹配的所属8796。旧2026-10-27画面/2026-10-29_service_recovery脚本仍验证81fd历史revision，不能直接重跑覆盖本版。start_voice.ps1只检查新的canonical host config，其余语音启动行为保持。

回退必须协调两端，先读deployment.json/source_installation.json并再次核对实际入口、空闲、所有源SHA和无新并行更新。只撤销deployment.json记录的本次systemd覆盖，恢复原pending startup-speed入口，不删除其他覆盖；之后rollback_windows.py仅恢复本次记录的Windows源与原CPU入口。该脚本不是整套板端回退，禁止在新板端UI仍需要763d资源时单独执行。备份在source_backup，旧快照/旧发布完整保留；不回退记忆库或机械绑定。

音频参考出现永久gap时不能退回原能量判定；本次有界非阻塞上报不得改回GLib线程同步print。MAX_APPSRC_BYTES/current-level-bytes保护与PCM时钟/哈希/取消边界保留。空闲起步13份过期参考未在静音长句中增长；声音仍断续时优先检查audio_output与turn.completed中的供音间隔、缺料包、排队时长和IPC指标，不凭感受宣称TTS/LLM已提速。

原生背压199.98→24.57ms、真实静音长句18.28ms/0欠载/0重排、实际UI断线7.934fps并恢复16fps已保存。说话长帧严格门槛仍失败（P95~80/P99~158ms），不可扩大为全项目完成。未创建代理、计划任务或心跳；静音试验临时回退timer已停止。
