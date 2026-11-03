# 转轴联合平台与实况接口接入

UTC2026-10-20 07:01起，用户确认按DS3230/J2.3/独立供电共地接入、摄像头随轴旋转；未确认机械零点或首次定位空间。沿用前一轮ZIP及现行方案/FPGA资料阅读，重新检查AMD_Smart规则、共享入口/回执、最新相机与GUI实测。无子代理，未修改Windows回执。

当前boot3e1add36-b917-4289-91dc-699348528782、内核5.15.36-xilinx-v2022.2、CID匹配。最初相机为enrollment-photos/6f1aa1842d53，GUI为long-conversation/9a5bcf476bf8，官方位流。当前基准设备树SHA501cf86e…与封存98c959df…虽字节布局不同，213节点、1420属性、保留内存及版本/boot CPU全部相同，无忽略项；已有联合DTBO在当前基树合并通过。8个联合payload和4个runtime哈希匹配，原驱动/固件不改。

执行固定boot/路径/源码/固件门槛的有限no-PWM事务：新增跟随扩展，备份unit/VART，安排180秒独立回退，停止相机确认ZOCL无使用者，再复用已审计load.py，核对ID/ABI/build和STOP；原相机关闭期间预检当前YOLO与CPU身份模型，再用wrapper恢复原相机，采10秒实况、运行shadow、最终检查。无BIND/REFERENCE/ARM/COMMIT/PWM。

axis-01/02在旧相机实际跑通联合固件、模型和实况，但部署检查错误地要求VART不变，自动恢复官方固件/原入口。axis-02逐项证据明确仅vart_unchanged=false：xmutil切换联合平台本就会改VART配置。修正为核对准确的已校验联合xclbin路径，保留源250ms期限、边缘/换人/超时停止及输出关闭门槛。01实况150次READY/98帧，shadow因SOURCE_EXPIRED接受0；02实况152次/99帧，shadow因HORIZONTAL_BORDER接受0。不能称为实体跟随通过。

axis-03在部署之前相机HTTP连接拒绝，无该次生产变更；重新盘点确认现场切换到了handsfree-dialogue/candidate-0c0a8ab46ec2新版，相机和GUI都迁移，约9.6Hz/identity=true。相机源码SHA仍8aa94461…，不复用旧unit覆盖新版。重新读取实际版本后，axis-04在新版目录完成接入，7项最终检查通过，GUI PID104694保持，14份原身份/相机/GUI源码配置SHA保持。

最终当前：相机PID106060，两个服务active；aura-visual-servo-b4096-v1.bit.bin operating，VART指向联合xclbin；VSRV ID0x56535256/ABI1/build0x14da0e60，最终flags0/lease0/ack0、未解锁。YOLOX固定图4人/空图0人、B4096 fingerprint0x101000056010407和CPU身份模型加载预检通过。不代表身份准确率已验收。

axis-04十秒采143次/96个不同真实源帧，READY23/NO_TARGET118/EXPIRED2；shadow因横向边缘停止，软件接受0，未实转。源年龄39/125/255ms(min/median/max)，前一源到下一新源接收最大325ms；需处理目标居中和尾部时延，不放宽250ms时效来凑通过。独立最终复读相机9.46Hz、帧龄118ms、identity=true、无相机/检测错误、真实motion路由READY；GUI当时免按键PROCESSING/已完成两轮，是状态快照，不是本轮语音效果验收。

最终只新增6文件到最新版相机，其原motion初始化/驱动已存在且匹配；unit只切可选wrapper，同相机/模型/配置。未修改身份原源码、GUI或HDMI/语音参数，未配置开机ARM/跟随；冷启动未验证。早期旧候选上的同名新增文件保留但已不活动，未删除用户数据。

准备有限首次定位脚本，默认只打印计划；确认后可先1500µs定位，再1504/1496/1500，每段0.5秒、100ms硬件租约、ACK/最终STOP。没有执行该脚本，也没有把1500复位/测试点当机械零点。语法、默认模式、不确认拒绝、非板端执行拒绝检查通过，硬件路径未测。初次1500定位可能明显转动，下一步须用户现场确认线材/空间与观察，之后核对转向、机械参考，再做有限实况跟随。

交付[本轮结果与证据](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_pan_axis_integration/README.md)，过滤四次事务/真实坐标、设备树审核结果、自有脚本及核验清单。原始UART/FDT/实际相机源码/图像/身份库留私有，Windows独立接收待其回执。本轮未改第一版控制源码，不重复将其历史324项回归/板端35测试当新测。

