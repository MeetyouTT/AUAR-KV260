# Ubuntu / KV260 执行回执

<!-- hdmi-training-native-observation-20261024 -->
**后续用户决定与新故障定位：** 用户已确认软件后未拔HDMI仍花屏，随后要求暂停显示问题。当前转入[其他问题统筹](Ubuntu_当前统筹_20261024.md)：转轴FAULT实际error=Boot mismatch，尚未动作，联合候选路由已过但最终报告未齐；长尾/收益/实际三模型负载/回退未完成。以下PENDING描述保留为当时记录。
**最新单终端：真实花屏场景软件试验已完成，视觉结果待回报。** [源码、数值及当前状态](../../语音共享文件/deliverables/2026-10-24_hdmi_link_training/README.md)。用户确认断电再上电及“仍然花屏”，新c5f247b9…/1309/1310/X1077自动恢复/NRestarts0，旧e6eb4b0d…checkpoint精确归档及SHA通过；启动期GUI接口未就绪的原失败保留。冻结474b控制器本boot单次train1/encoder开关0、调用/VBLANK返回、模块/自身trace清理和维护单元success，相机1363→1387同PID，新primary/optional超限0；后查2238帧/9.83Hz、worker/SFace ready、身份配置及库SHA保持、筛选内核错误0。软件后画面尚PENDING，未装启动项或重复触发。完整两小时7200.054秒/YOLO9.9527/YuNet27116完成/0新故障gap/SFace新0，含页面和显示干预，非满载/收益结论；两观察器及诊断已收尾。旧4fault4rec和141秒空档保留，长尾及pan FAULT未完成，Windows回执未改。
<!-- /hdmi-training-native-observation-20261024 -->

<!-- native-acceptance-coldboot-20261024 -->
**最新单终端验收更新：** [身份/真实断电与当前未闭环项](../../语音共享文件/deliverables/2026-10-24_native_acceptance/README.md)。本人正脸106/106、未登记者107UNKNOWN/0KNOWN、两人21点0单人绑定均通过，阈值0.5/0.1与登记库SHA不变。首轮混合转头86.79%未追认通过。正常stop/精确checkpoint/DPU锁释放后OS poweroff，用户重新上电；boot b7871498…、camera1294/GUI1295/X1076自动恢复，60秒YOLO9.9548/SFace新10/0新超限gap。**显示冷启仍闪，用户本次手工HDMI重插恢复；整机未通过。** 关机前原生YuNet34373准入/4fault4rec、SF1850完成0fault，归档真实4尾延迟，不再说根治/累计0。屏幕微雪板卡USB兼触摸，无独立电源Hub，用户正在换供电对照；板端操作暂停。后续先核对新boot，保持旧档/模型/库/Windows回执边界。
<!-- /native-acceptance-coldboot-20261024 -->

<!-- native-critical-live-20261024 -->
**最新单终端真实启用：** [原生r4运行版与实证](../../语音共享文件/deliverables/2026-10-24_native_critical_live/README.md)。boot a69299ef…、camera2174/GUI2206/X1075，三模型原生gate，单owner。180.841秒YOLO9.9369Hz、SFace新46次，0新primary/optional超限/gap；最新SFace64/optional0fault，primary累计2含失败/启动。6对/16执行API真实INT8等价通过，YOLO为空结果范围有限。两软件reboot、漏ByteTrack附件/metrics未注册导致的实际失败、准入/TTL拒绝和控制器超时均保留；正常checkpoint同boot承接r3→r4，无第三次重启或预算清零，旧5/3fault及4/2rec归档。67业务/237旧套件235pass2skip/16控制/22比较检查过。CPU63–64%/DPU busy5%为非配对点测，第二资源窗SF64→64无新负载，统计已关。身份cfg/INT8库/原unit与GUI源保持；保护式旧码rollback软件过、实切回未做，长稳/身份精度/实体冷启/严格收益待验。救援timer关闭、controller退出，Windows回执未代写。
<!-- /native-critical-live-20261024 -->

<!-- native-critical-single-r2-20261024 -->
**最新单终端执行：** [原生r2代码与实证](../../语音共享文件/deliverables/2026-10-24_native_critical_candidate/README.md)。用户限制单终端后中断副任务，root串行补完新kernel/legacy首迁移与归档链；222源/5 C++，62项业务迁移、旧237中235pass2skip、12实际CDLL-fake、原生20/8/5＋SAN通过。DSO c675ba69…板上只链接0.795秒，再仅加载读ABI常量，factory0/推理0；222源/拟用配置96948ff1…已上板独立目录，当前boot preflight按预期拒legacy，未安装覆盖/切服务/reboot。现YuNet5fault4rec LATCHED CPU、SFace3fault2rec LATCHED readyfalse/完成755，只有YOLO DPU9.95Hz，同camera29563/GUI29588/X1077、gap0、primary3，原unit/四源/身份配置/库保持、探针/统计清理状态保持。新boot旧fault按下界/unknown tail归档不重放时钟、当前boot唯一marker，同boot不解锁；实际冷启/真模型等价/性能/长稳未验。Windows接收回执未代填，下方早期状态保留。
<!-- /native-critical-single-r2-20261024 -->

<!-- native-critical-progress-20261024 -->
**UTC2026-10-24原生执行路径修复进行中：** [当前状态与证据](../../语音共享文件/deliverables/2026-10-24_native_critical_candidate/README.md)。用户改为多终端，root独占UART，三路本机实现/测试。原生bridge/固定缓冲/YOLO移交/unknown保留/不跨推理的生命周期锁已实现，8/6/10组与SAN、21绑定/5实际CDLL-fake检查、本机目标对象编译通过；恢复policy13组/3840步对照过但完整原生调度、seed、三模型接线仍在整合。历史首版板编译过但生产fault3→4，观察不干净/因果未证，完整保留；后又第5fault约36.5ms/guard越界，当前YuNet LATCHED CPU，YOLO/SFace DPU，camera29563/GUI29588/X1077、gap0、primary3、SFace391完成0超限。4fault已恢复，第5未解除；无重启清计数。当前214源码逐SHA闭包已齐，原unit/覆盖/四源/身份配置/库保持。旧parser无法直接承接当前mixed历史，缺内部时间字段不伪造预算；只做新严格迁移。候选尚不可部署/不称根治，Windows回执未改。
<!-- /native-critical-progress-20261024 -->

<!-- persistent-vision-recovery-final-20261023 -->
**2026-10-23视觉恢复/准入已持久启用（UTC10-24最终续查）：** [源码、163条SHA与完整实证](../../语音共享文件/deliverables/2026-10-23_vision_recovery_and_admission/README.md)。最新单终端约束后由root串行完成。SFace独立受限恢复、30ms保守准入/5ms guard、boot/重启保护承接及持久覆盖/回退落地；4源变更，原模型/库/阈值/硬cap保持。当前camera29563/GUI29588/X1077，原unit297…，持久覆盖zzzz-aura-vision-recovery-c76110abefc304bb.conf。237软件0失败/2跳过、68板隔离及60秒YOLO9.966/face3.897Hz通过，业务窗0新增超限/gap/USB，startup primary+1另记。两次实际YuNet33.678/32.964ms hardcap-only均自动恢复；第二次native16.239ms含14.006ms runqueue，GIL重获8.698ms含8.415ms睡眠，wait native0.009ms。当前约5万调用/fault2 recovery2/gap0，6739秒同PID计数续查无新增；SFace新增0、真实恢复与精度未验。资源CPU48.55%、DPU busy4.934%为非配对点测。Nice短试收益不稳定已回0，probe/instance/timer及CU统计清理、GUI175源/配置/库与回退检查通过。外部新boot原因未知且非本轮发起、旧boot拒绝传输和3次版本切换均留档。164文件/163SHA、97Python AST/44JSON核验，无权重/ELF/UART/生物数据共享。Windows回执未改；后续集成以本包4源和持久覆盖为基线。
<!-- /persistent-vision-recovery-final-20261023 -->

<!-- native-wait-diagnosis-20261023 -->
**2026-10-23等待诊断接续：** 用户允许两路，主任务独占UART，第二路精确ELF/控制器本地审查已结束。[69工件、源码与完整证据](../../语音共享文件/deliverables/2026-10-23_native_wait_diagnosis/README.md)。实际vart.so SHA dc6bff9b…，方法名/回调/24指令字证明execute native前释放GIL、后重获；SFace5788 execute30.167721ms/CPU0.580727ms，原始39.587666ms外部包围Q差0，不能直接归GIL或硬件。原生schedstat成本183.193µs未过100µs；外部60秒4.9789%单核未过2%，均不常驻。新四点UProbe自有无DPU fixture，修正append隐式seek后500轮/2000记录、额外平均CPU20.272040µs、P99完整CPU34.69µs/墙钟56.12µs、loss0/清理过，前两EINVAL保留。业务控制器9项本地检查通过，但SFace ready=false前置拒绝，未启动生产probe/60秒采样；最终own probe/instance0、timerinactive，worker failed并退出。旧camera499773的2YuNet+1SFace/gap1留证后只一次同版本恢复588727/GUI588755；又新YuNet21.03748ms guard-only退CPU、SFace39.891329ms hardcap-only停用，当前YOLO9.92Hz、身份ready=false，新fault1+1/gap0，未再次纯重启。175GUI源/模型阈值/库/30ms/5ms保持、GUI回退PID衔接及--check过，0新USB，监听false保持。下一先补SFace受限恢复/ready与probe许可隔离，再做native/GIL分段和独立准入余量；当前恢复补丁未实现。70总文件/69SHA、21Python AST/31JSON校验通过，无ELF/UART/图像/向量/库内容共享；Windows回执未改。
<!-- /native-wait-diagnosis-20261023 -->

**2026-10-23隐藏预览修复正式保留：** 用户允许两个终端，主任务独占UART，副任务只本地审查/测试。2源在vision/large unmap退休、map代次重绑、零输出停止读取、旧回调/FLUSHING及handler清理；不改像素/帧率/模型。15＋16软件、5真实Gtk/Gst、实流视觉→main→视觉通过；主页面GUI组149.8818→94.8821%单核，相对下降36.6954%，隐藏帧201→0；视觉12.73/重映射12.68Hz、角色8.06Hz，非整板/模型加速比。接受helper66cde810…，GUI535987、camera499773/X1077/unit29786434…不变；175源仅2变更，原库/配置/偏好保持、回退--check过，controller/timer inactive。首次既有保护拒启；前次试流因gap0→1拒绝且实际恢复原GUI，最后以旧gap1/fault2为基线未新增，全部失败与计数保留。当前YuNet仍CPU保护（37.069ms且guard越界），YOLO/SFace DPU后端、SFace本窗无新请求；没有重启相机清计数。交付[当前运行、源码、证据与回退](../../语音共享文件/deliverables/2026-10-23_preview_visibility_live/README.md)。新的GUI-only回退先于旧相机整包回退；Windows回执与同步接收未代填。

**2026-10-23 GUI CPU验收/同版本恢复：** 主任务串行接板，独立副任务本地审查。4源exact候选在22组2165691通道、7组164帧RGB/metadata均零差；18行为＋最终3封装/3旧分支检查通过。但ABBA各64帧CPU2857.724818→2701.569070ms，只降5.4643%，未过10%门槛，**GUI未部署/原库未换**。旧camera450495新3次YuNet硬超限35.295/31.706/30.362ms、均status0/未越guard，2恢复后LATCHED，完整保留，归因未定。停止额外测试后只做一次相同unit/源码的相机正常退出/启动，现camera499773，GUI450525/Xserver1077与原模型/偏好/阈值/新旧库SHA保持；第一次设备名预检失败没有mutation。恢复60.214秒9.9644/3.7367Hz、0新optional/主周期超限gap，SFace新0请求。最终12源、单owner、回退--check通过，额外任务/guard退出；10秒CPU63.25%、GUI组38.40%、相机21.94%，非收益对照。跨恢复仍记旧3次故障，未宣称长尾根治。见[结果、代码与证据](../../语音共享文件/deliverables/2026-10-23_gui_cpu_evaluation/README.md)。Windows回执未改。

**2026-10-23可靠性修复已正式接受：** 用户授权继续并增加一个终端，主任务独占UART、独立副任务只做审查/反例。9源含调度诊断释放/trace清理/未知native完成停所有新准入/worker故障状态/fallback计数及SFace可用性和GUI消费；210软件、26发布、71板隔离通过。正式unit29786434…/camera450495/GUI450525/Xserver1077；60.518819秒YOLO9.9308Hz、YuNet3.8170Hz/231实际native、CPU56.9187%，新增primary/optional超限、gap、USB/诊断错误0。SFace启动5次、窗口新增0，接受后累计6次，未作新身份精度或持续三模型高负载结论。原INT8/Windows库及身份配置SHA不变，30ms/5ms/周期锚点/GIL1ms不变；12源回读、880相机包/175GUI源单一消费改动、手动回退--check通过，controller/guard inactive。两轮部署工具错误已完整恢复，第三轮旧SFace36.743ms/status0停用在切换前拦住，第四轮保存故障后协调成功；原三次YuNet/C82ms环保留，不以重启清计数称根治。见[正式交付与回退](../../语音共享文件/deliverables/2026-10-23_vision_reliability_live/README.md)。当前SFace自动恢复/长尾根因/CPU收益/冷启长稳仍未完成，Windows回执未改。

2026-10-23 修订版DeepSeek补丁门槛核验：事实分析多已纠正，Patch1仍把release取在状态处理前且差值起点不同，慢finish3ms测试断言不成立；finally worker_alive=True和finally pass不能保证真实存活/trace清理。实际执行check_revision.py，另重算C的relative端点；结果见[核验及最小任务合同](../../语音共享文件/deliverables/2026-10-23_deepseek_revision_gate/README.md)。已对照AMD3.0官方blocking与v3.0释放GIL源码，未匹配实装二进制。本轮纯本地反例/文档，无新推理、部署、外部发送或生产修改，保留SFace候选及当前分工，Windows回执未改。

**2026-10-23独立审查回传复核：** [采纳与纠正清单](YuNet独立审查_复核与采纳清单_20261023.md)已整理。包内/实读pipeline_metrics SHA同4fe11137，返回端now/cpu在probe之前；runner np.empty在slot之前，现役1ms启动记录目标仍board_camera_motion.py。三条故障和49.2346分钟旧窗口已重算，SFace正常最长trace wait实际0.076061ms。3个离线反例确认20ms业务+20ms收尾仍记20ms，以及begin/finish的BaseException可泄漏active；未执行新模型、未连板或改变生产。官方AMD3.0文档及版本固定绑定源码已核，不能凭wait短排除设备等待或预设绑定不放GIL；实际二进制匹配仍未知。源码锚点/旧guard的“必错”结论改列设计契约/可达性待证，不原样实施；完整schedstat此前额外0.763ms未过成本，GIL/绑核已有实测。SFace92/16候选仍未正式部署，恢复策略未完成；CPU原任务继续，Windows回执未改。

