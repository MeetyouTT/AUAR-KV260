# 本 boot 的 wide 恢复审阅入口

**准备状态：REVIEW_ONLY，未执行板端写入。** 这是一份给唯一设备操作者的人工分阶段步骤，附正常停止前/后的纯只读检查入口。尚未提供可直接连跑的写入事务执行器，不能把旧 `run_step.py` 改几个常量后重放。本目录全部实证均为读取配置、源文件、进程和公共健康元数据。

## 本轮真实上下文

| 项目 | 新鲜事实 |
| --- | --- |
| boot | `903cfade-b93c-48fa-804e-379be1967313` |
| 当前业务 startup SHA | `07c5aa3b1c8da060e5a7d8520021bce7f167a8cf303b48a0a24f8e2a8b63035d` |
| 当前平台 | `kv260-benchmark-b4096.bit.bin`，FPGA `operating`，VART 精确指向 benchmark |
| 当前 FDT SHA | `d68bc147f22f5ab23bc60f0c2762af4bcd7b64340953e9c948e28ffa6b80f7ca`；仅是当前 benchmark 基线，不能用作将来 wide 的期望值 |
| 相机 owner | PID `1333`，birth `2359`，cmdline SHA `acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd` |
| 服务保护 | `Restart=no`、`KillMode=process`、`SendSIGKILL=no`、`TimeoutStopUSec=infinity` |
| GUI/监听 | GUI `failed/MainPID=0`、无 Job；保存偏好 `{version:1, enabled:false}` |
| DPU/运动 owner | 最新完整 `/proc/maps` + fd 观察只有相机 1333；没有 `libvsrv.so` 或 `/dev/mem` owner；没有不可读的仍存活进程 |
| 检查闭包 | 380 业务组件、14 读回来源、222 原 Native Python、7 operator 文件、wide 4 固件及 3 driver 实读匹配 |
| 最近短窗 | 1.087s 中 capture `237157→237190`、detected `78911→78921`、YuNet face `78905→78915`；无采集/检测/身份错误，未发运动 |
| 当前 Native 计数下界 | `primary_calls >= 78923`，`primary_period_overruns >= 1`，SFace `completed >= 427`。这些是当前累积计数的下界，后续不得清零；短窗 SFace 没增长不代表持续三模型负载或识别准确率验收 |

盘上的 `state/native-protection-checkpoint.json` 仍为旧 boot `3c94e7a0…`、PID1352/birth2396，SHA `5b26714b0be9d52bf99fe14c07a0f810105379171712328b63454beb314bc6bb`。当前 1333 通过原 `validated_new_kernel_boot` 入口新建本 boot 计数域并归档前驱，**旧文件不能作为本次同 boot 重启 seed**。正常停止 1333 后，应由其原 shutdown 路径生成新的真实最终文件。

当前实际 source manifest SHA 为 `5e08f7cf587d74334ef24104ea01f79701629b48f2004fb772ce3f8ea82afd0d`；原 operator ABI 兼容迁移后最终 checkpoint 的 source unit 为 `7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32`。原 operator 请求 boot `463c9307…` 与本 boot 不同，原 recovery worker 会直接返回；不得修改该字段以重复解锁。

## 通电条件下的默认输出依据

已读同一 `6a4b645a…` candidate manifest 对应的原 wide RTL，来源是 `E:\Win共享文件\协作任务\2026-10-28_整机联动与舵机范围\offline_wide\source\rtl\visual_servo.sv`，SHA `0fc6e305a51f22a31a50dfc88a9c2d2c80a303c79f9ef9d2b146bdb3ad12e180`。

- build `0x10282601` / ABI2。复位将 `bound/referenced/armed/active=0`、`lease_left=0`、`servo_pwm=0`。
- width/target/reference 的寄存器复位值1500不产生PWM，不是实物回中。有效 COMMIT 且已经具备 BIND/REFERENCE/ARM、会话/序号/范围/租约条件，才启动输出。
- STOP、独立 lease 到期或 QUIESCE 正常完成都清授权并令 PWM 为0。保留每20ms最多4µs的变化上限；500..2500只表示脉宽能力，不是本机构的已验收范围。
- Python driver 的构造只读 ID/ABI/build；`stop()` 的唯一命令是向0x24写STOP并检查 flags低四位和lease为0。原 Native transport close 会再发一次STOP并检查关闭回执。

