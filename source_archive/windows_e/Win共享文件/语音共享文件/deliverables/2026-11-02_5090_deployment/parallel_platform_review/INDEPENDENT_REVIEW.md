# 平台恢复独立静态审阅

结论：维持 **EXECUTION_NOT_READY**。原 `load_business_checkpoint` 的完整 Python 读校验分支可以在受控解释器和精确模块命名空间内安全调用；本轮只审源码，没有调用它。loader 的返回码存在两层遗漏，修复 daemon 还有底层卸载失败被转成成功的路径，因此实际 client 的 RC0 也不够。真实事务适配器、持久 intent/job 账本和卸载后硬件状态判据仍须实现并审阅。

本目录仅本机报告/源码快照；板端只读取公共源码、配置、进程元数据，并用 `readelf`/`objdump` 静态读取 ELF。未执行 loader/client、相机入口、checkpoint validator、NativeContext、driver、MMIO 或运动；未打开身份/记忆库；未修改板端文件、锁、服务、固件或标记。没有把模拟测试、文档或持久链接提案计作本次恢复/冷启动通过。

审阅输入为当前根 AGENTS 入口、部署 HANDOFF、`parallel_platform/RECOVERY_REVIEW.md`、`PERSISTENT_BOOT_REVIEW.md`、`preflight_readonly_03.json`、`native_context_readonly_01.json`、`startup_sources_readonly_01.json` 及补充源码04。独立重新读取的来源见 `checkpoint_sources_01.json`、`loader_inventory_01.json`、`loader_sources_01.json`、`loader_elf_01.json` 和 `loader_elf_02.json`。每份记录均保存 host UTC、board monotonic、boot、采集脚本和可信 SSH transport SHA。

## 一、原 checkpoint 验证器的真实闭包

安装根为 `/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/aura`。本轮重新读取并核对：

| 来源 | SHA256 / 事实 |
| --- | --- |
| `board/vision/native_protection.py` | `b8637c2aa387915a49ef0fd7a1c7cb9d015fb71802c4eaa11539a64466db1faa`，12746字节 |
| `board/vision/native_binding.py` | `5f385c03cf84b1f9ba3afe4d4a6cfd3022ba639aba06b8d923f83783bfd48da6`，25123字节 |
| `board/vision/__init__.py` | `091e8b3b95a7f46655ba0c5275630eb3aee2079b57a95a0f5ef35d4e44c47284`，仅77字节docstring |
| `board/__init__.py` | 不存在；父层为namespace，不能假定 `sys.path.insert` 后不会被其它普通 `board` 包遮蔽 |

精确字节快照在 `review_sources/`；`STATIC_AUDIT.json` 保存 AST 导入、函数位置和调用清单。该核对没有 import 任何项目模块。

`native_protection.load_business_checkpoint` 位于快照138行，调用链为：

```text
load_business_checkpoint
  → _read_pinned → Path/resolve/read_bytes, SHA256, digest, json.loads
  → _boot → uuid.UUID（只解析传入UUID）
  → integer, FEATURE_COUNTERS检查, 当前time.monotonic_ns
  → 绝对导入 board.vision.native_binding 的 Seed、Recovery
  → make_native_seed → ctypes结构分配/sizeof/字段范围和枚举检查
  → /proc/<source_pid>/stat只读身份检查
  → 原checkpoint路径派生的 .native-consumed-<SHA> 是否存在
  → 返回原seed/auxiliary/document/marker路径/SHA
```

项目导入闭包只有上述两个模块及已核的父包。`native_protection` 顶层导入 `ctypes, hashlib, json, math, os, pathlib, time, uuid`；`native_binding` 顶层导入 `ctypes, dataclasses, hashlib, json, os, pathlib, time, threading`。除标准库 dataclass 装饰器及 ctypes 类型/结构定义外，没有顶层项目函数调用。`NativeContext.__init__` 内170行的 `C.CDLL(str(bridge))`、后续原生工厂、runner方法均只被定义，不在上述闭包内。Python 自身的 ctypes/_ctypes 解释器支持不等同于加载 AURA Native/VART/VSRV 设备库；本结论不宣称完全没有解释器原生扩展。

消费标记写入位于另一个函数 `consume_checkpoint`（177行起），`write_checkpoint` 也为独立函数；完整读取验证器没有调用二者。不应 import `native_startup` 或 `native_entry.py` 来“取得验证函数”：前者扩大 Native/YOLO/schedule 闭包，后者会运行实际相机启动链；历史维护脚本同理不能当只读入口。