2026-10-23 DeepSeek结果复核：用户回传报告后，确认计时尾部/SFace停用状态/worker异常退出等源码发现，并纠正return侧probe顺序、np.empty在slot外、现有包装入口SHA匹配且1ms、deadline与sleep同锚点、切换次数不能二分类GIL等。4类本地检查和3次故障时间线重算、5源哈希/AST、ZIP哈希通过；第三次82.927ms/guard越界导致当前LATCHED退CPU的新证据已附，未将旧2/2恢复当当前正常。见[核验与外部补充](../../语音共享文件/deliverables/2026-10-23_deepseek_review_verification/README.md)。本轮没有接板/部署/重启/解锁、没有外部发送，不覆盖SFace4源候选或较新语音/GUI，Windows回执未改。

**2026-10-23分工后SFace候选完成/现场保留：** 用户把YuNet超限交另一AI；本任务未改YuNet/共享调度/30ms/5ms或重启正式相机/GUI。旧正式源3反例复现，SFace停用可用性、旧结果/登记门禁及GUI语音ERROR→identity_unavailable共4源候选已修；92相关软件回归和KV26016隔离检查通过，全部内存合成库、禁VART/XIR，正式PID与源SHA保持。**候选尚未正式部署，自动恢复未实现**；见[修复代码和证据](../../语音共享文件/deliverables/2026-10-23_sface_availability_candidate/README.md)。隔离检查前已读到第三次YuNet82.926870ms/guard+0.358214ms，当前LATCHED/CPU fallback，YOLO9.94/SFace仍DPU、gap0；[新故障补充交接](YuNet审查交接_第三次超限与保护锁定_20261023.md)应与两条故障版DeepSeek包一并读取。GUI当前core p50约38.492/total41.263/public1.023ms；core含控制/音频/动画，下一步内部定位。66工件/54Python AST/SHA通过，本轮无生产/监听/模型/库/固件/运动变更，Windows回执未代改。

2026-10-23 YuNet独立审查准备：按用户要求制作[DeepSeek完整提示词和资料](../../语音共享文件/deliverables/2026-10-23_deepseek_yunet_review/README.md)，使用最新a29082ba…三模型DPU及YuNet两次30.692/31.162ms真实故障。16现役导出源、7发布PIN源SHA匹配，6辅助源码标未有本轮实板PIN，7既有测试仅审查；36 Python AST及两条故障分段重算通过，ZIP完整性/哈希通过。已生成单文件TXT与ZIP，未上传DeepSeek或其他服务，没有接板/部署/新推理，未改Windows回执。不能将资料准备称为长尾根因已修复。

**2026-10-23 UTC08:14项目未闭环问题复核：** 同三模型正式版a29082ba/camera333557/GUI333586三服务active、NRestarts0，YOLO9.94Hz。YuNet累计10678完成/2次超30ms、最大31.162ms，faults2/recoveries2且当前RUNNING/DPU；gap累计0，SFace1528次/超限0。不能把早期一分钟零超限说成根因根治。manual_pan当前FAULT，原因未复核；3.066秒CPU62.61%、GUI组36.35/相机组19.46%整板，只作热点线索。源码仍缺SFace停用后的明确可用性/恢复闭环，当前未触发；身份陌生人/多人、同输入收益、转轴实体修复、显示物理验收及PL扩展等分项见[完整问题表与下一轮顺序](项目未闭环问题与下一步_20261023.md)。两次UART只读exit0/传输SHA/echo通过，本轮无runtime/config/监听/身份库/固件/运动修改，无新agent。Windows回执未修改，语音/插话/记忆已有成果保留。

**2026-10-23 SFace正式DPU接入已接受：** unit a29082ba…/camera333557/GUI333586/Xserver1077；YOLO＋YuNet＋SFace均DPU，正式identity DPU_SFACE_INT8。独立INT8库迁入原1个登记身份（原照片/原模板复核＋5张旧留出图score0.79–0.89），旧Windows库SHA未变。新源浮点类型边界和匹配计数已修；83软件/36部署/回退检查通过。明确开测后60.345秒：YOLO9.959Hz、YuNet3.563Hz/215 native、SFace1.740Hz/105 native；已知本人KNOWN95/UNKNOWN10（90.48%接受），13点11点认出本人，gap/USB/超限0。15秒CPU64.69/DPU任务busy6.276（SFace新31次），统计已关。当前16源/880包、model/domain/config/GUI/owner审计与回退--check过，controller/timer inactive。原未过的类型检查/已知覆盖和计时流程均保留失败/恢复。交付[三模型正式DPU身份](../../语音共享文件/deliverables/2026-10-23_sface_formal_dpu/README.md)。陌生人/多用户/长稳/冷启动/严格配对性能未验；Windows回执未改。

接受后只读续查同一unit/camera298571：YOLO9.92Hz、YuNet累计2478次/超限0，slot等待1330/1330 ready/timeout0，busy撤回/gap0、source age243ms。没有改service/config或开启额外采样；数值见交付`evidence/final-read-only-liveness.json`。长稳仍按正常运行积累。

**2026-10-23最新接受版** unit `048ee59c…`、camera298571/GUI298601/Xserver1077，YOLO＋YuNet DPU。slot-notification之后用独立close Event、immutable frame stamp与deadline检查，消除共享state lock busy withdraw；一分钟clean窗口YOLO9.962Hz、人脸DPU完成227/发布3.763Hz，slot等待80次ready，gap/TTL discard/busy withdraw/overrun/USB均0，CPU57.28%。旧版本单独只读窗口gap累计6保持不变，人脸2.714Hz；两段非配对输入不作严格加速比。另142软件/33部署/PIN/恢复/17KV260隔离检查通过；15.15秒CPU55.33/DPU任务busy4.934且统计关闭。当前源config/GUI/owner审计与回退--check passed、controller/timer inactive。交付[源码、数值证据和回退方法](../../语音共享文件/deliverables/2026-10-23_yunet_event_slot_wait/README.md)。长期稳定、真实冷启动、SFace INT8身份域和CPU收益仍待做；Windows回执未修改。

**2026-10-23最新正式版本：** unit `048ee59c…`/camera298571/GUI298601/Xserver1077；YOLO＋YuNet DPU，SFace正式Windows旧库。新YuNet slot通知等待与独立取消信号接受：旧方案先有60.063秒基线含6个gap；修正版独立60.327秒窗口YOLO9.962Hz、人脸发布3.763Hz、native完成227，CPU57.28%，USB0、freshness gap/锁busy撤回/source TTL丢弃均0。80次slot等待通知全部唤醒；无native超限。15.152秒CPU55.33/DPU任务busy4.934，XRT统计随后关闭；最终只读源/config/GUI/单owner审计passed，controller/timer inactive，回退--check通过。见[当前交付](../../语音共享文件/deliverables/2026-10-23_yunet_event_slot_wait/README.md)。曾拒绝的只通知版及两次未切换预检失败均留档，当前有效版本为token版；冷启动/长期/SFace精度和严格同输入收益仍未验收。Windows回执未改。

2026-10-23后续实时复查：相机252665/unit e893930d…保持，YOLO＋YuNet DPU、4402可选调用/超限0、三服务active且零重启；新发现逐发布TTL有效期缺口2次（5ms和30～31ms），当前人脸源帧龄671ms。原native max28.069ms/恢复RUNNING，缺口记录分别7/8次时隙拒绝、有帧供给，不是新DPU执行超限。见[后续状态](受限恢复_后续状态_20261023.md)。旧短窗/审计gap0仍是历史事实，当前业务时效验收未全部通过；只读，无服务或配置更改，Windows回执未改。

**2026-10-23受限恢复已正式启用：** 当前unit e893930d…、相机252665/GUI监督252691/Xserver1077，YOLO＋YuNet DPU、正式SFace Windows。受控一次31ms延迟导致35.509ms hardcap，guard未超，经冷却/1轮探测/3次native正常自动恢复，之后60秒167次native；普通入口另60秒195次native、YOLO9.983/YuNet发布3.228Hz、CPU57.89%、USB/超限/gap0，保留正常版本。15秒CPU57.00%/DPU任务busy4.868%，CU统计关闭；最终只读累计1601调用/超限0/gap0/真实native失败0、controller与guard inactive，880包文件与11关键源码核验。回退到af337bce…入口--check通过，旧固定unit helper不适用。详见[当前源码/证据/回退](../../语音共享文件/deliverables/2026-10-23_bounded_yunet_live/README.md)。下方“候选未上板/CPU fallback”为此前时点；未称等待根因、SFace正式身份、长期/冷启动或同输入收益完成，Windows回执未改。

2026-10-23快速验证更新：受限恢复候选已实现（默认关闭），117软件回归与KV260同源24项隔离合成通过，新增每调用线程CPU均值0.0274ms；没有真实DPU新作业或生产配置/服务切换，正式YuNet仍CPU fallback。见[候选与证据](../../语音共享文件/deliverables/2026-10-23_bounded_yunet_recovery/README.md)。用户要求缩短等待，后续每轮约1～3分钟真实业务试跑、长稳在正常运行中积累，不作为后续开发前置。下方“未实现恢复”为此前方案时点，原计数/30ms/5ms保持，真正等待长尾/收益仍待验证；Windows回执未改。

2026-10-23方案交接：代码审查确认一次超限后disabled本进程内一直保持；已制定[有界恢复与执行路径方案](YuNet长尾与CPU_DPU协同_后续实施方案_20261023.md)。先做默认关闭、保留计数/30ms/5ms的恢复候选与故障注入，同时准备确切ABI的原生VART对照；再证据驱动独立单owner执行进程、CPU剖析和SFace独立INT8身份域。此为规划，无新实现/板测/部署，当前实际仍为下方YuNet CPU fallback。Windows回执未改。

**2026-10-23后续实时复查失败：** 同boot/相机198117/unit af337bce…在进程启动2263.609秒后，YuNet31.340203ms触发原30ms硬保护，现为CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN。YOLO DPU约9.95Hz，正式SFace仍Windows，音频IDLE_READY；故障±60秒与本进程启动后匹配USB告警0且查询范围已确认覆盖。execute墙钟30.547/调用线程CPU1.011ms，唯一根因未确定；CPU退回后两次3秒点测65.08/70.57%，不是收益对照。只读取证、未重启或改运行配置。下方30分钟/实际启用/20分钟审计通过是此前有效实测，当前长期稳定性未完成。详见[最新状态与证据](../../语音共享文件/deliverables/2026-10-23_runtime_overrun_recheck/README.md)。Windows回执未改。

**2026-10-23最终已启用新运行版本：** 原版协调120秒、候选120/600/1800秒均通过，30分钟5603次窗口native、YOLO9.953/YuNet3.112Hz、CPU56.44%，USB/硬超限/逐发布gap/新增主周期超限均0，协调回退verified。首次正式启用复核超限已自动回退且保留记录；监测对齐长测并补故障快照后，R2启用120.315秒通过（YOLO9.974/YuNet3.325Hz、CPU55.70%），已保留新unit `af337bce…`。实际相机198117/UI198147/Xserver1077，当前1ms/重试/light3/50ms恢复启用；原unit84116d8f…保留回退，不可当作当前活动版本。部署后约20分钟累计gap/硬超限/真实native失败0，879包文件与源/config/模型/旧身份配置回读通过，guard及CU统计关闭。15秒点测CPU54.93%/DPU任务busy4.934%/196命令，非同帧A/B。具体源、回退命令、图表和边界见[最终交付](../../语音共享文件/deliverables/2026-10-23_coordinated_camera_audio/README.md)及[ACTIVE_RELEASE](../../语音共享文件/deliverables/2026-10-23_coordinated_camera_audio/ACTIVE_RELEASE.json)。正式SFace仍Windows/旧库，真人/强交互及冷启动未重验；Windows回执与接收未代填。

最终交付68工件SHA/35 Python AST/18既有JSON/17相对引用通过；9份当前实际源码与实板879文件封装及ACTIVE_RELEASE一致，完整图表PNG/PDF/SVG/CSV已生成，回退--check已实板通过（未为测试而撤销最终版本）。本轮只使用主任务串行板卡操作，未留下辅助试验/统计/timer。原始UART/生物数据/权重未共享。

2026-10-23自主续接：用户已授权离开两小时内自主修复。相机/原常驻音频协调模块16项反例通过，原版本120.566秒流程实测通过（YOLO9.953/YuNet2.505Hz、CPU55.18%、USB0/硬超限0），原unit84116d8f…及源/config/偏好保持，guard已停；仅短流程证据。当前同版协调模块用于50ms恢复候选，原89项模型/调度封包不变，生成接线6＋协议16共22检查通过，120秒板测进行中。见[当前自主任务](自主推进_20261023_相机音频协调.md)，下方“协调尚未实现/两次USB受阻”为此前状态。Windows回执未改。

2026-10-23本轮最终状态：已在独立目录完成50ms失败恢复候选（成功仍200ms、默认关闭），89软件/35板端合成成本通过；两次上板均在50ms节拍尚未实际执行前被USB告警中止，回退均verified，不报告运行收益。两次原音频生命周期恢复后，最终原相机130028/UI130049/Xserver1077 active、YuNet DPU/原Windows SFace，8秒USB0/CPU52.18%；独立后续5.14秒窗USB0/CPU52.70%，原YuNetmax16.170ms/硬超限0。当前下一步为相机切换与原常驻音频的有界协调；尚未实现该协调或复测恢复策略。交付[源码、实测、限制与下一步](../../语音共享文件/deliverables/2026-10-23_yunet_gap_recovery/README.md)，56份工件已核验，含独立恢复审计，原始UART/生物数据未共享，Windows回执未改。

2026-10-23 UTC间隙取证新结果：light3完整85软件/19评估器及KV26035项无设备合成通过，满32条gap记录health新增CPU0.2874ms。120秒实时诊断捕获1段175ms TTL缺口：13帧供给/7次尝试/5次DPU时隙拒绝/1次busy取消，继而成功；无硬超限/USB告警、回退verified。说明至少该段不是无输入。当前独立恢复候选（默认关闭，仅实验失败轮次50ms等待，成功仍200ms）89软件与同源板端观察器成本前置通过，受保护120秒正在运行；结果、CPU代价尚待确认。未改Windows回执或正式配置。项目详细记录`logs/daily/2026-10-23-YUNET-GAP-RECOVERY.md`。

2026-10-23 UTC组合候选600秒板测已完成并自动回退：为避免旧启动结果文件冲突，v4 helper SHA `ad0e9047…`改用独立launcher namespace；同版120秒前置通过（YOLO9.886Hz/YuNet3.232Hz/CPU56.31%/USB0/回退verified）。600.09秒有效观测600.33秒，YOLO9.953Hz、YuNet3.073Hz、采集12.493Hz、整板CPU56.04%、native完成1845、USB告警0、YuNet硬超限0，原服务回退verified，原unit SHA `84116d8f…`保持。严格总体未通过：121个5秒快照有1次YuNet结果源帧龄1097ms（约415秒，前后749/100ms），而输入TTL丢弃、发布TTL丢弃、process/callback error均0；另有7个definite clipped gap intervals（保守下界已跨过TTL）。吞吐/硬保护子门槛通过，不等价于时效/长期验收。30ms/5ms不变，当前不做30分钟扩展，先分析单次>1000ms及发布间隙。helper SHA `67ceb160…`，证据目录板端`/home/root/aura-dpu-vision-20261021/postpower-retry-live/cbee206f503bab01-105026`；本机过滤记录见`/home/ghmd/aura-post-power-20261022/combined-v4-600-outlier2.log`。原始UART未共享，Windows回执未代填。