这是配置完成、时钟与复位生效之后的RTL契约。全量PL重配置期间的引脚暂态、外部上拉和舵机失去信号后的行为，没有本 boot 电气波形实测，不能从源码宣布“切换必定完全不抖动”。用户已报告通电且能观察；切换时应保持现场观察、人员/线束/机构有余量，并准备可立即切断转轴电源。意外转动、持续抖动或接近限位时立即结束恢复，能可信发STOP则STOP，连接/标识不可信时不能盲写寄存器，现场断转轴电源。

## 分阶段人工入口和停止点

以下板端命令仅供主操作者审阅后串行执行。本子代理未执行任何一条。每阶段用一个新会话根记录 intent、真实结果、命令输出和 host UTC/board monotonic；不能复用旧 `aura-axis-priority-…3c94` 根或旧阶段文件。

### 0. 重取正常停止前的事实，冻结回退材料

运行 `collect_preflight_readonly.py`，使用新的本机输出名。若 startup、boot、相机身份或GUI状态改变，停在这里重新审阅，不直接改常量。现场通电/观察事实记录为事实，不填“方向通过”或“允许ARM”。

主操作者在本 boot 新根中独占操作并原字节封存：startup/组件映射、相机owner和健康计数、当前 checkpoint 旧 SHA、benchmark四文件SHA、VART原字节、当前FDT原字节及SHA、相机服务有效属性。记录 `stop_intent_mono_ns`、真实PID/birth、source/driver/bench指纹。为新会话使用唯一锁并检查已有设备owner；不删除已有锁或消费marker。

停止点：任一来源/服务保护条件不符，GUI出现owner、监听偏好不是false、有DPU或原始内存额外owner、相机fence或shutdown不完整，都不停止相机、不切平台。

### 1. 只请求原相机正常停止

确认本次 intent 已落盘后，只发一次：

```text
systemctl stop --no-block aura-camera-ui.service
```

之后只轮询 `systemctl show`、原 PID/birth存活情况和owner清单。原 SIGTERM 处理器让采集停止、YOLO worker join、身份/辅助runner正常关闭，然后执行 `native_startup.shutdown()`。没有可替代的“从health构造checkpoint”路径。

通过要求：`MainPID=0`、无Job、`ActiveState=inactive`、`Result=success`、`ExecMainStatus=0`；原PID/birth确实消失。20秒未完成应记录 `CAMERA_STOP_PENDING` 并继续只读确认，**不kill、不用外层timeout杀owner、不重启服务、不清锁**。超时不是可以换runner的证明。

### 2. 验证并封存真实最终 checkpoint

正常停止后才运行本目录 `collect_final_checkpoint_readonly.py`。这份脚本没有在准备期执行过，它会拒绝仍活着的1333、旧5b26714b文件、不匹配的boot/sourcePID/birth、不完整静止状态、已消费文件，以及低于当前已观察累计下界的计数。其输出给出原始文件精确字节的base64和SHA；没有重新序列化或修补seed。

主操作者另按已验证源码的原 `load_business_checkpoint(pin, boot_id=当前boot)` 完成原检查器的完整校验。调用此函数前需核对当前 installed `native_protection` / `native_binding` 来源，不能导入本来带顶层设备动作的旧维护脚本。此函数不能调用 `consume_checkpoint`；消费只能由真正的相机恢复路径完成。

最终必须逐项确认：

- schema `aura-native-protection-checkpoint-2`，scope `final_quiescent_before_native_owner_close`，purpose `final_quiescent_business_checkpoint`，checkpoint_kind1、ABI2。
- boot903c、sourcePID1333/birth2359、source manifest5e08及source unit7cf7真实匹配；capture monotonic晚于本次stop intent、不在未来；SHA与停止前不同。
- active/primary_waiting/fenced均0、三个pending_result_tokens全0；完整七项SFace计数、YuNet/SFace两份独立recovery历史及inherited_optional均在。
- 保留 `primary_period_overruns >= 1`、`primary_calls >= 78923`、SFace completed>=427和所有更晚累计值，不能固定写为这些下界。原Native校验的更多策略/时钟条件仍须通过。
- `previous_kernel_history`连接当前内核归档：`kernel-history/archive/903cfade-…-5b26714b….json`，归档SHA实读匹配，保留旧boot3c94及其完整前驱链。
- 没有此新SHA的 `.native-consumed-<SHA>` marker。

