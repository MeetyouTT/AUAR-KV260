# 只读冷启动预检与生命周期锁

候选接口与父侧约定一致：

```python
with voice_startup_guard(
    AURA, args.root, host=OLLAMA_HOST, model=MODEL,
    listen=args.listen, port=args.port, deadline=startup_deadline,
) as startup_evidence:
    # 在此构造ModelHost/ASR，按原剩余deadline预热、监听、运行，最后close。
    ...
```

candidate/tools/voice_startup_guard.py依赖之前40测试候选中的tools/service_instance_lock.py（SHA见manifest），两者须以相同tools包名导入。args.root必须是已存在、跨版本稳定的本地运行目录；锁是其中voice8792.instance.lock，不能随run-id或stage变化。context持锁直到服务close后退出；launcher不能持同一锁等child ready。

预检只读配置、进程元数据、可执行文件和设备显存。没有卸载API、提交凭据、等待空闲循环或进程操作。只允许GET固定127.0.0.1:11435的/api/version和/api/ps；空列表和8792未监听始终不等于无在途，返回证据no_inflight_proven=False、automatic_unload=False。

强制且校准有效时，严格核对：

- board_dialogue_model、D盘Ollama目录、GpuPolicy校验及冷/稳态预算分离。
- 已安装project_ollama_process.json与当前11435实际PID、creation、exe、完整command line、127.0.0.1专属listeners。
- ollama_runtime原始配置SHA、记录中的runtime policy、bindings中的exe SHA/version/GPU UUID和容量；当前API版本、实际exe流式SHA均要匹配。
- /api/ps仅为空或项目27B；检查后再次核对daemon身份、所有配置原字节SHA及8792真实listener，再取新鲜设备显存。

PowerShell只使用固定本地只读查询，子进程timeout=min(5,原剩余预算)。8792查询先成功读取Listen表再过滤8792，查询失败不会冒充“未监听”。HTTP连接、头、全响应体共用min(2秒,原剩余预算)，socket timer防慢流。exe分块SHA、配置读取和每阶段均检查同一个原deadline；不创建新phase预算。传入超过300秒的新预算会拒绝。

observe返回skipped_observe并保持生命周期锁、检查8792，capacity_verified=False；未校准的无强制配置不提供容量保证，非法强制GpuPolicy直接拒绝。默认严格策略需要父侧已合并带tts_cold_extra_mib的GpuPolicy，不能用旧schema放宽校验。

容量不足立即抛ColdStartupCapacityError，其evidence含gpu/cold_sample/extra。例如free2098、cold4742、reserve128时，明确需要4870MiB而只有2098MiB，并标controlled_reload_required=True；不进入ModelHost构造，不等到超时，更不会假造no_inflight。父控制器只有在原唯一owned voice ready/busy=false、GPU active/queued=0，受控停止并确认无listener后，才可由其既有受控路径单次释放自身27B缓存。此候选不实现或代替该授权路径。

父侧300秒启动deadline必须在原入口只算一次。VoiceWorker.warmup可传min(240,剩余秒数)，剩余<=0先失败；LLM预热需min(120秒局部上限,同一全局deadline)，thinking/social cues也沿用全局剩余预算。候选不能凭预热后才检查来约束旧版无界预热调用；这些业务接点由父侧负责。

本候选26项适配测试通过，包括真实本地生命周期锁、2098MiB立即不足、成功保持锁到清理、空/api/ps不推断无在途、PID/creation/版本/exe/配置漂移、其他模型保留、GPU总量/UUID/年龄、预算耗尽、只读接口范围及有界系统查询。所有系统查询/HTTP/GPU采样均为夹具，不是真实设备验收。此前原40项候选测试原文和源码保持并复跑通过；两组不与其他代理测试总数相加。

运行本目录validate_candidate.py可产出TESTS.log、VALIDATION.json和manifest.json。父侧联合runner可直接discover本目录tests，测试默认加载本R候选及GPU代理冻结的纯stdlib GpuPolicy，不访问生产服务。若父侧改了合并源，须另验证其真实整合源码和指纹。