2026-10-23 UTC续查：原light2混合事件环容量16，长测slot拒绝等高频事件使gap细节被驱逐；新隔离副本`/home/ghmd/aura-yunet-retry-gap-audit-20261023`增加最多32条gap专用纯数值时刻/边界记录，复用既有时钟。14项light测试通过，5轮30,000次host合成publish中位10.509μs/调用（light2）与10.398μs/调用（候选），仅主机微基准；尚未合并、无板端成本结果，生产关闭。后续先review健康响应尺寸及候选板端新增CPU是否低于0.5ms；Windows回执未代填。

2026-10-22来电恢复：已按用户授权开始自主接续，最多两个终端，主任务独占板卡。新boot7924ac9f…原相机1017/UI1081/Xserver1077 active/零重启、YOLO＋YuNet DPU、音频IDLE_READY、无录音/转写pending，原单元和runtime保持。正在执行时效统计合成开销前置；重试源码本地完善，尚无新板测收益结论。见[本轮任务](来电后自主推进_20261022.md)，下方断电暂停/旧PID为历史，Windows回执未代填。

2026-10-22断电暂停：用户要求等电力恢复再做，主任务与两个本地任务已停止。断电前核分配120秒重测通过（YOLO9.905/YuNet2.402Hz、CPU56.66%），600秒约5分钟31.047ms真超限失败，自动恢复原相机449083/UI441175/Xserver1077，独立审计原源/单元/模型/Windows旧库、影子/埋点/timer/XRT关闭通过；这些是断电前状态。新时效观察23项本机及独立审查通过，板合成开销未执行。完整交付与来电新boot/状态核验顺序见[暂停断点](断电暂停_20261022_CPU_DPU进度.md)，下方进行中/旧PID均为历史，Windows回执未代确认。

2026-10-22进行中：主任务独占UART/实板准备原5ms GIL的CPU核分配120秒双模型观察，两个本地任务分别审查回退和分析时效，遵循用户最新三个终端许可。修正版r2的28软件/独立实板版本核对通过，首次旧face pin已部署前拒绝，见[候选代码](../../语音共享文件/deliverables/2026-10-22_cpu_affinity_candidate_r2/README.md)。预检原425227在新实验前又31.971ms保护回CPU，证据留存；同原服务正常重启至437343确认YuNet DPU，原单元/配置/UI215734/Xserver1077保持。120秒结果尚未取得，原30ms/5ms/Windows旧库不变，无新音频/运动/位流/USB复位，Windows回执未代填。

2026-10-22最终：1ms解释器间隔双模型120.77秒/603.23秒吞吐和占用保护通过，6包装检查通过、14源cbee206f…/30ms/5ms保持。长测YOLO9.8868/YuNet2.0158Hz，1218次累计native成功、最大27.2545ms、0真超限/新USB；CPU69.10%不作收益。121个健康快照有3个人脸年龄达到1000ms TTL，时效仍待优化；没有根因/三模型长期或正式身份通过结论。首次journal cursor 5秒超时在切候选前退出，保留失败后只读复核再有界启动同版一次。已恢复原相机425227/UI215734/Xserver1077，原单元/6源/模型/Windows身份配置与旧库保持，影子/producer/埋点/相关timer/XRT关闭，1ms未常驻。见[代码、原始数字证据和限制](../../语音共享文件/deliverables/2026-10-22_gil_interval_trial/README.md)。用户最新准许两个终端：主任务继续独占UART/实板，第二任务仅本地开发CPU核分配候选，不混改GIL、不接板。未动音频/运动/位流，Windows回执未代确认。

2026-10-22等待观测：67＋66软件、21项本板合成/0.264ms平均额外开销前置通过；全runqueue模式未过，仅使用轻量切换计数。120秒双模型尝试未满，最后健康65秒后YuNet31.153ms超限，execute29.959ms/CPU1.107ms、自愿/非自愿各+1、新读取0.520ms亦计入保护，根因未定，0新USB。自动恢复相机400028/UI215734/Xserver1077、原源/单元/模型/旧库保持、影子/producer/埋点/相关timer/XRT关闭。源/开销成功与失败/实测恢复见[新交付](../../语音共享文件/deliverables/2026-10-22_thread_wait_diagnostics/README.md)。下一步GIL间隔、CPU核分配分开对照（尚未实施），保留30ms硬限。只用主任务串行，无新音频/位流/USB复位/运动；现场数据和原始UART不共享，Windows接收未代确认。

2026-10-22重试实板：三源delta及A/B隔离准备完成，KV26011项纯合成重试检查/本地8项回退通过；原A60秒10次但人脸覆盖10/13，严格配对不成立。B单独60.73秒59次/0.972Hz、YOLO9.814/YuNet2.223Hz，13采样均一张脸，短测目标通过。用户允许10分钟后约45秒YuNet33.0008ms硬超限，自动恢复378714/UI215734/Xserver1077，原单元/源/模型/旧库保持，影子/producer/埋点/timer/XRT关闭。execute32.65ms墙钟/0.984ms线程CPU、wait0.079ms，0新USB，根因未定。见[本轮源和失败/成功/恢复](../../语音共享文件/deliverables/2026-10-22_sface_retry_board/README.md)。下一优先低开销长尾观测再重跑长稳，30ms保护不变。仅主任务串行；照片/声音/向量/DB/原始UART不共享，Windows接收未代确认。

2026-10-22单终端接续：音频维护owner/worker准入回执与管道候选33项本地＋本板同套隔离检查通过（不是66项），真实Gst fakesink、非MCP01/生产UI。真人13源合并60.69秒检查通过但SFace吞吐未达：YOLO9.854/YuNet2.109Hz、SFace4次/57请求/53拒绝、供给109、整板CPU66.37%无同输入收益对照。原版已恢复316838/215734/1077，原库/正式Windows身份和双模型DPU保持，影子/producer/埋点/相关timer/XRT统计关闭，覆盖窗口新USB匹配0。新有界退让重试67＋45回归通过，未上板、未证收益。见[音频源和板证据](../../语音共享文件/deliverables/2026-10-22_audio_maintenance_ipc/README.md)与[真人数据、恢复及后续候选](../../语音共享文件/deliverables/2026-10-22_sface_live_retry/README.md)。下一项重试真人对照/长稳；实际MCP01恢复、正式身份/阈值、USB根因和Windows同步接收仍未验收。未修改Windows回执或覆盖较旧共享业务主仓，无新增并行Codex。

2026-10-21 UTC14:25～14:51：单次显示驱动解除绑定5.007秒/重绑定已完成，65秒就绪预算超时后独立恢复，后检三服务active、相机1014保持、GUI19803/Xserver19802及audio-frontend入口正常；EDID0、用户仍条纹，未固化动作。按用户最新要求重点分析实体HDMI差异：历史同boot实体重插恢复、EDID0→128而49MHz/16位/PID/SHA保持，软件OFF/ON未恢复；另有EDID128仍闪的反证。新发现600秒DPMS Off，单次运行时唤醒后扫描/时钟恢复、EDID仍0；新240秒被动监视2347次无实际DRM事件，PID/四SHA保持、正常退出，实体操作与画面回执待到，不作热插拔失败判断。[完整报告与证据](../../语音共享文件/deliverables/2026-10-21_hdmi_hotplug_analysis/README.md)。保留原生首次模式、原内核及当前业务，无永久配置/运动/CPU优化，独立USB供电未做，Windows同步未代确认。

2026-10-21 UTC14:00～14:15：首次模式在新boot975f931a…再次证实N/无fb0、Xorg16.868秒首选600高，EDID0；用户仍规律条纹，并确认屏幕USB取电KV260。只读验证hub独立供电及标准协议后，端口1单次关闭请求曾清电源位，但约2秒自动重新开启，未达计划5秒；finally恢复、独立定时器inactive，MCP01/相机地址4/5及GUI1075/相机1014/Xserver1074保持。用户仍闪，不自动固化。静态窗口根像素不符，测试未证可见，不作排除证据。已请求独立USB供电单项对照，结果待现场。[源码/失败/恢复/限制](../../语音共享文件/deliverables/2026-10-21_screen_port_power/README.md)，无新生产配置/固件/运动/CPU优化，Windows未代确认。

2026-10-21 UTC13:44～13:55：按用户最新“屏幕已正常，先修复初始1024×768”，确认内核fb0和Xorg两处来源，新增uEnv参数drm_kms_helper.fbdev_emulation=0、Xorg固定本屏49MHz/1024×600/16位；其余五份受保护文件保持。一次软件重启新boot c393d68c…、原2022年#1内核，参数N/无fb0，Xorg15.864秒首次1024×600，EDID128；GUI1077/相机1016/Xserver1076 active/零重启、业务API无错。最终6项文件事务/回退检查通过，首次备份阶段__file__错误先验证无活动写入再修正；回退原件及失败备份均保留。冷启动、实体画面及长稳仍待回执；无运动/CPU优化，Windows未代确认。[完整交付](../../语音共享文件/deliverables/2026-10-21_native_firstmode/README.md)。

2026-10-21 UTC13:35～13:39复核：原2022年#1内核已运行，boot bec99c5a…、无候选initial_aux参数，uEnv05cd7369…/旧D0等待5000ms保留。USB hub/触摸/MCP01/相机均枚举，GUI1092/相机1003/Xserver1079 active/零重启，保留audio-frontend入口；EDID128、原生1024×600/49MHz/RGB565，实际时钟48999993Hz。用户仍见条纹后慢闪，物理验收失败；板上5057～5058mV不能排除屏幕供电问题。等待屏幕供电接法后单项对照，本轮仅四次只读诊断，无生产配置/显示/服务/USB重置或运动。[最新证据](../../语音共享文件/deliverables/2026-10-21_hdmi_original_baseline/README.md)。下方候选及待开机为历史状态，Windows同步未代确认。

2026-10-21 UTC13:14～13:22更新：首次AUX延时候选软件重启曾通过（EDID128、5.11581秒、实际相机/检测正常），用户自行断电后新boot e93b105e…黑屏，USB hub/触摸/MCP01/相机约60秒后整体掉线，相机/界面未就绪，冷启动验收失败。已受校验回退uEnv至原Image选择，保留较新audio-frontend业务入口；随后的软重启串口停U-Boot早期，尚未确认原内核运行，已请求现场12V断电待灯灭5秒后接回、HDMI不动。当前被动观察，无bootloader输入/QSPI写入/运动。[完整实施、失败和回退证据](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_hdmi_preinit_candidate/README.md)。

2026-10-21修复执行中：DRM status detect已单次执行，EDID前后仍0，用户反馈仍黑闪；标准DP AUX DDC读取返回Remote I/O error。首次AUX注册前等待候选已完成完整Image构建、13085导出符号集合保持，正在通过带校验串口暂存，尚未替换活动内核或重启。[候选、回退与阶段状态](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_hdmi_preinit_candidate/README.md)，[单次检测失败证据](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_hdmi_redetect_once/README.md)。

2026-10-21 UTC12:25复核/用户回执：5秒方案实屏失败，当前仍黑闪。新boot5cd17bb7…已实读cmdline参数及sysfs5000，EDID仍0；三服务active/零重启、1024×600保存时序。已完成修复方案v2：单次真实重检测对照→按证据前移首次通信等待→核实分配器/下游恢复接口；固定时序单独验证，3次冷启动筛查再10次重复验收。方案步骤尚未实施，本轮只读，原5秒配置仍保留。[失败证据与完整方案](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_hdmi_repair_plan/README.md)。

2026-10-21 UTC12:17：按用户要求配置显示链路等待5秒，已新增板端/boot/uEnv.txt，原bootargs追加zynqmp_dpsub.power_on_delay_ms=5000，SHA05cd7369…回读通过；备份和受校验回退工具已留存。当前内核仍4ms，未重启，下一次启动才生效；它是D0唤醒后至链路训练前等待，并非全部HDMI通信延后或物理HPD。新boot fc221b0d…、三服务保持/零重启、EDID128、1024×600。HDMI保持连接的冷启动及实屏效果待验收。[配置、验证与回退](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_hdmi_delay5/README.md)。

2026-10-21 UTC12:09后检：用户确认“刚才插拔hdmi，画面已经正常”。同boot EDID由0恢复128字节/SHA727d3e18…，8秒复核稳定，1024×600/59.85Hz、三服务PID及配置SHA保持。物理插拔本次有效；软件OFF/ON此前无效。未改启动参数或继续重启，永久冷启动修复仍未验证。[实屏恢复及证据](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_physical_hdmi_recovery/README.md)。

2026-10-21 UTC12:01后续：用户明确软件重初始化后仍整屏黑闪，实屏未修复。只读确认EDID仍0、无AUX字符设备，但存在DRM debugfs临时EDID覆盖接口（未写入）；16位色深已满足。未改U-Boot/1080p/分配器寄存器或重复关开。物理HDMI单次拔插结果、屏幕供电接法待回执。[官方建议核查与后续分支](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_blackflash_followup/README.md)。

2026-10-21 UTC11:58整屏黑闪恢复尝试：已执行一次显示输出关闭2.002秒/恢复，CRTC实际0→1、1024×600原时序保持，独立恢复定时器已停止。三服务PID保持/零重启，8秒帧推进正常；启动器、Xorg及业务配置SHA未改，EDID仍0。实屏恢复待用户回执，不称根治；未安装永久补丁/运动/CPU优化。[操作和验证](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_blackflash_recovery/README.md)。

2026-10-21用户已确认整屏黑闪；UTC11:50只读扫描输出active/1024×600/49MHz、RGB565一致，无持续显示报错证据。已请求电源保持、单次HDMI拔插对照，物理执行/恢复结果待回执，未控制显示/改板端/发运动。[报告](../../语音共享文件/deliverables/2026-10-21_coldboot_flicker/README.md)。

2026-10-21 UTC11:48补充：用户确认拔插板卡电源，屏幕是否随板卡掉电未核实。100次X像素采样四角/背景稳定、无黑帧；只读验证退出0/SHA与回显恢复通过，不能代替实体HDMI观察。闪烁形态仍待确认，未改板端或显示/服务/运动。详见[本次报告](../../语音共享文件/deliverables/2026-10-21_coldboot_flicker/README.md)。

2026-10-21 UTC11:43重新上电闪屏实读：新boot8817dc71…，EDID连续为0，Xorg先1024×768后按保存时序1024×600；三服务active/零重启，6秒无热插拔事件，未休眠。实际已为speech-motion/922dab49a74f，启动器及Xorg仍回退版；动画约8fps但不能当作整屏闪烁根因。本轮只读，未修复或切显示/服务/运动；断电范围及闪烁形态待现场反馈。[本次证据与下一步](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_coldboot_flicker/README.md)。

### 用户要求回退约三小时前，近期显示启动补丁已撤回（UTC2026-10-21 06:14）