主操作者以O_EXCL/不覆盖方式把**原始最终文件字节**封存在新会话根，回读SHA相同；checkpoint指针原文件不改，marker不创建。记录 `CAMERA_STOPPED_CHECKPOINT_SEALED`、真实新SHA、source owner、完整计数和归档SHA。

停止点：任何校验失败、前驱仍活着、最终文件未刷新或不完整，保持原保护状态，不进入加载阶段。`collect_final_checkpoint_readonly.py`是独立静态前检，尚未实板运行；它不宣称替代原完整校验和本次intent时间比对。

### 3. 再次确认没有DPU或运动owner

在卸载前与加载前都重读 `/proc/*/maps` 和 fd：不得有 `libvart`、原Native operator映射、render/DPU设备handle；不得有 `libvsrv.so` 或 `/dev/mem` owner；没有不可读的仍存活进程；相机/GUI MainPID均0且无Job。再次核对真实最终文件SHA和sealed副本相同、未消费。

停止点：出现新owner或无法证明owner清单完整，不卸载、不加载。不能因为服务显示inactive就省略这一步。

### 4. 成套切换wide，接受真实loader行为

在各自intent阶段各发一次：

```text
/usr/bin/xmutil unloadapp
/usr/bin/xmutil loadapp aura-visual-servo-b4096-wide-v1
```

两条命令之间须确认第一条已完成、应用状态卸载、无DPU用户；不可并行。`/usr/bin/xmutil`当前包装没有把`dfx-mgr-client`的返回码传回外层，因此returncode0只是一个观察，必须同时保存stdout/stderr、loader子进程实际完成情况以及fresh `listapps` /固件/VART/FDT状态。通信超时或命令仍在运行时保留INTENT/PENDING，重连只读核实，不能自动再发一次加载。

不要沿用旧步骤“xmutil之后VART还应等于benchmark”的断言：上次真实loader已自动更新VART，随后仅finalize核验；此次按实读判断。

通过要求：

- 固件精确为 `aura-visual-servo-b4096-wide-v1.bit.bin`，FPGA operating，listapps中wide为当前活动应用。
- `/etc/vart.conf`原字节精确为 `firmware: /lib/firmware/xilinx/aura-visual-servo-b4096-wide-v1/aura-visual-servo-b4096-wide-v1.xclbin\n`。
- `candidate-manifest.json` SHA仍为6a4b645a…，wide bit/DTBO/XCLBIN/shell四文件及driver三文件重新核对。原bench SHA c9e91f…也必须匹配。
- 此刻计算并封存**新生成的wide FDT**原字节和SHA，生成新context绑定当前boot/firmware/FDT；不把历史e359/aed6/cb435等FDT值塞进本次context。
- 读取当前DT节点，确认wide firmware、ZOCL及所需overlay状态；已安装DTBO源码也已只读解码留档。DTBO里没有独立VSRV寄存器节点，不能靠FDT声称已读到VSRV ABI；下一阶段的受控ID读回完成这项确认。

停止点：任何loader结果不明确、VART/实际平台/配套文件不一致，不启动相机、不打开MMIO、不靠写VART或换旧FDT让断言通过。先保留现场和intent，由主操作者决定修复或成套回退。

### 5. 新平台的第一项设备操作是 ID/STOP-only

此步前相机仍停止，用户现场观察，STOP和转轴断电准备已就位。主操作者在新根创建fresh context，内容只有实际 `boot_id`、刚实读的 `fdt_sha256`、`firmware_name`，不得填旧宽度或physical_reference。

核对真实板端 `release/bench_identity_stop.py` SHA `c9e91f74336c1e73d7c60408739abc8537b80066eb666a1a79e32b81d7d267aa`、三份driver、四份runtime后，使用这个原入口（`<本次新根>`由主操作者实际创建并记录）：

```text
/usr/bin/python3 -B /home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c/bench_identity_stop.py --execute --confirmation ID_STOP_ONLY --manifest /home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c/candidate-manifest.json --manifest-sha256 6a4b645a5bbfd35c9107976edf27886cf8e0c91e40f48be6f052a95e1172c1cf --context <本次新根>/wide-context.json --output <本次新根>/id-stop.json
```