## 用户授权后的首次定位测试（UTC08:12—08:13）

用户在已说明首次中位可能明显转动及现场观察条件后明确“那现在就试一下”，据此执行此前具体准备的1500/1504/1496/1500µs、约2秒有限测试一次，不再重复索取授权。预检boot、联合固件/VART及相机保持，GUI已是avatar-performance/8049378caf0e、PID132404，未拿旧GUI覆盖。

执行冻结脚本5590字节/SHA919a5901…，boot/FDT、CID、8程序/4固件、活动APP、独占Native传输/ID/ABI/build校验后，使用台架BIND/REFERENCE/ARM及100ms租约COMMIT。各阶段0.5秒，46条命令ACK全部匹配，脉宽阶段读回通过，最后事件1979.79ms；脚本含guard加载3.643秒。finally STOP和关闭传输后再独立打开读回，flags0/lease0/active=false/armed=false，ACK46、width1500，确认输出许可关闭。未把该1500测试点当已标定机械零点。

前后相机106060/GUI132404 active、PID不变；相机30758→30805帧、约9.92Hz/身份ready/无相机检测错误。无服务重启、切位流、录放音、身份/GUI/HDMI/语音配置变更；无自动跟随、自动重复或扩幅。授权为本次有限台架测试，不能因此宣称摄像头实体闭环通过。

已通过问题工具询问用户本轮有没有转动/轻微动作、卡滞/抖动/异响及转向；现场反馈暂未收到，机械响应和外部PWM测量仍未验证，不把硬件ACK当舵机实转证据。结果保持输出关闭，下一步按反馈核对中位/方向或信号/供电，并处理此前跟随尾部时延和边缘目标问题。

板端事务 `/home/root/aura-pan-follow-20261020/first-pulse-01` exclusive-create防重复执行；UART执行与只读导出均校验成功，控制台回显恢复。过滤工件/实际执行脚本与证据写[首次定位交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_pan_first_pulse/README.md)，原始UART不共享，Windows回执未改。

首次定位交付13份冻结工件长度/SHA复核通过；46个连续ACK及每次active/reason/session/epoch/目标回读、最终独立flags/lease检查通过，回读脚本SHA与上一轮一致。共享入口、Ubuntu回执和资料导航已更新，以新测试时间覆盖较早“未发PWM”状态；现场反馈仍待到。

## 用户确认转动与停止复核（UTC08:20）

用户对本次测试反馈“转动了”，记录为USER_FIELD_REPORT的机械响应确认。仅原话确认转动，未确认方向、镜头朝正前方、卡滞、抖动或异响；这些值保留未知，未建立PhysicalReference或认定无异常。已通过问题工具询问镜头是否朝正前方、转动有无上述异常，暂待答复。

使用精确boot/common SHA、程序/固件、活动联合APP/firmware及Native独占门槛复核寄存器，flags0/lease0/active=false/armed=false、ACK46/width1500；输出许可保持关闭，无新ARM/COMMIT或脉冲，Native关闭按协议STOP。相机PID106060约9.92Hz，身份ready、帧龄135ms、无相机/检测错误；无重启、切位流或业务源码/配置变更。

现场原话JSON、补记README及过滤停止检查写首次测试交付的field-observation子目录，独立长度/SHA清单；原13份冻结测试工件不改写历史“待反馈”状态。共享入口/Ubuntu回执/导航更新，Windows回执不改，原始UART不共享。下一步结合当前朝向和异常反馈确认参考与方向，持续跟随还需处理源时效和边缘目标，不由“转动了”直接升级为完整跟随通过。

## 1500µs偏右反馈与1504µs有限校准（UTC08:26）

用户回答停下后镜头“偏右”，仅确认1500µs不是当前正前方，异常/方向仍未知。继续用户授权的转轴调试，在此前实际测试过的1496～1504µs范围内保持1504µs约2秒后STOP，用于比较方向，不把旧极性或脉宽增大自动认定为向左。