按前日23:58及当日04:51同版记录恢复板端启动器cd168022…、Xorg164afc02…，共享启动器全文61d852c0…及原17显示fixture通过；无精确03:06整机快照，未擅自恢复更早语音/身份版本。GUI停止/图形服务重载后恢复main/presentation，GUI2680/Xserver监督2672/相机987均active/NRestarts0，显示1024×600；相机约12.43/9.88Hz、无错、身份开启，241组件预检及配置SHA保持。免点击PAUSED、未自动开麦。6秒7次帧推进/服务稳定通过，物理闪烁仍待回执。[回退依据、备份和证据](../../语音共享文件/deliverables/2026-10-20_ui_time_rollback/README.md)。

最初闪烁恢复命令因UART遇到板卡SOFT启动而未发送；CR停住U-Boot后已说明并仅执行原boot继续，root/回显恢复，新bootc7d18dbf…。没有烧写、运动命令或CPU优化；原修复/当前回退前文件均保留。Windows回执未代填，图片和原始UART未共享，下方HDMI补丁活动状态均为历史。

### 用户报告四角发黑（UTC2026-10-21 05:57）

私有X截图四角均浅色，1024×600/单位Transform，DRM源/目标同尺寸原点、GUI全屏、Monitor On；未复现黑角，EDID仍0。具体是整屏、控件还是玩偶区域尚待回执，需要手机完整实屏照片再定位，不认定屏幕损坏或HDMI必然根因。无显示/服务/布局/运动变更。[过滤证据和限制](../../语音共享文件/deliverables/2026-10-20_screen_corner_check/README.md)，图片与原始UART未共享，Windows回执未代填。

### 界面布局变化只读核查（UTC2026-10-21 05:52）

当前debug/connection，私有画面是服务连接页；此前演示层玩偶交流页的导航/内容不同。实际GUI等7文件及启动配置SHA同HDMI修复前基线，1024×600/全屏、GUI1455/NRestarts0，未改布局/切页/重启。右下返回文字截断观察已记录，未发布修复；用户具体变化尚未回执。另读新boot Xorg实际初始1024×600、重置OFF/等待/恢复完成，物理花屏仍待用户验收。[说明和过滤证据](../../语音共享文件/deliverables/2026-10-20_avatar_layout_check/README.md)，图片未共享，Windows回执不代填。

### 玩偶App入口只读核查（2026-10-20，UTC21日05:10）

新boot33d0dc5b…，汐蓝自启服务enabled/active/NRestarts0，GUI1455全屏Normal窗口存在，API IDLE/devices/error空。所查桌面和应用目录没有AURA/汐蓝玩偶.desktop入口，当前使用systemd自启；设备状态页底部“返回”后选“玩偶交流”。[说明和过滤证据](../../语音共享文件/deliverables/2026-10-20_avatar_entry_check/README.md)。没有新增App图标、改板端或切窗/重启；新boot仅证明此次GUI自启，HDMI初始模式/EDID/重置阶段和物理花屏未检查，显示修复验收仍待做。Windows回执未代填，跨机同步未确认。

### HDMI启动补丁已安装，等待实屏冷启动（2026-10-20，UTC21日05:02）

实际render24-budget/e06409743174启动器cd168022…→ea68cb07…，OFF失败/超时不再误记完整重置，记录OFF/等待/恢复；同boot不再次关闭，2秒配置保持。Xorg164afc02…→64457c25…，增加本屏实测49MHz/1024×600首选时序及DP-1关联，保留ARMSOC和16位。原件备份及带哈希门槛的回退脚本已保存，下一次启动读取；本轮没有重启或实际显示控制。

Ubuntu/KV260候选42软件测试通过，业务启动源码39项通过；Ubuntu独立Xorg/dummy接受配置和目标模式，仅为主机软件验证。实际GUI/241组件/触摸预检及安装回读通过，GUI监督1072/相机988/Xserver监督1056前后相同、active/NRestarts0，UI IDLE/vision、无错。当前进程仍运行旧内存代码，真实冷启动和花屏消除未验收。初次传输仅候选收尾的UART日志句柄出错，已修复工具并恢复回显、核对最终文件及板端测试后才安装。

[交付、安装证据和回退](../../语音共享文件/deliverables/2026-10-20_display_startup_fix/README.md)。下一步正常关机冷启动，HDMI保持连接，记录实屏、Xorg初始模式/EDID和分阶段重置状态；若仍花屏先保留证据再对照真实拔插。未重连轴/改固件/恢复CPU优化，轴仍Boot mismatch；旧boot锁已退出。共享只合显示函数，历史config/release不覆盖当前基线；Windows回执不代填，跨机同步尚未确认。

### 上电花屏/真实拔插恢复：显示只读取证（2026-10-20，UTC证据跨20/21日）

用户明确每次上电HDMI异常、物理拔插后恢复。新boot567106f3…实读render24-budget/e06409743174启动，EDID早期0、Xorg17.335秒实际初始1024×768，启动器等待22.276秒后按保存49MHz/1024×600设置；同boot后128字节EDID恢复，SHA727d3e18…与既有屏幕一致，首选时序/校验和解码通过。用户当次准确插拔时间仍未回执，未把外部触发动作写成受控复现。软件截图清楚、X11/DRM RGB565一致；后续CRTC inactive由600秒DPMS Off解释，不混为开机花屏。

KV260板载STDP4320分配器、公开驱动HPD路径支持优先查冷启动识别/同步与真实热插拔差异。2秒配置仍在；但实际启动器cd168022…OFF失败也可能标“已重建”，一项离线mock专项复现通过，已纠正“标记证明完整重置执行”的说法，未证实本次实际OFF失败。内核CONFIG_DRM_LOAD_EDID_FIRMWARE未启用，不能只加EDID参数解决。

七轮取证均无显示模式/输出开关、服务或板卡重启、开机配置修改及运动控制；图片仅私有存放，共享仅过滤JSON/元数据、原启动器和复现测试。[完整报告与证据](../../语音共享文件/deliverables/2026-10-20_display_boot_audit/README.md)已保存。新boot旧临时保护256477已退出；当前轴FAULT/Boot mismatch、配置旧boot、官方DPU固件，未重连/ARM或恢复CPU优化。保留旧候选及冻结交付，Windows回执不代填；物理根因具体器件、修复验收和Windows同步仍未确认。

### 转轴驱动/旧点击/PWM候选集成完成，保护仍保留（2026-10-20）

按“继续”完成隔离候选：正常结束QUIESCE等待完整脉冲及输出关闭，超时/许可/上下文异常锁定FAULT；Native ABI2/build778d2512、命令白名单及默认disabled发布门槛配对。GTK使用原始GDK/X Server时间，增加过期/心跳卡顿/恢复窗口检查，原始时间透传IPC与预检，拒绝程序/HTTP伪造点动，停止保持可用。补充复现并修正QUIESCE撞新帧多发一帧的竞态。

28新增+23原软件测试、真实GTK/X Server六检查、九个PWM场景及两个原HDL台架通过；C协议/零build拒绝及AArch64交叉编译通过，未执行库；最终RTL独立综合595 LUT/457寄存器/0 DSP和BRAM、DRC零违规，不等于联合布局布线通过。见[源码、验证及限制](../../语音共享文件/deliverables/2026-10-20_pan_safe_completion/README.md)。

UTC12:42保护256477/同boot/互斥拒绝新owner复核通过，1420µs中位记录保持；相机106060约12.49/9.92Hz无错。GUI已另切listening-timing/candidate-5a0cab12671b，五份运动组件SHA与本轮修改前基线相同、GTK更新；本轮未发起该更新、未覆盖较新GTK。FAULT/EAGAIN为新连接被锁拒绝。候选未部署，板端本轮仅两次只读，无MMIO/运动指令/文件修改；未恢复CPU优化、未加载固件或重启服务。联合实现/准确发布配对、外部波形及实体反应仍待做，保护不自动解除。52内容文件SHA/14 Python解析/32链接核验、原158冻结内容保持；共享业务源码未改，Windows回执不代填，Windows同步未确认。

### 卡顿后大幅往返：停止隔离、波形机制复现和离线候选（2026-10-20）

已按用户确认记录当前中位姿态，关联1420µs。首次API停止失败后，结束唯一Native owner253350并经审计传输仅STOP，最终flags0/lease0/epoch42/ACK41；未ARM/COMMIT或发新转动。临时保护256477仅持同一`/run/aura-vsrv.lock`，不打开MMIO，第二个非阻塞锁确认新owner被拒绝；保留隔离，不删除锁文件或自动重连放行。相机106060保持、最后GUI只读IDLE无error，CPU优化仍暂停。

源RTL离线复现STOP/租约到期截短末脉冲：1420µs请求可留下500.02µs，真实100ms续期到期场景留下1000µs；旧测试跳过active=0下降沿，正常ACK不能覆盖波形。此机制可解释异常摆动，实际J2.3、供电/断信号和机械反应尚未实测。新渲染入口已在本轮前切换，是否其他会话发布及卡顿时序待答复；旧触摸处理过晚风险存在，未证实现场重放。

ABI2隔离候选增加正常完整脉冲结束与新帧租约余量门槛，保留原立即STOP。五个新增场景和两个原HDL测试台通过；紧急截短仍可能，Native/旧触摸适配、实现/时序及外部波形和实体复验均待做。未构建或加载新固件，未修改活动业务源码。[完整交付与验证清单](../../语音共享文件/deliverables/2026-10-20_pan_stall_waveform/README.md)已保存；Windows回执不代填，旧冻结工件保持。下方“普通档再点动”为历史，当前不可试转。

### 不动反馈：指令ACK正常，普通20档待现场观察（UTC2026-10-20 11:47）

用户最近右/左5µs两次1420→1425→1420各42ACK/约2秒，failure空、READY，最终flags0/lease0/epoch36/ACK42，不能单凭此宣称实体运动。动作小/死区只是待确认解释。仅将UI步长恢复20，实屏/诊断左停右均可用，位置1420及readback/history前后相同，发运动0；未重启/重连/改业务源码/范围，CPU优化仍暂停。待现场普通右转观察，再核对外部供电/共地/信号，见[四内容工件SHA及记录](../../语音共享文件/deliverables/2026-10-20_pan_motion_visibility/README.md)。Windows回执及原冻结交付保持。

### 左转/重连灰色核查与细调选择（UTC2026-10-20 11:43）

实读1415µs/普通20、READY且无错误，左候选1395低于1400所以灰；重连灰表示当前已连接。面板关闭使首次选项脚本在点击前退出，随后重新打开并只选精细5，左/停/右实际sensitive均true，右侧无相机截图核对通过。选项内部硬件读回/history不变，未发运动/重连、未重启服务或改业务源码；第二次脚本开始前位置已是1420/epoch34/ACK41，操作前后保持该值/flags0/lease0，不能将现场位置变化归给脚本。CPU优化继续暂停。见[四工件SHA核验与证据](../../语音共享文件/deliverables/2026-10-20_pan_fine_step/README.md)，Windows回执和旧冻结交付不改。

### 摄像头消失：整界面审查、显示修复和实屏验证（UTC2026-10-20 11:06）

用户明确卡住指摄像头画面消失。相机/DPU/帧传输持续正常，但实屏原生区域有旧弹窗残影；新放大预览正常。GTK因250ms过期隐藏DrawingArea、恢复同XID时跳过重绑，另有模态遮挡和跨窗口控件诊断坐标风险。已保持原生画布、每次map重绑，调轴改右侧同窗口面板，离页/返回STOP。共享旧GTK只改相同两处逻辑，板端精确补丁基于较新voice-barge-in版本。

347完整回归、真实GTK/Gst合成屏幕像素（过期清屏/恢复、五次同XID切页、三次调轴开关）通过。实板只重启UI一次、无回退：监督225296/轴225369，相机106060保持12.5Hz采集/约9.92Hz检测/身份开关保持。实际视频恢复、右侧125×64按钮不遮挡、保存诊断COMPLETE/errors空；238项SHA全匹配，原230核心中229保持，仅GTK显示逻辑变更。两次真实切页/开关及20秒40样本无服务/预览错误，39新鲜/1次250ms清屏后恢复；CPU约3.4/4核，尾部压力及长稳另待验收。

运动命令0，1415µs、flags0/lease0/epoch31/ACK41/history空，中位未校准/跟随未启用。当前启动drop-in指camera-fix-v3/startup，HDMI2秒及同boot标记保持。新建[完整交付](../../语音共享文件/deliverables/2026-10-20_camera_preview_pan_audit/README.md)，32内容文件SHA/长度核验通过，不含真实相机/人像、身份库、原始UART或权重。Windows自行回执，不代填；后续须合预览补丁和新版pan_controls，保留最新语音基线与manual_process。原三份冻结交付保持。

### 再次卡住反馈的范围核对（UTC2026-10-20 10:40）

只读发现控制READY、error空，最近10次用户点动epoch14～23均成功。当前位置1410µs、flags0/lease0/epoch23/ACK40，原owner STOP请求后保持READY/输出关闭；未新点动或重启服务。按left_sign=-1和普通20步长，下一左目标1390超1400已测下限，现有界面会禁用左键；建议切5µs，可继续到1405。具体是否仅左灰已询问、现场待答，未把本轮判为ACK再次失败或机械中位。见[本轮记录](../../语音共享文件/deliverables/2026-10-20_pan_manual_boundary/README.md)，Windows回执和此前冻结交付保持。

### 手动按钮变灰已修复、实体回归通过（UTC2026-10-20 10:32）

原故障为右转后FAULT/ACK mismatch，3条/240.99ms，输出保护关闭、位置1450。已更新前轮附加模块为独立控制进程、保留100ms租约、记录故障前状态并增加不重放的显式重连；原GTK/语音/身份230组件SHA保持。347主机回归、23板端软件测试、GTK模拟通过；实际四段1470/1450/1455/1450µs共165条ACK无异常，各段恢复READY和STOP。重连后台206103→207278且无追加动作，最终1450/reference1455/epoch13/ACK41、flags0/lease0，中位仍待用户确认。

当前GUI监督206028、实际GTK206098，控制进程207278的PPid=206098，独立解释器得到实读验证；相机106060约9.93Hz/身份true/无错误保持。own drop-in现指向fix-v2/startup，HDMI2秒/联合VART保持，Windows回执及原43份冻结工件未改。后续发布须携带manual_process及新的附加文件/manifest，见[修复源码、证据及保留说明](../../语音共享文件/deliverables/2026-10-20_pan_manual_ui_fix/README.md)。

### 视觉追踪手动转轴按钮已上线（UTC2026-10-20 10:12）

按用户新需求增加可选GTK入口及左/右/停止、20/5µs、左右互换和当前位置数值，用户自行调正后再告知Ubuntu中位。339项主机完整回归、15项板端软件控制测试、真实GTK模拟按钮/布局检查通过；972载荷收集包含附加模块、排除本板许可配置。原生界面打开调轴窗口ACK通过，上线时手动接口READY/1430µs/flags0/lease0/epoch8/ACK46，安装/开窗没有发点动，history为空，中位未校准、跟随未开启。

基于实际voice-barge-in/667b70d586ca新增5份源码/测试和本板配置，原230项组件SHA保持，独立80-aura-pan-manual-20261020.conf指向附加启动器；界面185828→195564受控重启，相机106060/约9.93Hz/identity=true/无错误保持。原语音打断和身份文件未覆盖，开机HDMI off继承的1秒恢复用户既有2秒要求，同boot标记保留。新boot/错误平台不自动ARM，当前GUI独占Native锁；实际点击转动/左右方向和用户选定中位由现场继续验收。详见[代码、证据与Windows保留说明](../../语音共享文件/deliverables/2026-10-20_pan_manual_ui/README.md)，Windows回执未改。

