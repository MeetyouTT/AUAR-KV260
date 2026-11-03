# Root续接工作状态（私有，不作为最终交付结论）

## 最新：本轮工作已封存

UTC2026-10-24最终续查仍camera29563/GUI29588、持久c76110abefc304bb版本，YOLO9.96Hz、YuNet50768调用/fault2 recovery2/gap0，SFace继承2次/新增0。两个审计相隔6739秒无新增optional/primary/gap。final-audit.json、final-cleanup.json、CURRENT_STATE.json均已齐；probe/instance0、所有自身observer/timer inactive、8线程nice0、CU计数在YOLO进展15帧时不变，统计确认关闭。没有活动中的UART或诊断任务。

第二条真实故障event20476已在offload-baseline-analysis.json分段：native16.239ms含runqueue14.006ms，GIL重获8.698ms含sleep8.415ms，wait_native0.009ms；32.96433ms硬超限未越guard并自动恢复。Nice=-5短试180秒694cycles/GUI8fps，长基线P99与nice相近，未保留，nice已恢复默认。八点板解析10分钟版成本3.136%失败留档，offload版1.738%通过；数据与gate严格分开。

最终237组合0失败/2私有ELF跳过、68KV260隔离、各parser/restore用例均有日志。完整源码/证据/回退已复制 /home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_vision_recovery_and_admission/，163条SHA/164文件、97Python AST/44JSON全部核验；shared-delivery-proof.json保存在私有工作目录。共享入口、Ubuntu回执、AMD索引/active优先级/daily及两组ACTIVE_RELEASE/CHECKPOINT均更新，并留旧状态备份。

下一次继续应先读上述交付README/VALIDATION/CURRENT_STATE及最新实板状态；不重跑已经结束的诊断，不用本文件下方历史session。尚未闭环：长尾完全消除、SFace真人恢复/精度、实际冷启动、持续真实交互及同输入收益。Windows接收未代确认。仍遵守单终端；以下内容仅为本轮过程历史。

UTC2026-10-23约23:15。用户最新：“自己查找、自己解决，离开2小时，只允许一个终端”。只用root，所有子agent已结束/不存在，不要再启动。任务从约22:06恢复，用户给的窗口约到00:06 UTC。无goal工具。全程root串行UART，禁止与未完成的UART exec session交叉。

## 当前板卡

boot008f3e1b-c627-4b98-b120-d2a460cdbcbe（外部新boot，非本轮触发；旧boot7924…的故障已档案保留）。当前持久版本：camera29563、GUI29588、X1077。原unit29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512保持；新增/etc/systemd/system/aura-camera-ui.service.d/zzzz-aura-vision-recovery-c76110abefc304bb.conf，SHA ebf6d52ce1848f2fc1af73e284688a70372bbd9ec585f9cbbc09af7035631b3d。

release=/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-vision-recovery-c76110abefc304bb。控制helper /home/root/aura-post-power-20261022/helpers/c76110abefc304bb/source.py，SHA c76110abefc304bb17be0e911cb68e743213c4df097bf68d3c84e327c22d504f。report /home/root/aura-vision-persistent-20261023/promotion/c76110abefc304bb/report.json；本机promotion-result.json accepted/pass，60.302826秒YOLO9.966365/face3.896998Hz，业务窗口0新增fault/gap/主周期/USB，startup primary+1单独保留。GUI context同root/gui-context-29563，GUI175Python未改、保持mic关闭/main/idle。

最终4源pin：schedule87b357326364d7cff874480a207482939623ef97025aa51bc947bd3cd1517d77，SFace c31c75831bb7e2563b17767aa31c80c1721da44dca137e1dd03618938f79f2bd，ui fc67a4fc7a3687011be6bb83d36e11adcc6deedaaea809698bd5eb75a83731f4，handoff7e8eaf3fa6b2e82bad73e36b82f25a6cc414722d07f5d44dd518f8c1929e251d。实际冷启动未做，不能重启/USBreset/转轴。SFace一直2次旧继承native、新窗口0请求，无真人恢复/精度验证。

## 已完成代码

SFace独立受限恢复：native_completed在slot内/正常wait后，过期只算完成不算成功；10s冷却，2轮/600s，3次合格后ready，前两Deferred不上身份/登记；guard/未知完成锁定，2策略独立。admission_floor=30，只严格拒绝<35ms窗口，不改30ms hardcap/5ms guard。启动handoff同boot继承，duplicate marker锁两optional；显式allow_new_boot首次新kernel boot开启新计数窗口/保留旧快照来源，重复新boot marker仍锁定。持久drop-in已上线，回退只移自己的永久文件、写/run临时保护回退，避免旧BOOT入口下次开机锁死。未知native owner拒绝替换。

工作目录阶段：aura-sface-recovery-20261023（初始198组合/171+26板隔离）、aura-admission-floor-20261023（61板隔离，60秒9.9665/3.8805）、本目录（最终68板隔离含7模拟新boot，6控制器行为）。combined-regressions.log=229通过/1skip，skip是私有精确ELF未挂Docker，host已过。当前业务源冻结，勿为了诊断更改或重启清故障。GUI同boot人工版本切换3次，NRestarts0仅自动重启属性。

## 刚捕获的真实故障（最重要）

