# HDMI 重训候选与原生长尾观测

**显示分支暂停：** 用户明确回报“未拔查，仍花屏”，本次软件重训未恢复实屏，状态已由PENDING改为FAILED。其后只读检查显示已进入原600秒DPMS Off；做一次独立普通唤醒Off→On，原计时设置未改，不把此步骤并入此前重训效果。用户随后说“拔查能恢复，那就先不解决这个问题，其他问题呢”，明确要求暂停显示排查。未再执行重训、模式切换、固件/GPIO/I²C操作或新的冷启动；不推定本boot已经实际再次插拔。后续优先转轴可用性、YuNet长尾与严格性能/业务验收，保持单终端。

**本次冷启接续：** 用户已上电并确认“仍然花屏”，未要求HDMI重插。被动UART观察Linux启动，确认已进入Linux后才接通shell，无bootloader输入。新boot c5f247b9-76b9-40a3-85ca-96578055eb5c，camera1309/GUI1310/X1077 active/NRestarts0；初次查询GUI尚未就绪ConnectionRefused失败保留，未重启绕过。137秒检查原生ABI2/owner未fence、YuNet395完成/SFace3、worker/ready均true，显示connected/enabled/On；前89d53检查点e6eb4b0d…与归档对象精确相等、归档SHA通过，旧历史不被新零值覆盖。用户花屏状态执行冻结474b控制器一次：train_loop1/encoder开关0、trigger_return/VBLANK通过、正常卸载/维护退出，自身trace移除，相机1363→1387新增24帧、PID1309保持，新primary/optional超限0。258秒后检查2238帧/9.83Hz、worker/SFace ready、身份配置与库SHA保持、筛选内核错误0。**用户尚未回报软件后的实体画面，视觉验收PENDING；没有写开机项或重复触发。** 整个过程含接口捕获/VBLANK查询，不能唯一归因于最后train调用。转轴仍FAULT。共享源码/数值证据更新，不含KO/ELF/原始UART/人脸内容。

**用户返回与本次真实冷启：** 两小时数值窗口现已完整取回：7200.054秒/3539查询失败0，YOLO71660新增帧/9.9527Hz，YuNet27119准入/27116完成/3未提交，新primary/optional超限、native失败、gap和fallback0，CPU整板51.31%。SFace新增0，不能称三模型满负载；包含已记页面/显示干预，不算严格收益。诊断单元退出、原三服务PID保持且NRestarts0的结束快照已核对。用户返回后DPMS唤醒实屏正常，再明确同意物理冷启。控制器3610d09e12307044正常停止GUI/相机，核对持久检查点、源进程消失及owner锁释放，safe_to_disconnect_power/poweroff_scheduled均true、failure=null；checkpoint SHA e6eb4b0d2f1ccb7a2e7d05f22f43a5e1fe6e43fb33e5daafec665921365ee0a6。用户随后确认已断电，正在等待接通电源；被动串口未接到Power down标记，不虚报该标记。接线保持，花屏先留现场；新boot/PID、历史归档、业务恢复及软件修复的实屏验收均待验证。关机前manual_pan=FAULT/automatic_following=false也未完成，不报全项目完成。以下“100.7分钟仍运行”为已保留的历史时点。

按用户仅一个终端及离开两小时授权继续，root串行，无新代理。[源码、数值证据和下一步](</home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-24_hdmi_link_training/README.md>)。

**后续更新：** 已完成一次真实软件重训调用，不再是仅诊断。预览A1/main60→B/vision180→A2/main60正常通过并恢复main：CPU51.20→63.01→51.43%，YOLO9.9607/9.9390/9.9335，视觉预览12.52Hz/玩偶约8Hz，新故障gap0，此为页面负载对照非代码优化收益。随后普通DPMS唤醒后，用474b8ce39ba29123新控制器显式单次触发；trace train_loop1次/encoder enable-disable0，action_returned1/error0、VBLANK返回、模块已卸载。相机44348→44372新增24帧/PID1291/worker保持，新primary/optional故障0/模式不变/无新相关内核错误。**无人观察实体屏，内部void返回非训练成功证明，花屏修复仍未验。** 新增5个冒烟结果拒绝边界后45离线测试通过。两后台观察窗包含页面和显示唤醒/重训干预，不能标为固定负载无干预长稳。以下“未执行”为该步前状态。

**采集器关联修正：** health故障计数与上一native报告不原子，v1可能将旧正常报告与新计数关联。仅停止诊断单元84fb…，1776.502秒/0新fault/自身trace清理通过，生产PID1291未变。v2 06f77083a55985a2继承原一小时截止，141.228秒交接空档计数新增0；不伪称无缝跟踪。增加最多500ms重读和ABI/task/时间顺序/新区间/故障标志验证，无匹配明确记录缺证，不分析旧正常报告。6专项使总数51；新正常2.288203ms对齐通过。两小时c248轻量器原exact_fault_report_available仅标志启发式，不能作严格新故障关联，部署冻结源码和此限制保留。最新3020.724秒YOLO9.9516/YuNet11339新完成/1未提交/0新故障gap、SF新0，非三模型持续负载；两个计时观察仍进行。