### 1450仍右后的1430µs修正（UTC2026-10-20 09:18）

用户反馈“还有点偏右”，以1450临时参考保持1430µs两秒，46条连续ACK/端点与独立STOP通过，终态flags0/lease0/width1430/reference1450/target1430/epoch8/ACK46，输出关闭。相机106060、当前GUI165304前后active/PID不变，相机约9.93Hz、identity_recognition=true、无相机检测错误，GUI IDLE/STOPPED，身份字段UNKNOWN。准备校验阶段无动作，提示开始后只执行一次；未改生产源码/服务/位流/HDMI/语音配置。

新源和过滤证据另存[第六次试步](../../语音共享文件/deliverables/2026-10-20_pan_midpoint_step06/README.md)，此前冻结原件和Windows回执保持。1430是否居中待现场反馈，未正式标定参考、确认停稳模式/图像极性或启动自动跟随。

### 可见大幅往返及1470/1450µs修正（UTC2026-10-20 09:03～09:10）

按“动作再大一点”完成1580/1420/1490各3秒的一次固定往返，208条ACK/端点和独立STOP通过，epoch5、输出关闭。第一次GUI HTTP8783拒绝导致动作前退出，只读复核事务未创建；改为尽力记录GUI状态后再准备，实际动作仅一次，身份采样/相机健康及硬件门槛保持。当时GUI仍activating，不写成健康通过，也没有修复或重启GUI。

用户确认“看清了，现在还有点向右偏转，再转一下”，1490→1470µs保持2秒，46条ACK/端点/独立STOP通过、epoch6。用户随后“还是朝右”，继续1470→1450µs两秒，46条ACK及独立STOP通过；当前flags0/lease0/width1450/reference1470/target1450/epoch7/ACK46，输出关闭。已询问1450是否改善/居中，现场结果待到，不把任一测试脉宽写作已标定机械中位或启用跟随。

两次修正相机106060、GUI162389均前后active/PID不变，约9.93Hz、identity_recognition=true、无相机检测错误，GUI已IDLE/STOPPED；身份状态先UNKNOWN、后KNOWN，仅作字段记录。准备不发PWM、开始提示后短启动器单次执行；未改生产源码、服务、位流、HDMI或语音配置。Windows回执保持，过滤证据及独立清单分别见[大幅往返](../../语音共享文件/deliverables/2026-10-20_pan_visible_direction_wide/README.md)、[1470试步](../../语音共享文件/deliverables/2026-10-20_pan_midpoint_step04/README.md)、[1450试步](../../语音共享文件/deliverables/2026-10-20_pan_midpoint_step05/README.md)。

### 小幅看不清后的1460～1540固定往返（UTC2026-10-20 08:51）

用户补充“转动有点小，没看清”，继续既有重测要求，执行1540→1460→1490µs各约2秒，共6秒，硬件限速/100ms租约/1秒端点/finally STOP保持。137条ACK与独立终态通过：flags0/lease0/width/reference/target1490、epoch4、ACK137，输出关闭。相机106060/GUI141059前后active/PID不变，约9.93Hz/身份ready/无错误，业务源码配置/服务/位流/HDMI/语音保持。

已问前两段实际方向及固定指令下会停稳还是持续转，尚无本轮现场答复；未从寄存器推定机械角度/模式、未标定中位或启用跟随。原冻结工件保留，Windows回执未改。见[本轮交付](../../语音共享文件/deliverables/2026-10-20_pan_visible_direction/README.md)。

### 正向加重右偏后的反向试步（UTC2026-10-20 08:42）

用户“更偏右了”记为正向增脉宽在用户视角下加重右偏，未直接改镜像跟随polarity。按硬件限速从1520测试点保持1500/1490各2秒，91条连续ACK/各段端点及独立STOP通过；最终flags0/lease0/width1490/reference1520/epoch3/ACK91，输出关闭。相机106060、GUI141059前后active/PID不变，约9.93Hz/身份ready/无错误。业务源码配置、服务/位流/HDMI/语音保持，机械参考及完整跟随未完成。

随后用户要求“重新测试，人嗯他反向转动”，已问清“反向”指校准动作还是人与镜头方向相反，保持停止并未执行额外重测。详见[本次交付与原话](../../语音共享文件/deliverables/2026-10-20_pan_midpoint_step03/README.md)，Windows回执不改。

### 1504无明显变化后的1520µs有限校准（UTC2026-10-20 08:36）

用户“几乎没有变化”补记到1504姿态反馈。继续既有校准，从上次测试参考1504、按硬件斜坡到目标1520µs，约2秒后STOP，46条ACK/阶段读回及独立终态通过：flags0/lease0/width1520/reference1504/epoch2/ACK46，输出关闭。已问有输出时向哪边移动，以及关闭后是否回位；不能据此称死区/方向/中位/完整跟随已验收。

第一次在发动作前因继承的GUI空闲检查退出，复核事务目录不存在；改为记录UI状态、守卫身份非ENROLLING/SAMPLING，原硬件/lease/STOP门槛不变，再执行一次成功，实际动作仅一次。当时GUI已IDLE/STOPPED，因此不作播放并发验收。相机106060/GUI141059前后active/PID不变，约9.92Hz/身份ready/无错误，业务源码配置/服务/位流/HDMI/语音保持。见[本步交付](../../语音共享文件/deliverables/2026-10-20_pan_midpoint_step02/README.md)。Windows回执未改。

### 右偏反馈后的1504µs校准步（UTC2026-10-20 08:26）

用户“偏右”更新为1500µs姿态未居中。继续既有调试，在此前已测试范围内保持1504µs约2秒后STOP，46条ACK/阶段脉宽及独立flags0/lease0/width1504/ACK46回读通过；未推定方向或建立机械参考。已询问相比原姿态是更靠中间、更右还是无变化，反馈待到，输出关闭。程序采用已测有限台架流程，增加ACK46/原脉宽1500/未解锁初态检查，主机默认/拒绝/单目标门槛及板测通过。

相机106060、当前handsfree/resume-049c88498ae0 GUI141059均前后active/PID不变、相机约9.92Hz/身份ready/无错误，未回灌旧GUI或改业务源码/配置、重启服务、切位流。原冻结工件保留，Windows回执未改。详见[本步交付](../../语音共享文件/deliverables/2026-10-20_pan_midpoint_step01/README.md)。

### 首次转动现场确认（UTC2026-10-20 08:20）

用户明确反馈“转动了”，有限台架测试机械响应已由现场确认，方向/当前是否正前方/卡滞抖动异响仍未知。已询问朝向及异常，没有据此伪造机械参考或无异常结论。本轮复核同boot/联合平台及停止寄存器：flags0/lease0/active=false/armed=false/ACK46，未发新脉冲；相机106060、约9.92Hz/身份ready/无错误。只新增现场补记和停止证据，上一轮13份冻结工件原样保留，Windows回执未改。见[现场补记](../../语音共享文件/deliverables/2026-10-20_pan_first_pulse/field-observation/README.md)。

### 首次有限定位测试（UTC2026-10-20 08:13）

用户明确要求立即试一次，按此前已说明的首次1500µs定位及±4µs/约2秒计划执行，46条ACK/各段脉宽回读通过；finally和重新打开传输后的独立读回确认flags0/lease0/active=false/armed=false、ACK46，输出已关闭。机械观察/外部波形/机械零点尚待确认，完整跟随未通过，不自动重复或扩幅。已通过问题工具询问现场动作及异常，尚未收到反馈。

本次未改生产源码或unit、未重启服务/切固件。实际相机为handsfree/0c0a8ab46ec2、PID106060；实际GUI已更新avatar-performance/8049378caf0e、PID132404，均前后active/PID不变，原相机约9.92Hz/identity=true/无错误。旧GUI不回灌。13工件按长度/SHA核验，实际执行脚本与前轮冻结SHA919a5901…一致，原始UART/图像/身份库不共享。见[本轮交付](../../语音共享文件/deliverables/2026-10-20_pan_first_pulse/README.md)，Windows接收由其回执确认。此前下方“未输出PWM”仅适用于07:21时点。

### 转轴联合平台和实况接口接入结果（UTC2026-10-20 07:21）

已在现场最新handsfree-dialogue/candidate-0c0a8ab46ec2目录完成同进程motion wrapper接入；新增6文件、原身份/相机/GUI等14份源码配置SHA保持，GUI PID104694保持，相机106060。联合DPU+VSRV固件operating，当前VART准确指向联合xclbin；模型预检/ID/STOP通过，独立复读约9.46Hz、identity=true、无相机/检测错误，新motion路由真实READY。10秒143次/96源帧，READY23/NO_TARGET118/EXPIRED2；shadow因边缘目标锁停、接受0，仍存在最坏时延超过250ms问题，未启用真实跟随或发ARM/PWM。最终flags0/lease0/ack0。

早两次因VART不变的错误检查自动恢复官方固件/原相机；修正准确联合路径检查。第三次在改动前遇到现场切handsfree新版，重新盘点后第四次在最新版接入成功；不覆盖旧unit/源码。28份工件按长度/SHA核验，先前失败/回退和实况坐标全部保留，未共享图像/身份库/原始UART。首次1500µs定位及±4µs/2秒脚本已准备，默认计划/确认/非板端拒绝检查通过，实体路径尚未执行，待用户现场确认线材和转动空间。详见[接入交付](../../语音共享文件/deliverables/2026-10-20_pan_axis_integration/README.md)。Windows接收由其回执确认；后续身份/免按键更新请保留motion入口及HDMI2秒/原语音设置。

### 转轴接入窗口（UTC2026-10-20，开始时声明）

用户已确认DS3230/J2.3/独立供电共地、摄像头随轴转。本轮Ubuntu仅新增motion扩展/工具到当前最新相机目录，调整该相机服务的可选启动入口；不编辑身份/原相机/GTK源码。相机空闲且DPU使用者退出后，受控检查已有DPU+VSRV联合平台、ID/STOP及视觉共存，然后做真实源软件旁路；保持PWM关闭。当前设备树1420属性/213节点、保留内存和版本与已测源版本一致，联合DTBO离线合并通过。此段为执行声明，结果另填；Windows身份源码及回执由Windows自行更新。

任务版本：`AURA-COLLAB-20261018-r1`；初始记录：2026-10-18。

## 当前已完成

- 已按原始 ZIP 入口、现行分工、最新整体报告和 2026-10-18 网络日志核对任务起点。
- 已创建共享根入口、任务总表、双方分开填写的回执和关键证据摘要。
- 实际读取微力：`34BZNXC`、`JoneNike` 均在线；两项任务指向 `/home/ghmd/Win共享文件`。UTC 08:22 快照中，JoneNike 已报告拥有本轮 8 份任务/参考文件的当前索引版本；34BZNXC 仍扫描中，尚无全部新文件的版本确认。该结果不是 Windows 磁盘独立 SHA 或人工接收确认。
- 新增 5 份 Markdown 的 14 个相对链接全部可解析；既有 ASR 必需 11 文件按原清单重算长度和 SHA256，11/11 匹配。此项为 Ubuntu 本地文件验证。
- Ubuntu 当前网络检查只有 Wi-Fi `172.23.222.189/16`，本轮没有修改两端网络配置。

## 任务状态

| 任务 | 状态 | 已有结果 / 下一步 |
| --- | --- | --- |
| U0 共享任务创建与索引确认 | 待对端复核 | JoneNike 的 8 文件当前索引已确认；34BZNXC 仍扫描；Windows 回执尚为初始模板 |
| U1 板端访问 Windows ASR | 已验收 | UTC 09:18—09:20 板端到 8791 ASR 及当前 8792 对话服务均真实 HTTP 200 / actual / ready |
| U2 新录音/取消/断连恢复 | 待执行 | 已具备服务前提，下一步实录问答、字幕、出声和异常验收 |

## UTC 2026-10-18 09:20 现场更新

已重新通过串口只读验证：板卡到 Windows 8791 ASR 健康 HTTP 200 / actual / ready=true；当前界面启用的是 `192.168.50.1:8792`、conversation=true，对话健康同样 200 / actual / ready，含 Paraformer / Qwen3 4B / OmniVoice 16 步。因此 U1 的网络及服务前提已通过，旧 FAILED 记录保留为历史。

UI 在演示层 main / IDLE，可开始录音，无错误；保留 80000 样本录音和 13 字 READY 转写。相机同 PID/代次持续采集。尚未在本轮发起录音或声音播放，也没有实物出声确认。下一步按[实机语音问答验收](下一步_实机语音问答验收.md)执行；Windows 回执及已部署源码版本仍待补齐。

## 最近已保存板卡状态

主机 UTC `2026-10-18 07:59` 经 USB UART 记录：板卡 `eth0 UP/LOWER_UP`、`192.168.50.2/24`；旧目标 `192.168.50.1` 邻居 FAILED，22/445/8791 失败或超时，健康接口 No route to host。板端时钟仍在 2021 年，证据时间使用主机时间。

本次编写任务未重新操作板卡录音、模型推理、显示切换、运动、服务启动或整板重启。相机和显示最新实测范围见“当前进度与证据”。

## 后续执行填写区

### 转轴连接只读检查（UTC2026-10-20 06:56）

用户报告连接转轴，已确认串口/板卡operating，现相机2004/约9.93Hz/identity=true、GUI41716/main/IDLE，仍加载官方kv260-benchmark-b4096。板上VSRV联合版8个程序/4个固件SHA匹配，但固件访问门槛不满足、ZOCL refcnt3，未切换平台/重启生产服务/打开MMIO/输出PWM。现场型号/线序/独立供电共地及摄像头是否随轴转已询问，暂无答复，不把连接报告当作电气或机械标定完成。新增6份过滤证据和连接检查JSON，见[记录](../../语音共享文件/deliverables/2026-10-19_pan_follow/connection-inspection-20261019.json)。Windows回执未改。

### 转轴跟随开发（2026-10-19，开始）

阶段结果：7个新增源码文件及说明已完成，9份含依赖源码冻结，29份工件长度/SHA通过。Ubuntu完整框架324项通过，其中35项新增运动/坐标测试；KV260加载实际enrollment-photos相机模块跑35项软件测试通过，90个fixture源帧/86次软件接受/结束DISARMED，临时HTTP端口验证新路由和原health兼容。测试前后相机PID2004、GUI41716、boot3e1add36及官方位流保持；初次05:06 GUI7187是更早现场版本，不把Windows期间的版本更新归因于本任务。首轮测试环境/NamespacePath加载差异已定位并修复测试方式，失败证据保留。没有部署生产坐标接口、切位流、ARM或PWM，不称真人实况/机械跟随完成。交付与Windows接入说明见 `语音共享文件/deliverables/2026-10-19_pan_follow/`；下一步协调相机入口加载→真人实况旁路→机构/参考标定→配套VSRV平台及显式启停/受控机械验收。Windows身份回执未改；下面是开始前的范围记录。

