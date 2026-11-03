同Paraformer四线程独立候选；未发布、未由本代理执行设备操作

唯一生产源码候选：after/board/runtime/audio/board_asr.py，SHA e7af12834461fbb9582dc8ac0c63792569c61d7a56beba5f799f4616b858f447。
父源4edb865881c887d6a290a02e078e14386bd95d017b79820b143b5a1e329997c3；仅最大线程3改4及对应错误文案，默认仍2。生产factory已有num_threads=value.get('asr_threads',2)透传，不需要覆盖已上线紧凑协议6源、记忆策略、GUI或前端。模型/令牌SHA、greedy_search、CPU provider、特征80、16k原PCM、20秒上限、锁/取消/期限校验均原字节。

probe_asr_abba.py为root执行的板端脚本，默认inspect，只有--run或内部独立槽入口才构造ASR；本代理未执行。不要把本地测试当板端准入。
  python3 -B probe_asr_abba.py --boot-id <fresh boot> --ui-pid <fresh supervisor> --ui-birth <start ticks> --camera-pid <fresh camera> --camera-birth <start ticks> --candidate <uploaded candidate path> --candidate-sha256 e7af12834461fbb9582dc8ac0c63792569c61d7a56beba5f799f4616b858f447
同参数再加--run才测量。默认startup为v14的39b102a4a505db491cf06b90e3a5232bfb656c79cb0a3c221551d76d414a9a0a；若现役变了，须主控重新核来源再传完整--startup-sha256，不猜旧PID。root_runner.py由主控独占，不纳入本交付冻结。

完整GUI和相机保留；必须先由主控暂停监听，无mic/播放/活跃识别或生成。脚本只读systemd、/proc、原8783状态及8797 health，不POST、不重启、不改设置。配置pin使用component_sha256['config/board_avatar_gtk.json']（gui_sha256是入口脚本pin，不能当配置）；要求GUI顶层stable_avatar_fps=16和现役asr_threads=3。启动前和每槽前严格要求模型active=false/pending0；MemAvailable默认至少512MiB（可提高），模型构造后再核；四个可用逻辑核、normal nice0，只读亲和性、不设置。

序列3/4/4/3，每槽新解释器、唯一额外ASR session，1次同公开WAV预热+1次计时，模型加载另计，退出回收后才下槽；每槽80秒上限，仅自己超时子进程可清理，不处理生产进程。沿用公开0.wav的固定SHA/16k mono PCM16，模型和tokens仍原SHA，未读私有音频。正式ASR仍resident，所以多一份候选session的RAM影响不可隐去；记录槽前后MemAvailable及子进程peakRSS。与实际GUI进程内解码的GIL/调度环境不完全相同，不能直接当正式效果。

所有输出仅metadata。识别正文不输出；公开结果hash仅用于比对四槽一致。保留每槽wall/processCPU/load/RSS及原owner/worker计数；UI和相机PID/birth/完整cmdline hash须保持。memory完成/丢弃计数变化或槽后发现模型busy时保留耗时并标background_changed；最终CONTAMINATED_NO_GAIN_CLAIM，不输出提速结论。下一槽前若忙仍拒绝，保留已经完成的槽。无法观察两个采样间已开始又结束的短后台任务；不能据前后空闲声称绝对无干扰。

是否值得测
实际既有CPU快照有cpu0–cpu3，监听空闲整体82.53%忙，camera99.64%单核等效、GUI88.14%、前端97.70%、播放器15.74%。半双工在ASR阶段释放采集计算，不能把监听时前端97.7%持续叠到ASR；但相机/GUI/播放器仍约2核等效，3线程已有竞争，第四线程可能收益有限甚至更慢。既有5.614625秒公开样本在关闭GUI条件下2线程4700/4718ms、3线程3741/4283ms；不是本候选或完整负载数据。理想完全并行时3→4的理论上限为解码部分25%减少，实际应更低；不承诺缩短当前首包8–9秒中的多少。

建议只做这一组有界对照。需要两对方向一致、差异超过本组波动，转写一致，才值得主控单文件+asr_threads=4的正常受控发布候选；差异很小/反向/受干扰时保留3。发布前仍需完整GUI实际ASR与首包对照、16fps目标/GUI faults、视觉与身份有效性、采集/暂停/恢复/取消/完整播放ACK门，不能以独立进程公共WAV替代它们。

动态优先级只读结论
现BoardParaformer没有nice/亲和性操作；正常GUI及其ORT线程保持0。现-10只属于独立采集前端，半双工ASR时该采集停用。给调用transcribe的Python线程临时nice并不能证明所有已创建ORT线程一起改变；进程级修改会牵连GTK和身份，不能直接复用。若四线程无明显收益，后续只能在取得ASR各TID的runtime/runqueue_wait/迁移证据后另评估有界优先级作用域；本轮不绑核、不提优先级、不扩大队列、不降视觉/帧率。

本地验证：15主测试/9子例通过0.23秒。含3/4参数原样、默认2、非法bool/0/5以上拒绝、模型hash门、原transcribe及factory其余AST一致、3/4/4/3顺序/结果一致、背景变化保留数值不声称收益、固定错误码不泄漏异常正文、默认inspect无模型/子进程、owned子进程等待/超时清理fake。Python3.9 AST通过。没有模型推理、设备、服务或真实库操作。