基于前次有限台架脚本，仅改变测试点/标签并加严格前态门槛：同boot/FDT、CID、程序/固件/联合APP、Native锁/ID/ABI/build，初态flags0/lease0/ACK46、width/reference/target1500。新脚本SHA2706fac7…，语法、默认计划、仅1504/2秒/100ms、确认/非板端拒绝和finally STOP检查通过。板端事务midpoint-step-01独占创建，实际46条连续ACK和每段脉宽回读通过，最后事件1993.23ms，含guard加载3.443秒。独立关闭后重读flags0/lease0/active=false/armed=false、width/reference/target1504、ACK46，当前输出许可关闭，无自动跟随或连续寻中。

相机106060和GUI141059前后active/PID不变；现场GUI已更新handsfree/resume-049c88498ae0，未拿前次avatar-performance目录回灌。相机38712→38758帧，约9.92Hz/身份ready/无错误；无业务源码配置修改、重启服务、切位流、录放音或HDMI/语音变更。

已询问1504相比1500是否更靠正前方、更右或几乎无变化，待现场反馈；机械中位、左右极性及卡滞/抖动/异响仍不能虚称已确认。现场原话、新测试源/计划、保护检查、实际ACK/STOP及过滤串口证据写[本步交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_pan_midpoint_step01/README.md)，原冻结证据保持，Windows回执不改。

本步17份工件长度/SHA及README链接核验通过；此前首次测试13份、现场补记5份、联合接入28份冻结工件复核保持一致。1504保持后的姿态反馈尚待到达，输出许可关闭。

## 1504几乎无变化反馈与1520µs有限校准（UTC08:36）

用户反馈“几乎没有变化”，记录为1500→1504试步尚无明确可见差异，不推定死区/方向或无异常。重读同boot/联合平台/程序固件/Native门槛，flags0/lease0/ACK46、width/reference/target1504，相机9.92Hz/身份ready/无错误。复核历史10月8日1500→1520台架和逆时针用户反馈，仅作测试点依据，不当本次轴载安装的有效方向标定。

派生第二步测试源SHAf3e019c4…，起点测试reference1504、目标1520，硬件每20ms最大4µs斜坡、总约2秒，100ms租约；精确boot/FDT、CID、程序/固件、APP、Native锁/ID/ABI/build、初态ACK46/width/reference/target1504/flags0/lease0守卫保持。新epoch2区分前一步，未建立PhysicalReference。主机默认/起终点/2秒/100ms、无确认和非板端拒绝、finally STOP源检查通过。

首次stage后的wrapper在读取GUI状态时因非IDLE退出，动作前失败；随后只读导出证实midpoint-step-02目录不存在，无BIND/ARM/COMMIT。本台架测试不重启或拥有相机/语音，将继承的不相关UI空闲要求改为记录实际状态，新增身份不得ENROLLING/SAMPLING的保护，硬件/lease/STOP门槛不变；复核未执行后重新运行，实际动作只有一次。成功执行时GUI已IDLE/STOPPED、身份UNKNOWN，不把本轮写成真实播放与运动并发通过。

46条连续ACK及各阶段1520脉宽回读通过，最后事件1983.58ms、含guard加载3.558秒。finally STOP、关闭后独立打开读回flags0/lease0/active=false/armed=false，width/target1520、reference1504、epoch2、ACK46，输出关闭。相机106060、GUI141059前后active/PID不变，检测44541→44587、约9.92Hz/身份ready/无相机检测错误；无业务源配置修改、重启服务、切位流、录放音或HDMI/语音变更。

已要求观察有输出的2秒内是否向哪边移动，并询问输出关闭后是否回原位；现场答复尚待到达，不将无明显变化直接归因于死区/故障，也不自动再扩幅。用户原话、新测试源/计划/主机保护、预检退出及未执行复核、实际ACK/STOP证据写[本步交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_pan_midpoint_step02/README.md)。原冻结工件保留，Windows回执未改，原始UART不共享。

本步22份工件长度/SHA和README链接复核通过，前步17份/首次13份/现场补记5份/联合接入28份冻结工件保持一致。阶段遥测采到width1504、1512、1520，支持本次寄存器斜坡已前进；不替代外部波形或机械观察。方向、居中和停止后回位反馈仍待到，保持输出关闭。

## 增脉宽更右反馈与1500/1490反向校准（UTC08:42）

用户说“更偏右了”，记录为1520相对前点在用户描述视角下加重右偏。未把该方位等同机器人坐标/顺逆时针或镜像控制polarity，因此原跟随配置未改。复核同boot/联合平台/Native状态为flags0/lease0/width1520/reference1504/epoch2/ACK46，相机9.93Hz/身份ready/无错误。