该原程序先读ID/ABI/build，第一项寄存器写入为STOP；没有BIND、REFERENCE、ARM或COMMIT。Native transport取得原互斥锁，关闭时再确认STOP。不要执行旧`id_stop_new_boot.py`，它额外假定相机已经恢复及旧会话phase。

通过要求：ID `0x56535256`、ABI2、build0x10282601，after_stop.flags=0、lease_left_ms=0，active/armed/referenced/bound全false，context关闭成功；证据显式记录BIND/REF/ARM/COMMIT均false。1500寄存器值只作读回，`physical_position_verified=false`。

停止点：ID不符、STOP拒绝、读回不稳定、锁被占用、出现意外动作或通信中断，都不恢复相机或继续运动。标识不可信时不盲写；现场按需要断转轴电源。STOP协议通过不替代位置/方向/电气波形确认。

### 6. 只用本次真实最终文件恢复原相机一次

确认阶段2 sealed SHA仍等于原checkpoint指针、未被消费，wide/context保持，ID/STOP通过、全部临时MMIO owner已释放且无DPU用户。记录 `CAMERA_START_PENDING` 后只发一次：

```text
systemctl start --no-block aura-camera-ui.service
```

保留原服务、原argv和所有保护属性。原native_entry自动选择当前真实checkpoint并由原启动路径消费。不能把旧5b26714b、health计数、isolated maintenance seed或手写sourcePID当seed；不调用旧boot_ops的activate/benchmark/rollback流程。

通过要求：从真实systemd和`/health`读出新owner的PID/birth/cmdline SHA，不预填新PID。新owner身份元组与旧1333/birth2359不同，命令SHA仍acf3…，只存在一个DPU owner；无camera/detector/identity错误、无fence、未quiesce，源帧/检测/YuNet推进。SFace后端ready及自然新完成分别记录，不把无当前人脸的短窗强当识别准确率。

必须核对 `/pan-face-edge-v5/native-operator-v1/recovery-audit-<实际新PID>.json` 的checkpoint_sha256等于阶段2真实SHA、`exact_seed_before_operator_request`逐值等于sealed文档seed，run config中的seed SHA相同；本次累计保护历史和previous_kernel_history保持。新SHA的consumed marker应由这一次真实恢复生成。

停止点：启动pending、失败或不确定owner时记录真实状态并保留原保护，不强杀、不重新start、不清marker、不为“试一下”切回benchmark。只有确认原owner正常退出并生成它自己的新最终checkpoint，才有下一次替换资格。

### 7. 业务读回承接与验收分别处理

新相机owner确认后，沿主操作者已有事务重新验证来源闭包/原模型与私库选择、原TTL/阈值及真实源推进，再更新face readback owner及其组件哈希。不能只替换PID或boot。此阶段不打开真实私库/模板，不改变原算法、模型、阈值或累计计数。

GUI是否启动、音频是否READY、Windows模型接入和用户聆听属于主操作者单独安排。恢复wide和相机不自动恢复监听，不自动跟随。新boot实体位置、方向、范围和初始化短测仍须当前事实与另一次明确授权；旧1505µs和方向+1均不能沿用作验收。

## 回退与未完成项

- 相机正常停止但平台未改变，若决定恢复benchmark相机，可用阶段2同一个真实、未消费checkpoint经原相机入口恢复一次；同样需要真实owner和读回承接。
- wide已加载、相机尚未恢复时，只有确认无owner，才可通过同一成套loader回到已封存的benchmark配套；核验实际固件/VART/FDT，不能只改VART。
- 相机已在wide恢复后要回退，必须再次正常停止**新owner**、取得它自己的新最终checkpoint并确认无DPU用户，再切benchmark。阶段2旧文件已消费，不可重用。
- 用户仍需提供/确认当前boot的观察到的位置参考、实际安装/相机随轴情况、运动方向和清障条件，才可另行准备有明确幅度/时长的短测。已上电且可观察只是其中两项。
- 本目录没有执行写入事务，因而实际本次最终checkpoint、新wide FDT、ID/STOP回执和恢复新PID均尚不存在，不能预填。主操作者必须把上述真实阶段材料写入自己的新会话根并审阅失败保持分支。
- 默认启动链接和依赖的持久修订在下一阶段；参见 `PERSISTENT_BOOT_REVIEW.md`。没有冷启动证据不能写为持久集成已通过。