**收尾实测：** v2已在原截止DURATION_COMPLETE，本段1682.739秒/0新故障，自身trace清理通过；读到aura trace实例0、uprobes空、显示模块已卸载、train_loop/IRQ/getresources目标kprobe均0。相机1291/GUI1407/X1403 active、NRestarts0，worker和SFace ready；最后DPMS Off为原600s休眠，未改设置。两小时轻量窗口4913.573秒YOLO9.9520、YuNet18452新完成/2未提交、新primary/optional故障gap/fallback0、SF新增准入/完成0，继续自动采集至7200s，尚未称完整两小时通过。

另有15.057秒主页点测CPU50.45%、相机组21.17%/GUI23.69%/X3.54%（均整板口径），DPU任务busy5%、207条真实驱动任务/SF新完成0；复用原脚本，前后空闲证明通过/统计已关/timer inactive，无新增模型/合成输入。非配对点测，不主张优化倍数。当前三个xmodel实际文件2,127,303/576,254/10,796,375字节（YOLOX-Nano/YuNet/SFace），健康均DPU后端，SFace合同128维；已更新共享模型分工表。未重复整权重SHA，不偷换成参数量/RSS/LUT数。

采集器“500ms重读”的准确口径为500ms重试窗口，单次health保留3s I/O超时，因此不是500ms墙钟硬上限；未在生产运行期修改冻结源码。真实花屏恢复、旧原生4fault4rec的唯一根因、严格同输入收益/实回退仍未验收。用户返回先保留HDMI连接及现场，再按RETURN_TEST.md核验，不能以此次驱动返回代替实体观察。

最终取回快照为轻量窗口6043.402秒/约100.7分钟：YOLO9.9525Hz、YuNet22730新完成/2未提交、SF新准入/完成0、新primary/optional故障gap/fallback0。两小时任务尚在运行并将自动落盘，未提前标满时通过。交付包47项SHA清单、14份Python AST、23份JSON/相对链接与候选源码指纹核对通过，51软件检查日志已归档；未包括权重/ELF/原始UART或现场人脸资料。

用户外USB供电仍花屏；物理HDMI晚插/重插恢复。已取得同boot25b3…坏→拔插→好，159.274秒1542缓存点、29/29过滤trace：EDID均0、扫描/时钟/PID不变，538.861014s重训入口来自DP IRQ；只能证明调用，非内部成功或唯一因果。真实冷启延迟首次Linux scanout至60.21秒，仍花屏；自己的单次Xserver覆盖已移除且无服务重启。不要再重复60秒延迟或把它当修复。

当前boot89d53e38…、camera1291/GUI1407/X1403。自研临时内核候选v2仅复用运行驱动train_loop，默认动作关闭，显式单次触发、解绑失效、活动输出检查及模式/IRQ序列化。源码ce7e1a51…/KO2e5bd549…，与实际1856启用配置匹配，交叉编译/符号核对及实际诊断加载/接口捕获/卸载通过；3次参数/动作关闭拒绝通过、成功触发0，无新模型故障/PID改变。40离线控制器/观察器/解析测试过，不冒充真实重训或解绑并发通过。首次DPMS睡眠阻断、驱动名打开失败、无IRQ捕获超时、错误编译器路径均保留，已定位/修正，未用旧产物追认通过。

控制器默认preflight已实板执行，未加载/触发；当时显示又600秒休眠。只做过一次xset force on供诊断，休眠配置未改。未安装候选启动项、未重启模型、未改PL/Flash/未知splitter寄存器。需要用户回来观察花屏状态后测一次候选，再决定持久化，不能把“已拔插恢复”记为软件修好。

两小时纯数字health/CPU观察器c248c0a96ffebb65已启动；早期1066.331秒YOLO9.9556Hz/YuNet4031完成/0新故障gap与fallback，SFace新0，不属于三模型持续负载。CPU50.85%为非配对当前负载，不能与旧63–64%计算收益。原生上一启动4fault4rec历史保留。

短C ABI probe识别YuNet1335/runner2，与原生报告时间对应；3.64秒后探针全清，未识别SFace，不猜。初版短窗帧率端点不一致，原值排除，代码修正。启动一小时仅目标TID的sched_switch/wakeup跟踪84fb117db99251b9，有独立清理守护、最多2故障dump/3600秒停止，无常驻uprobes、无nice/亲和性修改。正常2.105451ms窗口覆盖完整，其中RUNNING0.538451、RUNNABLE0.008、BLOCKED1.559ms；释放bookkeeping0.00177ms，等待本身正常，不是故障根因。暂无新超限，需等后续故障记录或完整结束。

所有trace/UART原始材料、KO/ELF和原用户照片不进入共享目录。观察器只保存数字/恢复状态，无现场图像、向量、姓名或录音。正式INT8模型/阈值/身份库及唯一DPU owner保持，Windows回执未修改。下一步读取两个观察器结果并核对清理，再测真实花屏候选；长尾根因、冷启、严格收益及实际旧码回退仍未完成。