本次从1520已到达测试点初始化，经硬件斜坡保持1500和1490各2秒，共4秒，新epoch3。新源SHAa1cb5d97…，初态精确epoch2/ACK46/width1520/reference1504/target1520守卫，boot/FDT/CID/程序固件/APP/Native锁及ID/ABI/build、100ms租约、阶段端点、finally STOP和身份非采样守卫保持。主机语法、默认计划/两段/4秒、无确认和非板端拒绝及源检查通过。midpoint-step-03独占执行一次，91条连续ACK及八段0.5秒端点读回通过，最后事件3968.01ms，含guard加载5.515秒。关闭后独立读回flags0/lease0/active=false/armed=false、width/target1490/reference1520、epoch3、ACK91，输出关闭。

相机106060/GUI141059前后active/PID保持，检测48005→48073、约9.93Hz/身份ready/无错误，GUI IDLE/STOPPED、身份UNKNOWN，无服务重启/切位流/业务源配置/HDMI/语音变更。已询问最后1490位置仍偏右/正前方/偏左。

随后收到“重新测试，人嗯他反向转动”，作为当前校准任务的重测要求和部分现场反馈，不替换原目标。已问“反向”指1490向左减少右偏，还是人移动与镜头方向相反，并说明当前是固定位置测试，自动跟随尚未启用；解释待到前不额外发脉冲，也不把反向一词当参考/图像控制符号已校准。本步结果/原话/保护/ACK/STOP/过滤串口证据写[交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_pan_midpoint_step03/README.md)。原冻结证据保持，Windows回执不改。

本步18份冻结工件长度/SHA及README链接通过；08:44再次只读复核flags0/lease0/width1490/epoch3/ACK91，相机9.93Hz/身份ready/无错误，没有额外ARM/COMMIT。该次停止复核3份过滤工件另存retest-stop-check并独立核验，不修改已冻结18份原件。重测要求的具体含义仍待答复。

## 小幅看不清后的放大固定往返（UTC08:51）

用户补充“转动有点小，没看清”，作为既有重测要求的进一步约束，不能据此认定旧“反向”含义或机械方向清楚。以1460～1540µs有限范围执行一次1540/1460/1490各约2秒、共6秒固定往返；说明站着不动观察方向，并留意固定指令会到位停稳还是持续转动。未改镜像跟随polarity、未建立PhysicalReference或启用跟人。

预检同boot/联合平台/程序固件/Native守卫，初态flags0/lease0/width1490/reference1520/target1490、epoch3、ACK91。新源SHAc058b361…，初始化参考1490、新epoch4、100ms租约、每1秒端点、finally STOP和独立关闭后复核保持；每1秒端点给最大80µs硬件斜坡预留时间，不是实测机械角速度。主机语法、默认计划、范围/三段/6秒、缺确认/非板端拒绝等通过，随后visible-direction-01独占执行一次，137条连续ACK和六个端点通过，最后事件5961.43ms，含guard加载7.901秒。最终flags0/lease0/active=false/armed=false、width/reference/target1490、epoch4、ACK137，输出关闭。

相机106060/GUI141059前后active/PID不变，检测53546→53639、约9.93Hz/身份ready/无错误；GUI IDLE/STOPPED、身份UNKNOWN，无业务源码配置/服务/位流/HDMI/语音变更。已询问本轮前两段方向、固定指令下停稳还是持续转，答复暂未到；模式、机械中位、外部波形和完整跟随仍未验收，不仅凭寄存器认定真实角度。

过滤原话/计划/保护检查/实际源及ACK/STOP/串口校验保存[本轮交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_pan_visible_direction/README.md)，此前冻结原件保持，Windows回执未改，原始UART/图像/身份库不共享。

本轮17份工件长度/SHA和README链接复核通过，上一轮18份冻结原件保持。固定脉宽下的停稳/持续转动和实际方向反馈仍待用户确认，输出许可关闭。

## 1420～1580放大往返及1470/1450修正（UTC09:03～09:10）

用户要求“动作再大一点”，沿用硬件限速，在已测1400～1600范围内完成1580/1420/1490各3秒，总9秒一次台架往返，208条连续ACK和三个端点通过，最后事件8996.9ms；最终独立读回flags0/lease0/width/reference/target1490、epoch5、ACK208。未改自动跟随范围或polarity。准备阶段不输出，开始提示后短启动器单次执行。