用户安排Ubuntu负责转轴跟随、Windows做身份识别。计划只新增 `common/motion_observation.py`、`board/motion/{camera_feed,follow}.py`、独立相机扩展/跟随工具、配置/测试及交付；不编辑Windows身份文件或覆盖当前ui_camera_service/GTK源码。相机扩展通过独立入口加载同一份现有相机服务，只增加只读坐标接口。05:06 UTC实板固件为kv260-benchmark-b4096.bit.bin，当前不具备VSRV，未读取未知MMIO、未切位流/ARM/PWM。当前相机identity=true/约9.91Hz；界面空闲但已经更新到新根，旧b1b08和stage目录不得作为最新业务基线。机构/相机安装状态已询问，答复前只做软件和无输出验证。旧方向确认polarity=-1、已测脉宽范围及VSRV/1保护作为历史依据，不当作新机构已标定。

### 每次开机HDMI重初始化（UTC2026-10-19 04:46）

用户明确要求普通重启及断电开机自动重启HDMI输出。实查当前b1b08开机服务enabled，原启动器已启用每boot一次1秒输出关闭；本轮仅将实际 `startup/config.json` 的 `display_retrain_off_seconds` 改为2，原件已同目录备份，原GUI/组件清单和服务PID保持。修改前后实机预检通过，17项显示逻辑测试通过，新boot标记失效/同boot不重复由既有逻辑处理；9份冻结交付长度SHA通过，当前EDID实读128字节。未替用户整板重启或断电，实际冷热启动与物理花屏修复未验收。见[本轮配置与记录](../../语音共享文件/deliverables/2026-10-18_hdmi_boot_reset/README.md)。Windows回执保持。

### 同进程DPU身份相机后端接入（2026-10-18，开始）

最终恢复补记（UTC04:42）：04:39观察到第二次新boot f4789036，重启来源待用户确认，板上无pstore和持久化上一boot日志。恢复原服务的首次前置检查遇8783拒绝连接，未改动；待界面active后复核IDLE、原版本预检通过，后台实际还原两份备份unit。最终原相机PID2300/旧stage目录、原连续对话监督器PID2302/b1b08目录均active；相机9.82Hz/帧龄98ms/无错误、界面main/IDLE可开始，电脑actual/ready/27B/OmniVoice16，登记接口仍缺。DPU候选已撤回，未改身份预算或模型。实体花屏是否经显示重置恢复仍待现场确认，不能写成已修复。以下04:36补记及更早状态保留为历史。

最新补记（UTC2026-10-19 04:36）：用户明确“已结束”，只读确认IDLE/停止录音/电脑服务不忙后，执行最终后台切换；04:29两服务目录已指向候选，相机active、界面activating。04:30起串口连续无回传；04:33恢复后boot从94bbc908变为6b3d1961，切换结果文件不存在，无法确认重启原因或独立回退已完成。新boot下候选两服务active，身份一次20.11ms触发20ms保护暂停，ready=false；没有真人登记。用户报告屏幕花屏，X11私有截图完整、EDID实读0字节；已校验原49MHz/1024×600时序并关闭输出1秒后恢复，软件模式回读通过，实体是否修复待用户确认。冻结源码及Windows回执保持；过滤证据追加到本轮交付，截图和原始UART不共享。下段为此前时点。

阶段结果：289项主机unittest通过；新适配器4组固定输入在真实DPU逐字节匹配，80检测+16身份无周期超时、SFace中位7.86ms，公开人脸5帧事务只在内存提交。正式服务切换尚未完成：第一次38秒就绪期限不足已回退且原界面恢复；第二次在前置检查发现界面正在使用而拒绝，没有服务改动，当前正等待用户结束对话的回复。已准备100秒启动/180秒独立回退的最终辅助，尚未执行。Windows新接口也待加载，登记开关保持false。28份源文件/24份过滤证据长度SHA核验通过，见[本轮状态、源码、回退和Windows脚本](../../语音共享文件/deliverables/2026-10-18_identity_dpu_runtime/README.md)。Windows回执未改；下方为开工与范围记录。

用户继续询问“现在做什么”，按既有身份DPU及语音启动目标推进。UTC2026-10-19 03:51实板只读复核：原boot、相机PID141309/9.93Hz无错误，UI main/IDLE、转写ANSWERED；Windows8792已恢复actual/ready、27B/OmniVoice16，缺少voice_text_channel字段；identity=false。本轮计划新增 `board/identity/dpu_sface.py`、`board/vision/dpu_schedule.py`、DPU专用身份配置及测试，修改 `board/identity/{camera_faces,live}.py`、`board/vision/ui_camera_service.py` 接同进程检测优先调度和模型标识，候选及验证写入 `语音共享文件/deliverables/2026-10-18_identity_dpu_runtime`，先快照。基于现有工程xmodel，不声称真人校准完成，不混用CPU模板；不自动保存真人图像或登记。受控固定输入板测/运行候选先做可恢复验证，保留当前流式GUI、FPGA和语音参数。

实际服务进一步读取发现GUI已换到 `/home/root/aura-automatic-conversation-20261018/candidate-b1b08f8b0b2b/runtime/aura`，PID189163，automatic_turns=true；旧ec77目录仍存在但不是当前服务根。两份GUI/录音源码比共享副本更新，新增自动采集和worker方法尚未回收到共享。扩展本轮范围：回收并合并 `tools/{board_avatar_gtk,board_recording,board_avatar_worker}.py`、`board/runtime/audio/{automatic_capture,vad}.py` 及相应自动对话测试/配置；语音登记补丁与新版自动对话并存，先保存双方版本，避免旧身份候选覆盖已运行功能。

接口核对补充：Python接口已有identity_collect/identity_cancel，本轮同时补齐 `common/schemas/{board_ui_command,board_ui_snapshot}.schema.json` 的动作和参数定义，快照原件后修改；属于接口资料同步，不改变模型或语音参数。

### 当前玩偶交流页只读检查（UTC2026-10-19 03:03后）

用户询问在玩偶交流页下一步。实际经独占串口读取原boot：UI main/IDLE、音频IDLE_READY、可以录音；相机PID141309、检测9.92Hz/帧龄101ms且无错误；identity=false，语音登记未启用。板端到Windows192.168.50.1:8792健康请求本次超时，界面保留TRANSCRIBING。不能由单次超时确定服务停止或网络根因，先取消当前转写、核对Windows启动语音服务，再验普通录音问答。见[操作与过滤证据](../../语音共享文件/deliverables/2026-10-18_voice_identity/现在在玩偶交流页_下一步.md)。本轮未录音/播放/登记/重启，串口回显已恢复，未改Windows回执。

### 语音触发摄像头身份登记（2026-10-18，软件候选通过）

软件候选已完成：语音询问称呼/确认、唯一人物绑定、相机五帧聚合事务及真实结果TTS；普通对话仍走原27B，每轮仅一次ASR。最终271项unittest和额外7项函数回归通过，新27项包含回环HTTP/真实SQLite及合成ASR/TTS/人脸。16份源码/配置/文档冻结并做SHA核验，见[交付与验证](../../语音共享文件/deliverables/2026-10-18_voice_identity/README.md)。未部署/采集真人，默认开关false；当前相机身份仍是CPU候选，正式DPU相机后端、真人听音及准确率待验。下段为开工范围记录。

用户指定通过语音助手下达“记住我是谁”启动登记。本轮在语音共享根实现可回归的软件候选：询问称呼/确认、唯一人物绑定、多帧采样事务及真实结果播报。计划修改 `aura/board/identity/{live,camera_faces}.py`、`board/vision/ui_camera_service.py`、`board/interaction/ui_contract.py`、`board/runtime/audio/{voice_channel,channel_jobs}.py`、`tools/{board_avatar_gtk,board_recording,board_model_host,voice_channel_source,package_board_avatar}.py`，新增语音登记控制器、配置与测试/文档；先保存源文件快照。保留现有27B/OmniVoice/流式参数。当前不修改Windows回执、不自动启动真人采集或替换板端服务，DPU正式相机集成及真人验收单列。

### SFace DPU工程实板及固定图混跑通过（2026-10-18）

用户授权“可以”并要求“继续”。实际完成INT8工程校准、导出、B4096整图编译，10,796,371字节模型，4组固定输入在物理DPU与主机量化输出逐字节一致。原并行Runner因YOLO进程独占DPU而等待；三次受控停止/恢复相机均成功，GUI进程及配置/boot/位流保持。修正首轮VART wait元组签名错误，失败和恢复证据保留。

单进程固定图测试50次YOLO基线、100次YOLO+20次SFace，预定10Hz/2Hz，周期超时0、身份特征逐字节一致；SFace中位7.677ms。末次相机恢复PID141309，新代次；20秒约9.895Hz、帧龄最大151ms、无错误，streaming=true，identity=false，恢复定时器清理完毕。未替换生产源码/模型、未登记/采集真人、未验证真实相机身份混跑或精度。

58份工件逐项SHA通过；模型、源码、过滤结果见[本轮完整入口](../../语音共享文件/deliverables/2026-10-18_identity_dpu/README.md)。下一步仍需授权校准/独立评测数据、正式同进程调度、多样本登记与多帧确认，不混用CPU模板。下方开始/暂停状态为此前阶段。

### SFace DPU量化编译恢复执行（2026-10-18）

用户在明确“准备数据→量化编译→板验→混跑→界面”的顺序后回复“可以”，恢复本轮执行。先使用已有公开参考图的光度变换做工程链路验证，不作为代表性身份校准集或准确率交付；另向用户询问授权真实样本来源，未获明确采集授权前不采集/保存真人图片。实验在独立Ubuntu目录及禁网Vitis AI3.0容器中进行，源码/结果摘要写入 `语音共享文件/deliverables/2026-10-18_identity_dpu`。保持当前YOLO、语音、FPGA及线上身份库，先完成可复核候选后再考虑部署。

### 整个项目模型总盘点（2026-10-18）

用户澄清范围为整个项目模型，已按配置/实际权重目录/最新语音及旧板测、ZIP方案核对，新增[完整模型清单](../../语音共享文件/deliverables/2026-10-18_identity_dpu/整个项目_模型总清单_20261018.md)。固定名称六项YOLOX/YuNet/SFace/Paraformer/27B/OmniVoice；另列Light-ASD和VLM待接任务、旧KWS/TTS/对话/身份候选，不计规则/跟踪/研究思想为独立已部署模型。当前文本LLM未接图像，不报告VLM完成。未修改生产配置或继续量化、编译、部署。

### DPU模型选择评估（2026-10-18，只读）

用户询问当前哪些模型适合DPU，本轮保留暂停执行状态。核对实际模型/配置、旧CPU板测、SFace初检及官方Vitis AI3.0文档，建议保留YOLOX、下一项适配SFace、再评估YuNet；其他语音/27B/首版ASD继续Windows。新增[选择建议](../../语音共享文件/deliverables/2026-10-18_identity_dpu/DPU模型选择建议.md)及项目日志；未量化、编译、部署、改生产源码或运行配置。原始CPU时间是旧固定图参考，不是当前并发性能或加速比。

### 身份设计复核：按用户要求暂停执行（2026-10-18）

用户明确身份用DPU后，最新要求“等一下，先看看整个项目，身份识别具体怎么做”。本轮转为方案/代码/保存板测只读复核，暂停进一步量化与部署。新增独立量化脚本存在，但未见量化日志或输出目录，没有得到INT8模型。未改生产源码、未部署或重启服务。

复核发现原方案要求多样本登记及多帧稳定确认，当前CPU候选仅单模板/单次新鲜结果，尚不满足这两项。目标是DPU SFace提特征，CPU做YuNet/对齐/匹配/数据库/界面；加人是登记模板，不重训网络。详见[身份具体做法与实际缺口](../../语音共享文件/deliverables/2026-10-18_identity_dpu/身份识别_具体做法与实际缺口.md)。本条优先于下方“开始”执行状态；恢复前不继续未完成量化请求。

### 用户明确身份使用DPU（2026-10-18，开始）

用户最新明确“要用dpu”。本轮目标改为现有B4096上的SFace INT8量化、完整编译与实板执行验证，不先部署CPU身份后端。CPU仍可做YuNet检测/对齐、匹配数据库和界面。使用独立候选目录，保留当前视觉位流与新版流式语音，不覆盖活动运行目录。新增工具/交付记录位于 `语音共享文件/deliverables/2026-10-18_identity_dpu`；实验缓存放在既有Ubuntu独立工作区，私有人脸不进入共享目录。

已向用户询问代表性人脸校准数据来源；回复前只允许用既有公开参考图/数值对照输入验证工程链路，不能据此声称身份精度已验收。生产源码有必要改动时，先继续在此列明路径。

### 最新串口实读与判断纠正（UTC2026-10-19 01:43，本地10月18日）

此前“未检测到串口”仅是沙箱设备视图，不是主机断连证据。获准主机检查识别4路Xilinx UART且无占用；稳定if01口确认root、aarch64、原SD CID，响应长度/SHA及回显恢复通过。GTK active/PID1457，运行新版 `aura-stream-playback-20261018/candidate-ec77f48a63de/runtime/aura`；相机active/PID987，快照9.95Hz、帧龄78ms、最近检测调用32.45ms、identity_recognition=false。未部署、录音、播放或重启，不属于身份板级验收。

见[过滤状态](evidence/ubuntu/identity-dpu-check-20261018/board-readonly/result.json)和[四工件核验](evidence/ubuntu/identity-dpu-check-20261018/board-readonly/verification.json)。下一项先将CPU身份合入实际流式GUI、验登记/重返/UNKNOWN/删除，再以授权校准和独立评测数据推进INT8、编译及DPU混跑。以下原“无串口”记录按本条纠正，Windows回执未改。

### 身份 DPU 兼容性核查（2026-10-18，开始）

按当前讨论，先检查SFace图结构、现有Vitis AI3.0量化/编译工具和B4096目标兼容性。本轮新增核查工具/独立工件，不修改运行中的相机、GTK、语音、模型权重或FPGA配置。当前仍无板卡串口。Windows侧新增的流式播放/延迟优化较本轮身份候选更新，后续上板须回读新运行目录，不沿用旧启动路径或覆盖新语音源码。

本轮阶段结果：原SFace实际Inspector为30DPU/28CPU；第二版等价改写为139DPU/0CPU，四组与原OpenCV浮点对照和3项数值边界测试通过。原权重不变，未训练、未生产INT8模型、未完整xmodel编译、未上板。24份证据复制SHA通过，不含图像/向量/身份库/权重。详见[DPU身份模型兼容结果与下一步](DPU身份模型_兼容性结果与下一步_20261018.md)。下一阶段是代表性人脸校准及独立评测数据、量化编译和单DPU混跑；不把随机对照输入用作正式校准数据。

### 身份与界面：Ubuntu 开始实现（2026-10-18）

用户已指定先做身份与界面。本轮修改范围：`共享文件夹/aura` 的 `board/identity/`、`board/vision/ui_camera_service.py`、`board/interaction/ui_contract.py`、`tools/board_avatar_gtk.py`、身份配置及相关测试/文档。仅将基线一致的这些文件同步到 `语音共享文件/aura`，保留其较新的模型服务和起音修复。Windows 端请避开上述文件并在自己的回执记录并行改动；本条是文件任务声明，未通过消息工具发送。