本目录phase-result.json/phase-summary.json不是600秒通过：计划600s但25.2715s遇新YuNet fault就停，81完整cycle。event12638，总33.677557ms，hardcap1/guard0/status0/native完成1，guard仍余31ms，primary/gap未新增，owner未fenced。Python execute22.461ms/CPU1.1706，wait9.695ms/CPU.2155。精确uprobes匹配：native21.611ms，between .428ms，RestoreThread仅.094ms；Python返回到lease释放11.01029ms。captured-fault-analysis.json有完整分段。不能把本例归因为GIL重获，也不能叫纯DPU算33ms。当前源pipeline_metrics.native_mark先取now再锁，因此wait_start→wait wrapper可能含诊断锁/调度。

vision_current_recovery.py已实板读回：同camera29563自动恢复RUNNING，faults1/attempts1/recoveries1/probe_successes3、YuNet DPU、gap0/primary仍3；未重启。保存到model-inventory/vision_current_recovery.response.json（还需复制进本目录）。SFace ready且故障0，但新输入仍0。

旧第一轮3分钟702cycles、main600秒2354cycles、vision180秒682cycles在aura-sface-recovery目录，全部0fault/gap，不混用为当前最终版无故障。当前故障必须保留，README和VALIDATION还没更新这条。

## 正在做的下一步

新8点probe+内核sched_switch/wakeup诊断，不改生产：trace_wait_sched.py。4原execute/GIL点＋wait callback入口0xfdf0、wait native前0xffd8、native返回0xfff8、cleanup后0x10154，均精确opcode验证。h.NAMES8重绑，cleanup先disable自身instance的sched_switch/wakeup再删8uprobes/instance；page恢复有guard。DURATION600/遇新增fault早停。目标TID从当前fault29571取得，uprobes记录当前所有既有线程，sched仅target29571。targetR/R+换出→换入是runnable等待；S→wakeup睡眠与wakeup→in排队分开，无wakeup记unknown。只能用完整phase关联，不把睡眠直接叫GIL。

probe8_isolated.py 已板验证：500cycles/4000events，额外均CPU38.363us/8probe、P99完整64.961us，成本<100us、cleanup/globalstate/guard过。result在transfer-vision_probe8_isolated/result.json，helper0bf8df6…，未复制本机结果文件。5项wait-sched-parser-tests.log过（精确ELF+8段+kernel parser）。

**当前exec session9510** 是stage_helper_bundle trace_wait_sched，label vision_wait_sched，日志wait-sched-stage.private.log。先poll session9510完成，再读/home/ghmd/aura-post-power-20261022/transfer-vision_wait_sched/result.json取得新TOKEN/report位置，创建小poll probe，别与UART交叉。未得到实际8点结果前勿下结论。然后host按phase与off_cpu_intervals关联，决定是否应调CPU优先级或修诊断锁；不要盲包C++、换模型/阈值。

## 资源/最终审计待办

前一准入版resource-result（admission目录）实际15.06s整板CPU48.116%、GUI23.107/相机19.787/X3.602%整板、DPU CU任务busy约5%、209命令，非A/B/SFace负载。统计已关。最终本目录resource第一次71803…失败在启动前“非零累计”门槛，未启统计；记录failures/resource_nonzero_counter。计数停止仍保留总数，不等于活跃。resource_snapshot.py已改为1.5s中>=5个真实YOLO完成而CU计数不变才判断不活跃，4个resource-gate tests过。还未重跑；应等当前probe结束后独立重跑（当前源修改后helperSHA会新），最后off最好也用>1.4s实际进度证明。

vision_persistent_audit.py在model-inventory目录，直接run_probe因wire长3885>3800而在本机断言失败，没有接板。需用stage_helper_bundle传这5KB只读helper来最终核对源码214/GUI175、配置/DB SHA、回退--check、unit/probe/timer状态；结果复制本目录final-audit.json。current idcfg398ece…，DB ee22b…，旧Windows库未触，建议补其SHA验证e0d211…亦可。

## 交付/日志尚未完成

本目录README.md、OPERATIONS.md、build_delivery.py已写，VALIDATION.md/CURRENT_STATE.json/final-audit/resource/最新8点结果未齐。build_delivery预设files+history/proofs，运行前补齐；不可包含.so/权重/UART/真实脸/向量/数据库/私有偏好。待打包后copy到 /home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_vision_recovery_and_admission/，更新共享入口/Ubuntu回执（不能Windows回执）、AMD_Smart/PROJECT_BOOK_INDEX、active计划、daily日志以及两个live coordination目录的ACTIVE_RELEASE/CHECKPOINT（旧还是588727/旧boot，需备份更新）。共享临时进度文件SFace受限恢复_执行状态_20261023.md还指5842/旧阶段，需改最新。

RUNNER_FINDINGS.md、runner-symbols.json、runner-recovery-proof.json在SF目录：本板libvart-dpu-runner.sha bd832b…，DpuRunnerDdr::wait确为BTI/movw0,0/ret，execute含start_dpu2。准确源码提交仍未匹配，具体对象dispatch未证明。objdump CRC警告污染JSON导致首次读工具parse失败，framedbody SHA已复算等于status/end，363B警告后恢复JSON；无新推理。不要把wait短当硬件没耗时。

严守单终端、root串行UART/最多35s命令/3800字wire，长helper stage，exec session未完不发新UART。原始记录和ELF仅本机，CPU与DPU busy/静态FPGA资源率分开，不以短窗或仿真说根治/长稳/真人恢复。