完整 Python 验证器会校验 hash pin、schema/scope/purpose/boot、capture未超当前单调时钟、静止/无pending、七项SFace计数及顺序、三任务计数和独立recovery结构、前驱PID/birth已退出、未消费marker。它**没有**代替以下事务条件：

- source manifest/unit 与本次已核来源的精确相等，只在内部校验SHA格式；实际旧owner及本次stop intent之后的capture也须外部绑定。
- `previous_kernel_history` 全链、`inherited_optional` 完整存在/承接和比当前观测计数不回退；原函数不遍历归档。
- pending数组恰为三项等外部更严格形状条件；原函数对数组做逐值检查。
- C层恢复的更严格策略/时钟一致性。原源码161行附近明确说明C层会在创建原owner之后、gate执行之前重核；不能用只读Python校验宣称C/native已恢复。

## 二、精确且不消费的调用配方

`checkpoint_readonly_call_recipe.py` 是可审阅的只读配方，SHA记录在 `STATIC_AUDIT.json`。本轮只做AST解析，未运行。未来唯一操作者在原1333正常退出、真实最终文件形成后，可将其字节送入一个新的 `/usr/bin/python3 -B -I -S` 进程，传入真实新SHA及实际boot；它不需要上传、安装或修改任何板端源文件。

配方先核原始源码字节/父路径与哈希，再创建空 `board`/`board.vision` ModuleType namespace（空搜索路径），用**已经计算SHA的相同字节**编译原 `native_binding` 和 `native_protection`，以原绝对模块名预装入 `sys.modules`；然后仅执行：

```python
pin = {'path': '/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/state/native-protection-checkpoint.json',
       'sha256': actual_new_final_sha256}
loaded = protection.load_business_checkpoint(pin, boot_id=actual_boot_id)
```

不能给 `now_ns` 传伪造值，也不能对sealed副本路径调用后把该marker结果迁回原路径：标记派生自原checkpoint路径。本配方调用前后重新核原文件字节和原marker路径，拒绝任何marker路径对象（含dangling symlink），并断言没有导入其它项目模块。stdout只返回原验证结果；不消费marker，不创建NativeContext，不访问私库。

配方的范围仅是完整原Python函数调用。主事务仍须在其前后重核停机/owner fence、当前boot、来源、时钟、所有累计下界、前驱归档、封存字节和本次intent；不能把这份配方的存在填成已通过实际validator。

## 三、xmutil → 实际client → daemon 的返回语义

本轮 PATH 为 `/usr/bin:/bin`，`xmutil` 字典中裸名称 `dfx-mgr-client` 实际解析到 `/usr/bin/dfx-mgr-client`。安装文件及进程：

| 对象 | 精确身份 |
| --- | --- |
| `/usr/bin/xmutil` | SHA `037a78b2bafb9d72cd7f0b8343b2f9fe06de5f501adcebcc7e44227b0452209b` |
| `/usr/bin/dfx-mgr-client` | SHA `a37d8449c3362a509d459f9e57aa3711314602369354f7d98ca60c3e51607ad7`；18408字节；build-id `0b838e2710763a41aeb9e96ef91cf15a283a222c` |
| 实际daemon | `/usr/local/lib/kv260-dfx-state-repair-20261003/dfx-mgrd`，SHA `369c7fb0ddd023a7cf7af14896a7fda6036219a36f4980c73640889720c95dfd`，117856字节；本次读取PID1121/birth1516，cmdline SHA `eba390fe164718811ee931534079ab55a51a95b5e8092c7600dcf730346d7088` |
| vendor daemon（未在运行） | `/usr/bin/dfx-mgrd` SHA `bdbd8ee09b3f767a53bd5111240c9ade3bb19b1da83d73bd06785ae86260e9a2` |

保留修复源码位于 `/home/root/kv260-dfx-state-boardtest-20261004/staging/extracted/source/`，其 `SOURCE_MANIFEST.json` SHA `9d5c7bef81adbe2aa37973e8e5ed700ddb07e1017aea98d52fe757f1b25892f3`；本轮读取的七个相关C/H文件全部匹配该清单。其配套 `bin/dfx-mgrd` 与实际daemon精确同SHA。配套重编client为 `fe8b2c…`，与安装client不同；本审阅因此另外对**实际安装client**做静态反汇编确认控制流，没有把配套client当成当前安装版本。

返回链有三处风险：