首次启动在GUI HTTP8783拒绝连接处失败，动作事务未创建，随后只读确认不存在、没有动作；将GUI状态读取改为尽力记录，保持身份非采样/相机健康及硬件/租约/STOP守卫，再准备后仅一次真实执行。大幅往返期间相机106060正常约9.93Hz，GUI161498前后activating，不记录GUI健康。本任务没有诊断其启动根因或修改/重启服务，不能归因于运动测试。

用户随后“看清了，现在还有点向右偏转，再转一下”，记录为动作可见、1490仍右偏。以既有增脉宽加重右偏反馈为试步依据，从1490到1470保持2秒，新epoch6，46条ACK/端点通过、最后事件1993.32ms；独立终态flags0/lease0/width1470/reference1490/target1470/ACK46。用户再答“还是朝右”，继续1470到1450保持2秒，新epoch7，46条ACK/端点和独立STOP通过，当前flags0/lease0/width1450/reference1470/target1450/ACK46，输出关闭。1450是否向中间改善仍待现场回答，不将ACK、暂用reference或KNOWN状态当机械/身份准确率验收。

1470和1450两轮相机106060/GUI162389均前后active/PID保持，约9.93Hz/identity_recognition=true/无相机检测错误，GUI已IDLE/STOPPED，身份字段先UNKNOWN后KNOWN。本任务没有重启GUI，其恢复不归因于本任务。生成脚本语法、默认无硬件、有限目标/2秒/100ms、缺确认/非板端拒绝检查通过，实际源与回传SHA一致；保护沿用精确boot/FDT/CID/联合APP/程序固件/Native锁/ID/ABI/build及精确前态、新epoch、硬件斜坡和finally STOP。1470准备初次使用短脚本传输器在主机因长度超限退出，未连接板卡，改用既有分片工具只准备不动作成功。

三份新交付分别保存现场原话、计划/保护检查、自有准备/执行/导出脚本和过滤ACK/STOP/服务证据；原冻结历史证据及Windows回执不改，未共享UART原始流、图像、身份库，无生产源码/服务/位流/HDMI/语音配置变更。共享入口、Ubuntu回执和导航已更新，仍未建立PhysicalReference、确定到位停稳模式/图像极性或启用自动跟随。

最终1450试步最后事件1967.85ms；新交付大幅往返33份、1470试步20份、1450试步20份冻结文件长度/SHA及28处README链接通过。此前可见往返17份、反向18份、1520试步22份、1504试步17份、首次13份、联合接入28份冻结原件逐项复核保持一致。当前等待1450实际姿态反馈，未追加动作。

## 1450仍稍右后的1430µs有限修正（UTC09:18）

用户补充“还有点偏右”，记录为1450试步后的现场反馈。继续现有定位调试，按硬件斜坡由1450临时参考保持1430µs约2秒，新epoch8，46条连续ACK和阶段脉宽端点通过；finally STOP与关闭后独立读回flags0/lease0/active=false/armed=false、width/target1430/reference1450/epoch8/ACK46，输出关闭。1430是否居中尚待现场回答，未建立PhysicalReference或开启自动跟随。

新源SHA34801a6c…，精确初态epoch7/ACK46/width1450/reference1470/target1450/flags0/lease0，boot/FDT/CID/联合APP/程序固件SHA、Native独占及ID/ABI/build、100ms租约、硬件限速和STOP门槛保持。主机语法、默认无硬件、1430/2秒/100ms、缺确认及非板端拒绝检查通过。准备阶段只传送校验，发出开始提示后短启动器单次执行，没有重试动作。

相机106060和当前GUI165304前后active/PID不变，相机69915→69961帧、约9.93Hz、identity_recognition=true、无相机/检测错误；GUI IDLE/STOPPED、身份字段UNKNOWN。GUI较前轮PID发生变化属于两轮之间的现场状态，本轮没有重启或改动它；无生产源码/服务/固件/HDMI/语音配置变更。过滤证据、新测试源及现场原话另存第六次试步交付，共享入口/Ubuntu回执/导航同步更新，Windows回执及历史冻结证据保持。

最后ACK事件1969.25ms，回传实际源SHA与主机一致；本轮20份冻结文件长度/SHA和9处README链接通过，前次1450/1470各20份及大幅往返33份冻结工件复核保持。输出维持关闭，1430物理姿态待现场确认。
