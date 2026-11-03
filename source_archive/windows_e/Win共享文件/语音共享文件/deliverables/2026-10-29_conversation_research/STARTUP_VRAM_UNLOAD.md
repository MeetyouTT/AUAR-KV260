# 冷TTS启动时只释放项目27B缓存

结论：官方API及现役Ollama v0.40.13均支持。仅在Windows语音8792尚未启动、项目11435所属进程已核对且无在途请求的启动阶段，可对项目27B发送以下JSON，省略prompt。它释放运行缓存，不删除D盘权重；不要设成每轮操作，也不要改11434。官方FAQ给出了空请求加keep_alive=0的卸载用法。[官方FAQ](https://docs.ollama.com/faq#how-do-i-keep-a-model-loaded-in-memory-or-make-it-unload-immediately)

```text
POST http://127.0.0.1:11435/api/generate
Content-Type: application/json

{"model":"aura-qwen3.8-27b-abliterated:iq4_xs","keep_alive":0,"stream":false}
```

版本钉住的代码在空prompt/零keep_alive时先走expire分支，返回done=true、done_reason=unload、空response，然后结束，不进入生成路径。stream=false合法。[v0.40.13 GenerateHandler](https://github.com/ollama/ollama/blob/v0.40.13/server/routes.go#L445-L455)、[generate请求字段](https://docs.ollama.com/api/generate)

expireRunner按该daemon内部的模型key或同名runner设过期；实际卸载由其调度线程完成，仍有引用时会等当前请求完成。因此200/unload不是显存释放凭据，必须在原总deadline内等11435/api/ps为空且设备global free达标。只调用11435不会向11434的调度器发命令，二者仍共用物理GPU。[v0.40.13 expireRunner与过期处理](https://github.com/ollama/ollama/blob/v0.40.13/server/sched.go#L1648-L1674)、[官方/api/ps](https://docs.ollama.com/api/ps)

## 与本次真实容量的关系

父侧给出的实测：冷TTS peak_reserved=4,972,347,392 bytes=4742MiB，baseline=0且含初始化；稳态短句额外reserved=153,092,096 bytes=146MiB。27B驻留后global free约250MiB，单次最低210MiB，首PCM4.343秒。此处只引用父侧结果，没有在本子任务重复推理或实机A/B。

启动时以经过校准的tts_cold_extra_mib+reserve_mib判断，稳态按tts_extra_mib运行。短暂释放本项目27B缓存让冷TTS先初始化，再按原warmup顺序加载27B，可以避免为了罕见冷峰而永久预留整份4742MiB。这是待父侧实机验收的布局策略，不能从短句146MiB推断长句峰值或全部模型并发已安全。fit-target=2048实验由父侧独立执行，本报告未执行。

## 候选及精确接口

- candidate/tools/service_instance_lock.py：纯stdlib，Windows msvcrt.LK_NBLCK锁第0字节，非Windows fcntl.LOCK_EX|LOCK_NB；立即拒绝竞争。只打开自己的稳定本地lockfile，不写内容、不截断、不删文件，不信PID文本。退出/句柄关闭自动释放；句柄不继承给子进程。
- candidate/tools/startup_vram.py：纯stdlib，不在导入或构造时访问API/模型。只有显式调用prepare_cold_tts_startup才可能发一次固定卸载请求。
- tests/test_service_instance_lock.py、tests/test_startup_vram.py：真实Windows临时文件/子进程竞争，另以mock覆盖fcntl协议；启动辅助全部使用假API、假时钟与假显存，不连接真实端口或设备。

```python
prepare_cold_tts_startup(
    config, policy_dict, *, lock, deadline, expected_owner,
    verify_owner, voice_is_listening, memory_sample, api=None,
    clock=time.monotonic, wait=time.sleep,
)

ProjectOllamaOwner(
    pid, created, executable, host, models_directory, no_inflight
)
```

config中的host和model必须分别是固定127.0.0.1:11435和当前项目27B；OwnerEvidence中的模型库必须为D:\AIModels\Ollama-AURA。新模型/存储位置需要重新审阅候选常量，不能传任意模型来复用卸载接口。

expected_owner是父侧已核对的所属daemon身份；verify_owner(deadline)必须重新返回同一ProjectOllamaOwner（含PID、稳定进程创建标识、exe、host、D盘库、no_inflight=True）。父侧可适配project_ollama.inspect_ownership及本轮已记录的config/exe/create。**进程归属不等于无在途请求**；回调必须另有启动调度/请求所有权依据，不能从/api/ps空、8792未监听或仅PID存活构造“无在途证明”。不清楚时应拒绝该操作。

voice_is_listening(deadline)返回实际8792是否监听的字面bool；True或未知均拒绝操作。memory_sample(deadline)可适配GPU候选NvidiaMemoryProbe.read(timeout=剩余预算)，返回其MemorySample：gpu_uuid/free_mib/observed_at；UUID须匹配校准值，年龄不超过750ms。三个回调都必须在自己的锁、子进程和I/O中扣原deadline，函数返回后再检查超时并不补救无界回调。

policy_dict来自已验证的GPU配置。observe返回skipped_observe；无校准标识/UUID/有效冷预算返回skipped_uncalibrated；均不访问API、不卸载，capacity_verified=False。强制策略下先确认11435仅包含项目27B，再取实际free；不足才重新核对所属、模型集合和free。期间free恢复则保留缓存。真正卸载后等/api/ps空与free达标同时满足；最多发送一次卸载，不重试强杀，不删权重，不增加deadline。

API适配器只有GET /api/ps及POST /api/generate两路由，固定127.0.0.1:11435。连接、头、整个有界响应体共用原绝对deadline，并用socket shutdown timer防慢流；不使用默认Ollama端口、CLI stop、全局keep_alive环境变量或模型删除接口。

## 父侧集成位置

只由ModelHost.main在任何ModelHost/ASR/TTS模型构造前获取生命周期锁，启动辅助、模型构造、warmup、监听到退出清理都处于该锁内。lockfile必须放在所有版本共同使用的稳定本地目录，例如当前稳定args.root中的voice8792.instance.lock；不要放到每轮新stage或不同run-id目录。launcher不能持同一把锁等待child ready，否则会互等。旧的不合作版本仍需实际8792检查，文件锁本身不能约束它。

```python
# 接入示例；父侧提供已有的配置、OwnerEvidence与有界检查适配器。
# startup_deadline在原启动入口只计算一次，不能在卸载或warmup后重置。
with ServiceInstanceLock(stable_runtime_root / 'voice8792.instance.lock') as startup_lock:
    startup_evidence = prepare_cold_tts_startup(
        config, gpu_policy_dict, lock=startup_lock, deadline=startup_deadline,
        expected_owner=expected_owner, verify_owner=verify_owner,
        voice_is_listening=voice_is_listening, memory_sample=memory_sample,
    )
    models = ModelHost(args.root, args.voice_python, accepted_tts_path)
    try:
        # 继续原ASR初始化、warmup与8792监听；沿用原剩余总预算。
        run_existing_service(models, startup_deadline)
    finally:
        close_existing_service_and_models(models)
```

以上是父侧手工整合接点示例，不是已接入的业务补丁。当前launch_models的ready deadline在spawn之后计算；如要求覆盖整个启动，应提前建立同一个原deadline并传到子进程，不能另给helper一份新预算。需将新源纳入指纹/源码能力清单；不能沿用旧指纹声称已加载。

## 验证与边界

最终候选40项测试通过：12项锁、28项启动辅助。真实Windows验证包括空文件锁、4进程同时竞争只有1个持锁者，以及os._exit绕过finally后OS自动释放。非Windows只mock验证fcntl调用协议，未宣称完成Linux原生测试。锁协议依据[Python msvcrt文档](https://docs.python.org/3/library/msvcrt.html#msvcrt.locking)、[Microsoft _locking说明](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/locking?view=msvc-170)、[Python fcntl文档](https://docs.python.org/3/library/fcntl.html#fcntl.flock)。

首次测试因默认沙箱Temp ACL导致创建后无法访问/清理；记录保留在STARTUP_TEST_FIRST_FAILURE.md。最终夹具全部显式放在本交付tests目录，验证解析路径后清理自身临时目录。没有修改共享启动代码、部署、调用真实Ollama、关闭模型、开启麦克风/播放/运动。

本地文件锁是合作式单实例防护，不能阻止不使用它的旧程序或直接HTTP客户端；POSIX下运行期间不得unlink/替换lockfile。采样后外部进程仍可能分配显存，故这不是物理VRAM隔离或永不OOM保证。冷TTS恢复后的真实初始化、27B重新布局、短中长非缓存合成与其他模型共存仍由父侧整合验收。