1. `xmutil.py` 49/52行只 `subprocess.run`，不return其结果或 `sys.exit(child.returncode)`。外层RC0可以掩盖子进程失败。
2. CLI保留源码 `dfx_cli.c` 34–74行在回复后仅printf成功/错误，131行统一return0。实际安装ELF `main` 的 `0x14c0–0x1538`（load）及 `0x15b4–0x15ec`（remove）证实相同性质：reply负slot或remove非0只影响打印，不影响已为0的返回寄存器。**实际client RC0也不能证明daemon接受/完成成功。** write/read出错返回非0；read错误发生前请求仍可能已到daemon，不能推断“未执行”。
3. 修复daemon `dfx_daemon.c` 72–91行先同步调用 `load_accelerator`/`remove_accelerator`，再把slot/ret数值发回客户端；没有事务请求ID或幂等去重。`dfx_daemon_helper.c` 128–150行的VART更新失败只记日志，slot0仍可能返回。`dfx_accel_linux.c` 的 `sys_remove_accel` 351–364行在底层 `dfx_cfg_remove`/`destroy` 失败后仍返回SUCCESS；**当前daemon ELF** `0xd350→0xd378`、`0xd3e4→0xd410` 已确认错误日志之后返回0。因此daemon回复0、甚至它的listapps内存状态空，也不能单独证明overlay/实际平台卸净。

源码显示本flat加载经 `load_accelerator_locked → load_accel(...,0) → sys_load_accel → libdfx.dfx_cfg_load`；卸载经 `remove_accelerator_locked → remove_accel(...,0) → sys_remove_accel → libdfx.dfx_cfg_remove/destroy`。实际daemon动态依赖含 `libdfx.so.1.0`。本轮未执行该库或其任何入口；libdfx/内核电气行为仍由阶段后的真实读回约束。

## 四、真实loader适配器应保存和判断的结果

由于当前xmutil的load/remove分支只有转发动作，未来经审阅的板端监督器可直接启动精确SHA的绝对client argv，从而取得真实子进程状态；这不应通过修改安装xmutil或“修好wrapper”来试验。若仍保留xmutil路径，必须有等价的真实child结果记录，不能只记外层状态。

在任何发送之前持久保存唯一session、boot、context SHA、action/argv、真实daemon身份、来源/固件SHA和intent；原子独占创建并fsync文件及目录。真实child必须绑定PID、birth、完整argv/命令SHA、exe SHA和所关联intent。完整stdout/stderr保存**原字节**、长度和SHA，不能只保留最后一行。结束时保存真实wait结果/信号及board monotonic/host观察时间；进程或输出未知时不能填0。子监督器的寿命须与SSH失联隔离，不能通过超时context manager、systemd启动超时或主机timeout顺带杀掉它。

必须区分：

| 状态 | 可接受证据与后续 |
| --- | --- |
| PENDING | 真实child或相应daemon操作仍可能进行；保留同一intent/job，仅只读poll。超过时间预算仍是pending，不重发、不kill、不restart daemon |
| UNKNOWN | SSH中断、无结束回执、读失败、child已消失但结果未落盘、回复无法解析/关联；可保存为 `PENDING_OUTCOME_UNKNOWN`。重连只读核对，不把“没看到PID”当未执行 |
| CONFIRMED_FAILURE/HOLD | 收到完整负load slot或非0remove回复，或完成后读回错配；记录可能已有部分副作用，不自动重试或回退 |
| SUCCESS | 精确child已确认结束、结果/完整回复被保存并关联本intent、load期望slot0/remove数值0，且实际平台新鲜成套读回通过；缺一项不能升级 |

完整回复应严格解析，不按“包含0”或第一字符判断；load应为当前XRT_FLAT的期望slot0，remove应为完整整数0。RC0和日志中的“success”只作附加事实。没有可信回复但硬件看似正确时仍记录UNKNOWN，不能补造成功回执。

卸载成功特别需要补充真实平台判据：相机/GUI均无owner/job、完整maps+fd无DPU/MMIO用户、实际overlay/configfs/ZOCL状态达到允许下一次加载的已定义卸载态，并与当前firmware/FDT读回协调。只查listapps为空不够；也不能强要求卸载后旧 `/etc/vart.conf` 自动清空，原源码没有这个保证。加载成功再核实际wide firmware、operating、当前wide活动项、精确wide VART原字节、四固件/三driver配套、新FDT原字节与overlay状态。

## 五、分阶段草案的独立意见

本次冻结审阅SHA为 `22b7644e5ede791cc21b062467816337400939d369fbe5fc716ebeff049d6592`，字节副本 `review_sources/platform_transaction_draft_reviewed.py`。其真实backend硬拒、无run-all/GUI/ARM/COMMIT入口、先正常停原相机再真checkpoint、ID_STOP_ONLY先于恢复、pending不重发/不kill的方向正确。25项fake测试证明的仅是模拟控制流；本轮未重复运行它们，也未当成实板证据。