当前未检测到 /dev/ttyUSB0 或 /dev/ttyUSB1；先做 Ubuntu 软件与真实 CPU 模型离线验证，上板状态另外记录。身份库在设备本地用户数据目录，测试使用隔离临时库，不将真实身份特征或用户照片作为共享工件。

本轮实现已完成，状态为“Ubuntu已验证 / 待板卡连接验收”。主仓220项和语音根224项完整回归通过；真实模型静态图13项、原生GTK身份流程10项、九种界面状态检查通过。12份改动文件已在两处目录核对一致，模型服务/起音修复三份较新语音文件保持差异并原样保留。候选17载荷SHA/长度通过，未包含身份库、用户特征、LLM或私钥。详见[实现与验收](身份与界面_实现与验收_20261018.md)。

首轮沙箱回环套接字权限错误及GTK截图Cairo失败均保留；分别通过获准的本机回环环境和已有X11截图工具完成验证。无新板测、在线部署、服务重启、机构或FPGA操作。Windows端接收后可复核新源码和报告，但不要直接用旧整包覆盖现场运行版本。

### 同步修复：UTC 2026-10-18 12:21—12:25

已在本机用相同内容补齐1260个缺失文件、8,269,204,111字节；每份实际源内容匹配对端数据块哈希，复制后SHA256核验通过，1260/1260已被微力索引接受。已有文件未覆盖，新代码与不同版本继续由微力接收。两项任务短暂停后均恢复原状态。

zhenghang链路连续三次零待同步/零错误、对端100%；之后新的小文件更新曾短暂排队/报错，UTC12:24:40已再次归零。小型任务探针已被zhenghang报告拥有当前索引版本。JoneNike开始接收新增镜像，仍有独立的大文件队列，不能写成所有设备都同步完成。

已准备Windows本地补齐脚本及1260项清单，供JoneNike本机复用原目录相同模型；Linux隔离验证通过：匹配内容可创建、已有用户文件保留、内容变化拒绝。尚未在Windows实际执行。详细结果见[同步修复报告](同步修复结果_20261018.md)。

- 收到 Windows 回执时间与设备名：待填写
- 当前板卡身份 / boot / 实际运行目录：待填写
- 实际 Windows IPv4 与板端路由、邻居、健康结果：待填写
- 板端 ASR 地址配置回执：待填写
- 新录音转写及实屏证据：待填写
- 取消 / 重录 / 自然结束 / 断连恢复：待填写
- 改动文件、实际命令、验证范围和遗留事项：待填写

### HDMI 载板版本只读补充（UTC 2026-10-22 02:50）

通过运行内核已注册的 `1-0051` / `at24` EEPROM 只读解析，过滤结果为 `XILINX / SCK-KV-G / 5066-01 / revision 2`；FRU 公共头及板卡区校验和通过，尾部结构解析未完全通过，故不据此确认 splitter 固件。未输出序列号/MAC，未扫描 I²C、写 EEPROM、访问 STDP4320 或写 GPIO。更新交付见 `语音共享文件/deliverables/2026-10-21_hdmi_hotplug_analysis/README.md` 与 `evidence/carrier-fru-readonly.json`。后续应按 Rev2 官方原理图确认 splitter host I²C/固件地址和是否有受支持的控制方式；当前实体 HDMI 重插及实屏最新结果仍未收到，本机未配置新改动。

### STDP4320 设计路径核对（UTC 2026-10-22 03:00）

从本机 B03 原理图参考抽取到设计值：host I²C `0x73`、HDMI OE/DDC/PWR 分别连 STDP4320 GPIO5/6/7、芯片SPI接 SST25VF020B。STDP4320 数据手册说明 OCM地址ID E6(8位)换算成7位为0x73，SPI固件ISP需GProbe/厂商程序；Xilinx当前carrier DTS没有splitter client，SOM DTS保留旧固件多地址冲突说明。认为物理重插主要恢复下游HDMI握手路径是当前最有依据解释，但仍属推断；没有现场I²C探测、寄存器读写、固件访问或GPIO写。下一步需拿到适配该载板/固件的只读身份寄存器定义或认可的GProbe程序，之后才设计单次GPIO/HPD事务。证据更新见交付 `evidence/splitter-path-analysis.json`。

### STDP4320 GProbe 查询（UTC 2026-10-22）

修正一次性脚本的 sysfs 符号链接解析后，只读确认 ttyUSB3 对应 FTDI interface 03。按预先限定仅发送一帧只读 `GetInformation index 0`，共4字节，等待1秒收到0字节，无重试。未发寄存器/GPIO/I²C/Flash命令。该结果不能证明芯片不存在、损坏或其他接口无响应；当前固件身份仍未知。证据在交付 `evidence/gprobe-getinfo-preflight.json`。

厂商资料表明 STDP4320 UART 属可选调试口，RD1 流程需 Kinetic GProbe 工具并复位后观察固件横幅；本次公开协议单帧无回复不具备故障定位效力。当前没有复位板卡。需先取得适配 KV260 Rev2/固件的厂商工具、线序和维护验证流程。

### 更正STDP UART并取得有效身份应答（UTC 2026-10-22 03:24）

以上接口03定位错误，B03第9页导线实际为FTDI CDBUS0/1经U65到STDP UART，即接口02；DDBUS0未接，DDBUS1为EEPROM写保护控制。正确口GetInformation index0和GetDeviceId index0..7共9条只读请求36字节，收到60字节/9条校验通过的响应。字符串PEGBB/ST/IROM/9f/9f9f/2/0/00不直接当作固件版本。未复位/DebugOn/RunCode/RAM/寄存器/Flash/I²C/GPIO写入；每命令/索引记录阻止重复执行。旧无回复证据标记wrong-interface/superseded，先要厂商工具/复位才能通信的结论失效。

只读新boot215c4292…首次1024×600/fbdev=N保持，On/RG16/49MHz后末次已DPMS Off，三服务PID/零重启及配置SHA保持。本boot实屏与独立供电对照仍未得到回执，未修好黑闪；继续需要HDMI状态/控制定义或现场单项对照。新证据 `evidence/gprobe-uart-c-readonly.json` 与 `evidence/current-uart-c-checkpoints.json`，未代填Windows回执。

后续证据放在本目录 `evidence/ubuntu/`。微力索引确认只证明对应版本可用；Windows 独立 SHA 校验和执行以其回执为准。

### 模型处理位置及大小只读盘点（UTC 2026-10-22 03:03）

用户要求查看各模型现在处理位置及大小。三次UART实读当前配置/文件stat/相机health，响应校验和控制台恢复均通过。实际SFace为Windows CPU/8792远程特征后端，YOLO为KV260 DPU、YuNet为板端CPU；相机1017约9.91Hz且无相机/检测错误。语音三模型保留Windows分工，但本轮8791/8792健康均超时，未宣称正在加载。

文件大小：YOLO2,127,303 B、YuNet345,478 B、SFace ONNX38,696,353 B；Paraformer243,371,218 B；OmniVoice主网和audio_tokenizer合计3,256,009,740 B；27B采用10-18保存的Ollama size13,885,180,476 B（未实读D盘）。SFace DPU候选10,796,371 B目前未选用。详见 `语音共享文件/deliverables/2026-10-21_model_inventory/README.md` 与 `evidence.json`，原始UART留Ubuntu私有。本轮无部署/服务重启/配置或硬件改动，Windows同步及实时驻留未确认。

### CPU/DPU占用监测与迁移分析（2026-10-21洛杉矶，UTC22日）

CPU两段约15秒为75.03%/82.63%（四核100%）；相机第一段39.89%、界面23.92%、Xorg3.89%、音频3.85%。实际DPU CU.3.auto驱动统计15个1秒窗口busy4～5%（加权4.07%）、149任务；该数为调度任务忙时，不能当DSP效率或FPGA逻辑资源率。临时stats_begin/stat监测已经stats_end关闭并确认计数停止；服务PID1017/1078 active/零重启，检测9.91Hz无错误。xdputil两次12秒超时后遗留的本轮两个孤儿查询，经准确PID/argv/ppid校验已清理，业务保持。

模型建议：YOLO保持DPU，SFace已有编译/历史固定图7.68ms及10Hz+2Hz短测，仍需代表性校准、真人精度和当前相机调度；现SFace在WindowsCPU，迁回主要减少远程依赖，不保证明显降低当前ARMCPU。YuNet43Conv等卷积可评估DPU部分卸载，但目标Inspector/量化编译尚未做；语音三模型保留Windows，Light-ASD暂不整网迁移，ByteTrack/UI等仍CPU。本轮没有改源码配置、部署、重启、切位流/显示、运动或恢复CPU优化。完整说明与过滤证据在 `语音共享文件/deliverables/2026-10-21_dpu_cpu_load/`；原始UART/源码片段留Ubuntu私有，Windows接收仍待其独立回执。

### 全部模型职责与计数纠正（2026-10-21洛杉矶，UTC22日）

用户要求完整解释所有模型。本轮实读活动audio-frontend源码/配置，发现之前漏列GTCRN gtcrn_simple.onnx、Silero VAD v5；二者配置WindowsCPU8795且enabled=true，健康查询超时，未发音频，权重大小未实读。GTCRN降噪供Silero判断speech，原始PCM仍送Paraformer。现按8项功能模型列YOLOX/YuNet/SFace/GTCRN/Silero/Paraformer/27B/OmniVoice，另列TTS内部tokenizer、待接Light-ASD/VLM及历史研究候选；不能称8项全部在线完成。

三次UART校验/回显恢复通过，新增 `语音共享文件/deliverables/2026-10-21_model_inventory/全模型概览_当前.md` 及过滤证据，原大小页/DPU表补漏项、历史10-18总表加当前入口。没有生产配置/代码/模型变更或新推理、录音/采脸/服务重启；不改Windows回执，Windows在线/同步与真人整机验收仍未确认。

### 用户新方向：板载CPU/DPU协同与比赛展示（2026-10-21洛杉矶，UTC22日）

用户希望尽可能利用板卡DPU与CPU，展示使用、利用率、提升和创新。已直接核对官方PDF22/23/25页与ZIP同源，近期主线调整为YOLO→SFace正式DPU身份→YuNet适配→三模型统一调度和CPU共享帧流水线→在正确率/时效约束下提高有效负载。旧全模型PL仲裁保留为软件调度稳定、资源时序核实后的扩展。

新增 `语音共享文件/deliverables/2026-10-21_model_inventory/板端CPU_DPU协同与竞赛展示实施方案.md`、历史实测基线CSV（15行）及实验矩阵CSV（6项，均not_run/结果空白），并写AMD_Smart有效优先级和日志。CPU/DPU百分比、静态资源、有效吞吐与准确率分别报告；历史75～83%/4～5%不当作新boot现测。SFace旧活相机预算触发、代表性校准/真人精度及YuNet目标编译是当前关卡。

本轮完成资料/源码核查和方案/数据模板，未改业务、切模型/位流、提频、推理/量化编译、重启、显示/运动或恢复此前暂停CPU优化。语音暂按原配置留Windows，双方先回收实际版本再集成，Windows独立接收以其回执为准。

### DPU适配首轮实施完成，常驻切换尚未放行（UTC2026-10-22 05:41后）

按用户“先把能放DPU上的开始、自己规划”执行：YuNet与新校准SFace已转换、目标编译并完成固定输入板测，SHA分别54d348bf… / 12b2ff5c…，体积576,254B / 10,796,375B。SFace256不同身份校准、独立公开1000配对FP32/INT8均98.8%；YuNet完整路径固定短测约2.02倍，SFace对板载FP32特征参考约38.41倍。三模型固定预编码10/5/2Hz、40/20/8次调用0周期超时，尚非实时业务长稳。

候选以实际板端源码为基线，保留现行脸部跟踪、照片策略和Windows SFace；18项软件回归通过。真实YuNet短测后延长观察出现MCP01 USB音频slot04/ep3告警和日志CPU负载，回退CPU后仍持续，根因未确定，整机CPU收益不作结论。已恢复原相机服务单元/配置，最终PID106407、检测持续、GUI29087/Xserver1077保持active/NRestarts0；当前YOLO=DPU、YuNet=ARM、SFace=WindowsCPU。CU统计已关闭，未改身份库/显示/运动/语音/位流，暂停CPU优化边界保留。

交付 `语音共享文件/deliverables/2026-10-21_dpu_vision_start/` 含README、release.json、两份xmodel、源代码、基线清单和过滤证据。公共图像/裁剪/特征数组、原始UART不共享。后续先排USB音频与稳定基线，再做三模型实时长稳、SFace版本隔离登记库与现场阈值。Windows须按实际基线集成，不能以旧共享主目录覆盖；其同步及独立回执未确认。

### 下一阶段只读定位（UTC2026-10-22 06:06后）

MCP01告警slot04/ep3已由USB接口/端点及xHCI上下文定位到播放端0x02/Isoc OUT。ALSA播放RUNNING、owner29254，录音closed；尚未证实持续播放本身是软件错误。最新800日志0.722394秒含433条同类告警，3.004秒总CPU91.55%，journald读取时deactivating/NRestarts15。原相机/GUI/Xserver三主单元active/零重启，检测9.89Hz/采集12.47Hz、无相机/检测错误，dpu_schedule为空。音频恢复和DPU实时常驻尚未实施，不能归因于模型或计为收益。

只读UART退出0/回显恢复；未录音/新播放、重开音频、服务重启、USB复位或生产配置变更。新计划/过滤证据/只读脚本在 `语音共享文件/deliverables/2026-10-21_dpu_live_baseline/`；下一项为实际音频播放流生命周期定位和正常恢复，再按YuNet→SFace→同条件竞赛对照推进。显示/运动/暂停CPU优化边界保留，Windows同步与独立回执待确认。

### 开始恢复与实时迁移（UTC2026-10-22 06:24～06:56，进行中）

用户明确开始并允许并行Codex。Ubuntu主任务独占UART/板卡，实际修改仅在独立相机运行目录和本轮交付；并行SFace/USB审查均使用独立候选，不改Windows源文件或回执，不并发生产操作。回收真实speech-motion/de989bf024a9界面源码后，在空闲状态正常停止/启动同版本一次，MCP01关闭/重开后短测0警告，配置/用户设置/免按键偏好SHA保持；UI主PID主动变为131932，相机106407/Xserver1077保持。原配置恢复后15秒CPU63.28%/XRT4.13%。

YuNet v3在独立相机根启用30分钟验证，异常自动回退；截止约24.7分钟YOLO9.95Hz/YuNet2.39Hz，0 USB告警、0 YuNet真正超限，1次20ms估计偏差/最大22.07ms、1次YOLO周期超时（不能写零超时）。同方法15秒CPU55.09%/XRT4.66%，非固定视频/非完整三模型收益，长稳尚未最终完成。

SFace独立版本库候选7源码/21项回归完成，最新纯配置检查在板上通过，model_store SHA310b4f32…；没有创建runner或DB，阈值null，正式业务仍WindowsCPU/旧库。后续影子计算候选正单独实现，未上板。USB机制审查与12项恢复模拟已完成，未接生产；声音实际出声、初始故障触发及根因未验。资料见 `语音共享文件/deliverables/2026-10-21_dpu_live_baseline/README.md`，最终以后续结论为准。

### 最终：YuNet DPU 30分钟通过并保留（UTC2026-10-22 07:02后）

任务PASSED_RETAINED：部署1811.48秒含目标1800秒观察、360个5秒快照，YOLO9.9538Hz/YuNet2.36998Hz、CPU整段53.929%，0 USB匹配告警/0日志读取overrun/0 YuNet真正超限或CPU回退。YuNet1次20ms初始估计偏差（最大22.0694ms），YOLO周期超时1次，不能称全链零超时。主检测健康快照帧龄中位106/P95=160/P99=184/最大191ms。

当前常驻YOLO+YuNet=DPU，SFace仍WindowsCPU/原库。最终相机134844、UI主131932/Xserver1077 active/零自动重启，6源码SHA/模型/manifest/原数据库路径/偏好保护通过；回退timer与XRT统计停止。后段15秒CPU52.99%/XRTbusy4.80%，原基线63.28%/4.13%、首段55.09%/4.66%均保留，实时画面与实际脸部频率不严格匹配，不作纯硬件归因。

SFace直接候选21项回归/最终板上纯配置检查通过、未定阈值null/不建库不切生产；影子候选独立实现和实际测试归档到本轮交付，不计当前已上DPU的生产模型。USB恢复接口12项模拟通过未部署。新只读网络检查eth0 carrier1/路由存在，Windows8792 TCP/health仍2秒超时，尚不知Windows主机/防火墙/监听具体原因；未发送音频、人脸或识别请求。后续可先做无FP32余弦依赖的本地DPU影子计算，同图对照须先确认8792可达。

冷启动、长期故障根因、现场身份/实际出声与SFace实时联动未验。原始UART/图像/音频/特征/身份库留私有；`语音共享文件/deliverables/2026-10-21_dpu_live_baseline/README.md`和release.json为统一入口，Windows同步/独立回执未确认。

### SFace真实人脸影子短测准备（UTC2026-10-22 07:13后，进行中）

用户回复“现在有人”，实板只读已取得face_count=1/有效单目标。影子候选最终16项回归通过，compare_cosine=false可在Windows请求前独立计算，不改原FP32身份语义；不会登记、落盘人脸或特征。6源码部署专用包SHA d6f06aa970649c9e076ccc916ca0c5c3257dcf79639082dd026fa7e90fed95bc已校验暂存至板staging/d6f06aa970649c9e，尚未切生产。准备复制已保留YuNet根并只加影子配置，设置受字节保护回退timer；必须实际DPU completed/accepted非零且主YOLO/脸部/音频健康才算通过，短测后先回退当前YuNet配置。Ubuntu主任务独占UART，部署准备agent只改独立脚本目录；Windows不要覆盖当前相机源/配置。最终状态以后续结果更新为准。

### SFace真人三模型DPU短测完成，已恢复双模型常驻（UTC2026-10-22 07:25后）

20秒真实相机影子观察通过：SFace请求17/完成10/通过目标时效复核10、延后7、失败0，特征调用平均14.478ms/最小12.090/最大19.487，YOLO10.039Hz/YuNet2.148Hz，0 MCP01告警。SFace不发布身份、不写库；compare_cosine=false/余弦样本0，未做现场识别准确率。原Windows特征配置/FP32身份语义保持，8792 TCP/health此前超时原因未确定。20秒CPU65.60%仅报告该窗口，不将不同长度/画面的测试前5秒69.13%作迁移收益；本次未测三模型XRT忙时。

自动恢复经独立审计通过：passed/complete/rollback_verified=true，回退timer停止；相机165277回到保留YuNet根，UI131932/Xserver1077保持，单元SHA84116d8f…与6源码/模型/manifest/原库路径匹配，影子关闭/CU统计关闭。当前YOLO＋YuNet在DPU常驻，SFace正式身份仍配置WindowsCPU；没有把短测写成SFace正式业务或三模型长期通过。直接候选21项/影子16项回归、部署准备3项本地检查均已记录。

本轮交付`语音共享文件/deliverables/2026-10-21_dpu_live_baseline/`补充真人报告、完整20快照、部署源码/源包、恢复审计和release.json，冻结子候选保留生成时未部署说明，最新实板状态以父级release/证据为准。没有把图片/人脸/音频/向量/身份库或原始UART放入共享。Windows不要覆盖当前板端较新源码；下一项独立INT8登记/现场阈值、较长三模型和同输入对照，Windows同步/独立回执仍待确认。

### 下一阶段统筹计划（2026-10-22，仅规划）

用户要求“接下来做什么，统筹规划一些”。已发布`AURA-CPU-DPU-ROADMAP-20261022-r1`到`语音共享文件/deliverables/2026-10-22_cpu_dpu_roadmap/`，含README/tasks.csv/plan.json。本轮声明只改规划、入口与Ubuntu回执，不改双方业务源码或Windows回执；未连接UART、部署、提频、重启或新采集人脸。

第一批T1/T2/W1并行准备：Ubuntu补SFace CALIBRATION_ONLY工具/独立INT8身份接入和阶段计时；Windows核对8792/8795网口、监听、本机health、实际启动入口及源码版本，回填自己的回执。本地标定/模型执行不要求先恢复Windows；同图FP32与整机语音依赖远端另验。并行Codex后续按需启用，生产/UART/DPU仍唯一主任务，本轮未新启agent。

后续T3三模型影子30分钟＋至少100次真实完成、T4分场次标定/现场独立库身份验收、T5测量支持的局部CPU优化、T6同输入调度和有效容量对照、T7发布与整机验收。标定/验证分开，阈值先冻结；初步多人检查需2已登记者＋1未登记者，小样本不称广泛准确率。约12.5Hz实采约束先定位，再探索更高检测频率；新增PL仅在同源资源/时序与软件证据齐备后评估。所有新工作包均未执行，不更新原release实测状态；Windows同步/接收仍未确认。

### 第一批执行开始（2026-10-22，进行中）

用户最新明确开始并行。Ubuntu主任务只修改独立T2/T3候选、共享实施记录与Ubuntu回执；独立Codex只在aura-sface-calibration-20261022开发T1，不操作板卡/共享生产。当前YuNet单元、6源码/模型/manifest/旧库路径复核通过，UI空闲，最新计数可选最大29.63ms/2次估计偏差/0真正超限，镜头前1脸。准备复用冻结影子源包做受保护30分钟长测，脚本6项本地检查通过，尚未称板验通过。新T1标定工具/阶段埋点另行验证，不混入本次冻结代码长测。Windows端保持原模型/接口并回填自己的版本/health，不能以旧共享主目录覆盖板端较新源码。结果写入2026-10-22_cpu_dpu_implementation交付，原实测包保持冻结。

### 第一批代码通过，三模型长测失败并恢复（UTC2026-10-22 08:15后）

独立T1 RAM标定工具9源码、46项软件回归通过；gallery与实际frontal_medoid_v1选择核心对齐，默认关闭，不登记/写库/发布身份，正式15秒采集/后验验证/阈值/持久化仍未板验。主任务将T2的3源码计时与T1合成11源码，46＋10项合并回归通过，另5项纯统计检查通过。标定8项及统计标准库合成检查已在板端Python实际通过；它们没有runner/相机/DB访问，不算新接线或真人板验。新源码未部署生产。

T3原冻结影子6源码长测，v1在修改服务前因Xserver单元路径假设错误安全失败，改用systemd FragmentPath后v2正式执行。计划1800秒，12个5秒健康快照最后55.03秒；下一次健康检查因SFace可选overrun失败，自动回退verified=true/timer停止，UI/Xserver当时保持。最后记录窗口YOLO9.944/YuNet2.182Hz、SFace20次完成/接受、均值16.637ms，实际有效0.364Hz低于拟议0.5Hz，不能称长稳或正式身份。v2没保存失败瞬间快照，超限的确切数值未知；v3已补快照及异常基线拒启，6检查通过未执行。

回退相机188288后YuNet又33.147ms超限转CPU，MCP01 slot4/ep3播放告警独立复读确认复发；15.46秒CPU93.73%/XRT4.32%样本属于影子已关闭且CPU回退的故障状态，不是三模型利用率。通过原空闲应用正常停止/启动一次，原配置/偏好SHA保持、停止PCM closed，恢复8.12秒0告警。UI主变191322，Xserver1077和相机188288在音频操作期间保持；随后只重启同原相机单元一次恢复YuNet DPU为192540。最终源/模型/manifest/unitSHA/原库路径审计通过，影子关闭、timerinactive/统计关闭。恢复15秒CPU55.62%/XRT5.00%/190命令，另15秒YOLO9.978Hz/实采12.439Hz、0新匹配告警/0YuNet真正超限，均短窗，不是新30分钟。

没有USB复位/切位流/运动/手工关开HDMI/新录音听音；原启动器同模式显示/唤醒按原行为。正式SFace仍配置WindowsCPU，旧库未迁移；Windows当前health/独立回执与同步未确认。本轮2026-10-22_cpu_dpu_implementation含源码/冻结候选/合并测试/数值证据/release，原始UART及真人媒体/向量/库不共享。用户继续授权后，主任务和独立agent转向低开销故障时观测，先定位复发/调度尾延迟，30ms不放宽，再验新接线与长测。Windows勿覆盖当前板端较新源码。

### 接续诊断与CPU小改动候选（UTC2026-10-22 08:51后）

原192540在SFace关闭/无新USB告警时YuNet35.9234ms硬上限超限转CPU，guard尚余约40.48ms，说明SFace和新USB告警并非每次超限的必要条件。agent冻结4诊断源码/29回归、离线过滤6检查，主任务控制器4检查通过；默认双env显式启用、同owner、原30ms/guard不动、最多8条数字fault，不长期读高密度日志。

120秒独立双模型诊断源包684f232b…、helper161ba854…，候选相机208402：295次真实成功wait、YOLO9.92438/YuNet2.44165Hz、整板CPU55.2604%，0fault/新增USB告警，120.06秒后自动回退verified=true、相机209792。正常VARTwall均值3.3232ms/最大24.3731ms，调度占用最大24.532ms、1次估计偏差/0真正超限；最近256分位与累计stage/启动数据分开。stage重叠不能加成CPU，未采XRT新忙时/正常threadCPU分布，不称纯硬件时延。

同4源码600秒延长helper1c22a77b…在原209792的15秒基线发现新USB告警后拒绝，没有切候选单元/实际600秒观察。实时slot4/ep3、journald重启增加，无法确认和相机切换/等待抖动的因果。只读Windows8791/8792/8795 TCP均约0.7秒超时，未发送人脸/音频/推理；远端具体原因未定。V4L2只读查询30/1参数、可见控制无曝光条目；不能据参数解释约12.5Hz实采，未改设备格式/controls或启动第二采集。

按空闲原音频关闭→同原相机单元重启→重建原音频恢复。原恢复脚本a0572918…错误保留了跨相机PID累计帧数比较，最后complete=false/AssertionError；原失败报告保留，未来修正脚本f4c6c574…未执行。独立只读验收按新PID计数差/后端/模型单元/配置偏好/告警检查通过，绝不将原脚本伪报通过。当前相机215707/UI215734/Xserver1077，原6源/模型/manifest/unitSHA/旧库路径保持，影子与埋点关闭、CU统计关闭/timersinactive。after8.094秒0告警；同新进程5秒YOLO约9.97Hz/无新匹配告警/0YuNet真超限。新顺序是否防复发、实际声音/冷启动/长期稳定未验。

只读分析给出SFace42供给×20/42准入＝20完成/55秒，说明低频不等于DPU容量上限；crop供给仍受同步Windows调用＋500ms间隔约束，1000ms worker周期也限拒绝尝试。650ms socket timeout不是总deadline，缺逐次HTTP时长，不能定量归因。后续解耦供给和有界重试先软件验证，原Windows语义与TTL保留。

另一个Codex单独实现CPU单copy候选，真实callback8项回归/两基线最小补丁应用通过，少一次921600B数组复制/帧为源码事实，像素/镜像/布局/metadata/内存生命周期保持；未上板、未测CPU/DDR收益。诊断冻结4源未被优化改动污染。

共享2026-10-22_dpu_audio_diagnosis归档4源、29＋6检查、控制器4检查、120秒完整数据、600秒预检拒绝、原恢复验收错误与独立证明、只读分析及单copy候选。63工件/28份Python AST/18份JSON/8个本地链接校验通过。原始UART、真实脸/声音/特征/库未共享，Windows同步/接收未确认。现场身份所需人员/标签未获本轮确认，标定工具和正式身份均未自动启用。

### 单终端接续验证（UTC2026-10-22 10:10后）

用户最新要求只一个终端后仅主任务串行，无新agent；此前并行产物按独立目录接收。音频实际transcription.py补回收到私有actual-source，6份依赖SHA齐备。引擎草稿首轮15项暴露重复请求/close后stream两处问题，已修复并补32个ID有界台账、旧事务/改内容拒绝、异步NULL/失败/限次、晚到预热和poll异常请求NULL/保持失败态，最终20项通过。源001898f4…，本板真实Gst1.18.5合成fakesink管线NULL→WARMING→READY_UNVERIFIED→close、重复请求、参考代次及全释放通过；无ALSA/MCP01/真实声音/DB或新DPU，不称完整音频恢复接线。上层owner屏障、IPC回执和AEC仍待补，未导入生产。

合并13源：producer/标定、正常wall与线程CPU、单copy，56＋45回归通过；42820B源包0dd98eee…完整暂存后，板端Py3.9.9导入13模块、原Windows配置/默认关/合成计时检查通过，禁止XIR/VART导入和DB连接，实际DPU作业0。源码没有常驻；正式SFace后端与原库仍Windows配置。共享布局同两组及音频20项已复跑通过，不重复计为额外新测试。

另仅以原UI单copy候选d74e3025…运行60.183秒真实UVC，helper3a73b43d…、观察YOLO9.9363Hz/实采12.4786Hz/0新增匹配USB告警，passed/complete/rollback_verified均true、timer停止。完成后按预案恢复原84116d8f…单元与6源/模型/manifest/旧库/配置偏好；新相机264975，UI215734/Xserver1077保持。独立审计/后续内核尾检查通过，最后保留USB告警约4991秒以前/不是725条新告警，journald仍28次未增加。未启影子/计时统计，原30ms与guard保持。

单copy候选未保留为生产常驻，本短测不等同长期或同输入整板收益。局部11.9%/21.1%仍限定此前两线程条件微基准；没有新XRT忙时数值或正式身份精度。交付2026-10-22_single_terminal_integration包含音频引擎/测试、producer/timing冻结源、13源合并、真实UVC与虚拟Gst/导入数值、机器状态、回读审计和SHA。Windows源码/回执未改，当前接收与远端健康未验；原始UART、真实人脸/音频/向量/身份库不共享。

UTC10:13最终交接：再次核验264975仍DPU_YUNET_INT8/真超限0、原源模型/单元/库一致、影子与统计关闭、回退timer全部inactive；追加final-handoff-audit.json。最终94工件SHA/60 Python AST/18 JSON/5本地引用通过。共享运行入口重现56＋45项和音频20项均通过，重复只是布局复现不加测试数量；仅主任务运行，没有新并行Codex。Windows接收/微力同步仍待其独立回执。