执行前必须落实/修复：

1. **loader语义条件不完整。** 冻结稿276/296行要求actual-client RC0和 `fresh_readback_verified`，没有显式daemon完整回复成功字段；卸载仅显式检查 `active_application is None`。必须把第三、四节的完整reply语义和实际overlay卸净判据变成可审核的真实字段/检查，不能在backend中默认true。
2. **持久状态与owner fence不存在。** 当前只有内存/模拟快照；启动job后的身份、正常完成阶段转换没有真实持久回执。需要同boot唯一owner、写前intent、已保存job和崩溃重入的只读reconcile。正常stop只发一次 `systemctl stop --no-block`；不能外层timeout杀原相机。未知launch无handle同样不得重发。所有可能在发送后发生的异常须归一为未知结果，并保留可查job，即使guard进入HOLD仍可只读观察已有操作。
3. **checkpoint证据只能从1333原shutdown产生。** 旧盘上5b26714b/boot3c94/PID1352不是本次seed。须验证新boot903c/PID1333/birth2359、manifest5e08/unit7cf7、本次stop intent之后capture、正常服务退出和无旧owner；用原函数校验**原路径pin**，O_EXCL封存原始字节，fsync/回读SHA，不重序列化、不修补、不改指针、不写marker。封存未知结果只能查已写物，不覆盖。
4. **外部计数与归档验证仍是假布尔。** 冻结稿只直接比较primary_calls/primary_period_overruns/SFace completed三个下界，`previous_kernel_archive_chain_verified` 仅由backend返回。未来backend要持久保存本轮更晚观测下界，保留最终seed全部计数、两个独立recovery历史、七项SFace和inherited_optional；至少本轮已观测下界78923/1/427必须保留。不能把下界写成最终值。逐层以原始archive SHA核 `previous_kernel_history`，验证当前903c归档连接5b26714b的旧3c94及后续前驱；拒绝循环、缺失、路径重定向、silent truncation及旧owner仍活着。现有 `collect_final_checkpoint_readonly.py` 只核第一层archive，不能直接把它的成功等同全链通过。
5. **读取清单不等于持续独占。** 真实适配器须在卸载、加载、ID/STOP、恢复前重取完整maps+fd和服务/命令/boot/startup来源，并维持唯一主操作者fence。任何仍活着却不可读的进程均阻断。ID/STOP pending阶段只能豁免本次已保存且身份验证的唯一transport；原 `/run/aura-vsrv.lock` 的互斥不能被删除/绕过。新相机恢复也须继续核原shutdown保护，不能因命令SHA相同就跳过有效服务属性。
6. **恢复证明仍须真实落地。** 原入口只start一次；pending保持。新owner来自systemd+proc+health并为唯一DPU；源/模型选择未变、真实源推进。原audit `exact_seed_before_operator_request` 与sealed seed逐值相同、原marker仅由这次真正恢复消费。旧operator请求boot463c本轮应直接return；不能改boot或重跑恢复解锁。若恢复后再回退，必须正常停止这个新owner并取得它自己的新final，不能复用已消费的阶段2文件。

## 六、通电、ID/STOP与持久启动边界

本boot已知事实仍是benchmark、相机1333、GUI failed/MainPID0、聆听false；用户仅确认通电可观察。默认RTL reset/PWM0说明配置完成且reset有效后的输出契约，不能证明PL全量重配置期间引脚无暂态、外部上拉无影响或舵机不会抖动。新平台第一项设备写入应为原ID/STOP入口的STOP；ID/ABI/build、flags0/lease0、transport关闭确认只证明协议输出关闭，1500寄存器不是物理回中/位置参考。当前没有新boot ARM/短测授权或位置/方向验收。

持久链接与ready unit提案仍未安装/冷启动验证；只改默认选择也不保证相机晚于实际wide/overlay/VART就绪。需保留既有修复daemon/ZOCL依赖、原相机无限正常停止保护、监听false与动态boot/owner来源绑定。即使将来配置写入成功，冷启动实证完成前也只能记 `PERSISTENCE_CONFIGURED_COLD_BOOT_PENDING`，不能宣称持久集成通过。

本轮没有生成本次stop intent、真正final checkpoint、wide FDT、ID/STOP回执或恢复新PID。以上缺口完成之前，发布状态保持 **EXECUTION_NOT_READY**。
