# 人脸持续随动、身份恢复与平滑控制

跨日继续2026-10-24-PAN-BOARD-TRIAL.md任务。用户离开睡觉，明确授权先完成未完成项，再加人脸移动速度反馈和中值滤波。保持其他终端/Windows业务，未触碰身份库或代填Windows回执；不将合成探针或软件回放写作真人验收。

## 已完成的身份可用性恢复（UTC06:26～06:32）

旧SFace/YuNet分别3/7次超限、预算耗尽锁定。开发独立native_operator_v1：新增显式API，仅允许safe completed budget latch、旧两轮均自然过600秒、当前primary连续健康30秒且实际推进200次、无active/pending/fence，才转10秒cooldown；三次实际新鲜probe/ACK后才READY。原故障、恢复、尝试累计与旧时间戳保留；原30ms cap/5ms guard不变。对C optional执行仅本线程FIFO10，finally恢复原调度。

本地20组旧策略、5组C ABI、8组新守卫及ASAN/UBSAN、7项Python RT/ABI兼容迁移检查通过。旧库源与schedule-integration指纹核对相符。板端仅link+ABI阶段无context/模型/作业，camera66241同PID、0新超限。

正常stop66241并核验精确boot/PID/birth、quiescent checkpoint、无pending/active/fence及ZOCL0；原样恢复seed后启153151。显式兼容迁移先按旧unit验证seed，再记录新unit；未篡改checkpoint。新库SHA704f561a…、unit7cf7eaee…，24z own camera dropin。新启动primary18→19新增1已保留，不隐藏或归因FIFO；之后31次原生守卫拒绝等待至稳定窗口，才接受请求。

SFace3个合成零输入健康作业实际约7.6～7.8ms，同输出SHA c6a6ff10…，三次ACK后恢复；没有匹配姓名/登记/发布业务身份。YuNet由当前自然图像探测恢复。最终identity.ready=true/error空，两个可选RUNNING；原faults仍3/7，SFace attempts/recoveries3/3、YuNet7/7，原窗口自然老化后当前1轮。旧断电跨boot4→1断档仍保留，不称已补齐。真人身份效果需用户回来后确认。

回退须先正常stop并核验fresh新checkpoint，再用native_entry_rollback.py显式兼容新unit回旧库；不能直接删除新dropin后用旧unit启动。过滤证据IDENTITY_OPERATOR_VERIFICATION.json和相关源码已共享，无原图/身份内容。

## 持续跟随基础版（UTC06:45～06:56）

continuous_v1实现常驻监测、每次运动≤10秒、1425..1505µs/24..40µs/s/120µs/s²/单源≤4µs。区内不ARM/PWM；越线重新确认ARM后只接ARM之后真实新源；回区正常finish/STOP；丢脸/断流STOP后仅重新确认新帧，硬件/协议fault锁住。重复包不续lease，250ms源期限及20ms提交余量保持。左线按脸框触实际画面左端2px解释，右线仍用户脸中心80.647%线；左触边实物效果未验收。

14项session/所有权/只读receipt检查通过，包含多轮越界-回区、丢脸重确认、体框拒绝、重复源、限幅不反复ARM、断流与硬件故障。新GUI仅主窗口内增加开始/停止工具栏，无独立TOPLEVEL；257pins和旧已停止报告继承验证通过。GUI-only restart后camera153151不变，方向恢复+1；原手动点动1425..1445范围不扩展。超范围读回只经显式前代consumer pins/report SHA/精确epoch-session-ack-width验证，不授予新写权限。

25秒控制墙钟试验实际子进程运行23.409秒，105样本均NO_TARGET、元数据视频均可见，0个运动段/0ARM/0COMMIT，输出保持1476µs、epoch11/ack16、flags0/lease0，停止后manual READY。相机同PID、identity.ready，主/可选超限新增0。该证据证明无人监测/启停，不证明新持续版真人物理跟随。

## 正在处理的实际画布问题（UTC06:53～07:08）

截图发现实际左画布仍是占位文字，尽管native sink计数与frame_visible正常；三个屏幕像素一致，直接相机JPEG是正常房间画面，故未把metadata通过当实际画面通过。完整取回实际AAE786… GTK源，确认旧placeholder逻辑已修正、无STAGE ERROR，问题在原生绘制/GTK屏幕层仍需验证。

按GTK3 X11原生窗口绘制/GstVideoOverlay官方接口准备gui-continuous-v2：native canvas关闭GTK双缓冲/设为app-paintable，在绘制后idle阶段显式expose，重画前检查同一输出和真实源年龄<250ms，过期/clear/卸载输出不重画；增加实际widget mapped/placeholder/double-buffer诊断。专项当前/过期/clear/卸载/未映射检查通过。只改own GUI proxy、camera/固件/运动不改；正在GUI-only restart后实际像素核验。此刻不能写已修复，也尚未进入速度反馈/中值开发。

参考原件：[GTK3绘制模型](https://docs.gtk.org/gtk3/drawing-model.html)、[GstVideoOverlay expose](https://gstreamer.freedesktop.org/documentation/video/gstvideooverlay.html)。这些说明绘制机制，不代替本项目像素实测。

## 最终完成（UTC07:15～08:36汇总）

原生画布修复通过实际像素检查：12/12 X11屏幕区域匹配直接相机JPEG，12帧不同；最终冷启动复核最低相关0.99645、最大均值绝对差5.517/255。native canvas visible/mapped=true、placeholder=false、double_buffered=false，400×300；相机和原始帧保持640×480，橙线位置未改。这是软件屏幕像素验证，物理HDMI扫描未测。

在身份/基础持续监测及实际画布完成后，加入三点中值、80ms位置平滑、100ms速度平滑和实际新图像速度反馈，基础24、反馈后8..60us/s、最大120us/s²/4us每新源，行程仍1425..1505。向外快移加速、向内回区减速、原始测量回区立即停；没有预测旧源/体框/头部yaw。跨ARM仅继承已确认的感知历史，不继承源时间、执行速度或命令，旧帧不可输出/续lease。

最终continuous-v2r2 manifest SHA251ec5808b2b028ec09835561df817523d6c8969562c74e4160fe9ba29375027。17项算法/会话在Ubuntu及板端PS通过，板端仅合成帧/FakeDevice、0实际执行器访问。板端纯数学回放：同一最终位置静止请求25.45us/s、向外移动33.60；向内14.40；单帧毛刺未中值60、有中值24。该比较不称实物速度/平滑度通过。

发现旧manual1425..1445使1476us停点左右按钮均受限。独立USER_BOUNDED_MANUAL_VSRV2范围按已授权跟随窗口对齐1425..1505，仍5/20us单次、≤2秒、点击新鲜度与独占owner不变。旧20us人眼证明在原范围核验；新范围physical_range_verified/external_waveform_verified/mechanical_reference_calibrated均false，不伪称80us机械标定。4项授权范围/旧证明继承/漂移拒绝通过，板端load_release/verify_platform无MMIO写入预检通过。一次脚本超过UART3800字符门槛在发送前拒绝，改传文件并SHA固定调用后成功，无服务/输出影响。GUI-only重新加载后manual READY/1425..1505；camera153151保持。

最终60秒墙钟、控制子进程58.637秒无人实流，179/179预览可见，均NO_TARGET、0运动段/0ARM/0COMMIT，主/可选新增超限0。停止后manual READY，1476us/epoch11/ack16、flags0/lease0保持；新手动范围可恢复调节。GUI supervisor265320、editor238044、camera153151，identity.ready/error空，SFace/YuNet RUNNING、故障累计仍3/7，primary累计19。257/257组件pins通过、renderer/editor无错误；后续2秒新USB缓冲错误与读日志overrun均0，未清日志。

新GUI代理cb973b5a…、editor e2d4477d…；源与精确依赖、指纹及过滤证据写入共享2026-10-24_pan_follow_shadow/。39份本轮源/工件有FINAL_SOURCE_SHA256，主报告FACE_FOLLOW_20261025.md，完整数据FINAL_VERIFICATION.json。未改Windows业务主目录、模型/身份库或他人回执；Windows是否接收同步不代填。

结束输出关闭、视觉页显示，用户回来可直接点“开始人脸跟随”。新版真实姓名/双向边界/机械平滑度、机械零点限位与角度/外部波形、冷启动组合仍需返场验收。没有用无人测试或合成回放替代人眼确认。现役unit7cf7…但保存的旧checkpoint是66241已消费前代；下一次正常stop导出新unit，回退仍须显式兼容迁移。


## 用户返场后的持续跟随故障修复（UTC 13:05～，进行中）

用户反馈转动一下就停止，明确授权两个终端并行，且确认仍在镜头前。主终端独占UART/执行器，第二终端只读分析与独立候选开发，未访问板卡。前面的“最终完成/用户未返场”均是历史时点，不能代表本轮实际效果。

continuous-v3 已将软件范围由1425..1505扩至固件现有1400..1600，不称机械限位标定；回区后保持同一PWM目标，丢脸仍关闭输出。v8实板25.252s内71ACK/12段、57目标变化/14保持，最后COMMAND_PERMISSION_OR_CONTEXT锁停；真实动作和中断均保留，不能称平滑通过。v6较慢LK已撤下；v7本机P95 55.44ms未达30ms目标，不能追认该性能门槛通过。

第二终端核实原相机本来就在YOLO前投递，撤回“仅YOLO后拿到帧”的猜测。v9修复实际扩展层offer先后与锁后选帧：同一真实capture对象/fid/stamp先投Flow，原检测调用一次且入参原样，等待检测快照锁后再取最新捕获。23/23本机软件检查通过，250ms源期限、500ms真脸锚边界、固定模板阈值及脸专用key保持。既有Flow通知和stream revision机制本来已正确，无重复v10补丁。

正常stop camera613778，fresh checkpoint SHA136345c8…、同boot/确切PID-birth/quiescent/pending0/ZOCL0通过后切换v9，camera628468，GUI265320始终未重启。现役native unit7cf7…及旧故障预算保持；启动primary22→23新增1，SFace/YuNet旧3/7保留。当前源manifest875f5c4f…；旧r4源码/模型/身份库未改。

continuous-v4 实板34.635s/23ACK后COMMAND_HARDWARE_REJECTED。v4r1补齐preSTOP证据及MAX序号拒绝；实板69.309s内16ACK（6目标变化、10区内保持）后再停，实际拒绝flags32/reason2/lease0/旧ACK16、context和target1526保持。与RTL核对：expiry先清权限(reason4)，随后的COMMIT可覆盖reason为2；此前仅保存STOP后flags0无法判断原因。该故障被实测定位，不是实体平滑验收。

continuous-v4r2（manifest613c48ab…）只对精确已知到期路径恢复监测：原submit内部live preflight，旧成功ACK/context/target一致、合法单次提交与shadow读回完全匹配、post flags32/lease0、且已到上次成功源的最早过期时刻，才先STOP确认再等待新帧重新确认。不得把拒绝算成功，不重放，不放宽TTL；未知/硬件/上下文/序号耗尽故障仍fatal。直接reason4入口同样核对精确context并排除MAX。26/26本机软件回归及编译通过；已只切运动child/配置，主GUI与相机未重启。现正在用户在场的180秒监督测试，实际结果待下条记录。


UTC13:25～13:40更新：v4r2约180秒真人窗口43ACK/13段、到达软件1600端点，flags0/lease0由独立诊断定时器停止。用户确认“有持续转动”，随后明确“仍有明显顿挫”，因此平滑验收未通过，不能把永久退出修复当作整体完成。一次持久模式恢复脚本因诊断timer已自动collect返回systemctl exit5而停止；未切服务、未写执行器、未改变状态，不是新的hardware fault。原较长审计脚本4001字符在UART3800门槛发送前拒绝，同样无板端影响。

深挖发现真正热路径：C vsrv_read每word做4个系统文件platform检查，原status12word=48次open/read/close。新独立mmio_batch_v1新增read-only read_many，整批前后platform与MMIOidentity检查、ACK围栏最多3次、失败不改调用方输出；原open/read/write/close函数体与协议头逐字一致。18组fake FS/MMIO及18组ASAN/UBSAN、交叉编译AArch64通过，无生产访问。新lib SHA93e17fdf…，consumer v5 manifest e3f0cb1c…；29项Python检查通过。原validated_context仍验证前代driver/lib/固件，consumer额外pin新lib；NativeRegisters既有初始化hash/boot/flock约束不变，仅status/identity读分组，写仍逐次全平台保护。

板端同owner、同寄存器、STOP状态、0ARM/0COMMIT三对只读对照：旧status [2.306,2.377,7.768]ms，新batch [0.781,0.637,0.580]ms，中位2.377→0.637ms。仅3对有限观察，不宣称长尾/P95或实体平滑通过。相机628468/GUI265320未重启，identity READY，primary累计24（比先前23新增1，未清预算），可选旧3/7。初始20秒106/106 UNCONFIRMED、0输出；私有当前JPEG确无可见人脸，未将图片/身份内容放共享。用户同意重新进入画面测试；当前常驻跟随已开启，无新180秒诊断timer，250ms源期限/20ms余量/单运动段10秒/1400..1600仍保持。新版真人平滑正在验证。


## 用户追加“边界突然大幅转动、起步抽搐”后的PS重构（UTC14:06，进行中）

用户给出共享《转轴平滑调研》报告，并要求继续。已立即停止v5，最终flags0/lease0/1469µs、manual READY，v5累计366.925s/354ACK/22段，仍多次SOURCE_EXPIRED/LEASE，已知expiry→COMMIT竞态窄恢复实测flags32/preflight15/lease1/原ACK31/shadow一致，未再fatal；不能称抽搐修复。已核对报告基于v2r2，当前v5正常回区本已保持PWM/历史，不复述旧版本正常回区每次重建为当前事实。

continuous_v6采用独立感知和20ms轨迹循环：OneEuro替换中值+固定位置低通（作者原公式/实source dt），大跳且高瞬时速度需下一张真实图证实；边界外按距离连续速度、回归时预减速，不变更用户80.647%右线/左框触2px语义，不加入隐藏空间滞回。已确认脸先保持当前width，区内无角度目标变化，边界微动不重复ARM；初始ARM后仍必须新帧。正常回区立即freeze当前硬件width，保PWM和同脸历史；lost/expired/invalid仍STOP重确认。

Ruckig仅使用官方开源一轴Velocity接口，pin commit99751e6e…、MIT许可随包；独立C ABI继续传上一命令p/v/a、速度40us/s/加速度80us/s²/jerk400us/s³。20ms ticks不是新图像，只在同一真实source的原250ms截止内输出，20ms余量不改；每个新图批准的总位移仍≤4us，旧/重复包不能延长deadline。源位移预算、回区freeze及故障STOP是jerk例外，不宣称所有瞬间机械jerk连续。接近行程提前制动并锁住同向继续，反向可恢复；tick迟于100ms停机不补偿大跳。

软件14项session检查通过：边界噪声、5外1内10轮单ARM/不finish、同源tick不延时/不扩位移、跳变、回区冻结、迟tick、真实故障、旧preARM时戳不能绕过wrongboot/body/lost/protocol等。OneEuro10项、轨迹10项host检查通过；裸OneEuro单帧坏框反例保留，不称单一滤波足够。交叉库最初静态版引入GLIBC2.34已撤下；最终compat SHA d08abd38…仅要求GLIBC2.17/GLIBCXX3.4.19/CXXABI1.3.9。板端300步纯数学C ABI起步/反向/停稳47.269ms，0MMIO/0ARM/0COMMIT，不能称实体通过。

新consumer v6 manifest cb38da3d…已传14文件、继承v5批量读库，仍验证原平台/固件/driver及新增库pins。仅切控制child与own配置，camera628468/GUI265320未重启；60秒独立停止timer保护首轮，实际真人效果等待当前测试结果。


UTC14:11用户在场v6结果：59.438s/262ACK/59次ARM，命令width1469..1481，记录的有效delta最大1us，无fatal，最终1478us/flags0/lease0。用户说“转动幅度太大，没有跟着人走，莫名其妙，延迟高”，又确认“突然大转和抽搐明显减轻”。这不是通过反馈：只能记录抽搐相对减轻，跟随方向/幅度/延迟仍未解决。大量SOURCE_EXPIRED/LEASE导致初始区内保持也反复ARM/PWM吸合，v6初始区内自动保持这一实现正在撤回；正常已启动后回区保持仍保留。

主进程v7限制一次持续越界纠偏累计±6us，跨丢帧/重新确认不扩该预算，必须真实回区或改为反侧才重新开始；速度降至16us/s、取消正向脸速加速，保留回区预减速；区内初始不ARM/PWM，避免失效恢复时无谓吸合。本轮属于小幅方向/响应诊断模式，不能称完整长距离跟随。15项本机session检查通过，已传候选，未试转。第二终端正核对输入同key锚点多余NCC计算及miss快照竞态，仍不放宽250ms/500ms边界、不跟身体。当前执行器已停止，等待候选源完成后正常checkpoint切换一次。


UTC14:20新输入v10：第二终端复现原v9晚公布miss导致的2个无谓UNCONFIRMED反例。候选30/30本机回归通过：仅当已匹配图像fid与stamp均不早于新miss源且continuity key正确才发布；250ms当前源、500ms真锚、原stamp不变；同binding/anchor/detector key完全相同且旧真锚有效时跳过只影响同一dict选择的额外NCC，真实当前像素匹配不省略。manifest e69fa7f4…。正常stop camera628468，fresh精确checkpoint SHAa281912e…/pending0/ZOCL0验证后承接同boot新camera702556，GUI265320保持。相机服务已READY、运动输出0；没有删除旧预算/重登记身份/切PL。

小幅consumer v7已激活，manifest7586ebe5…、15项本机软件检查通过；复用V6两已pin库，板端复制前后SHA一致不重新编译，独立source路径未覆盖旧版。起步区内无ARM/PWM；6us累计预算跨丢帧持久，主动回区/换侧才开始新一轮，无正向脸速加速。当前60秒有界真人诊断窗口开启，仍待方向/延迟和实体效果反馈，不能把candidate测试称完整随人行走功能已完成。


UTC14:23～14:33：v7/v10窗口58.515s/108ACK/21段、仅4个目标变化、width1478..1482，delta最大1us。用户明确“方向大致对，但慢半拍、转过头、速度过快；人在边界没识别”，不改已知方向。前18秒38ACK全固定1478且9次ARM，对该前段物理大幅动作不能解释为软件目标大步变化；反复PWM启停/机械吸合及脉冲截断仍需核对，不能当已测电气根因。已停输出，flags0/lease0/1482。

输入v11修复实锚裁剪的几何矛盾：真实脸仍有55.56%宽可见时，全核心模板部分在画外，原full NCC无法表达正确位置。新版本保留整块匹配优先，仅在左右画边对固定原锚两个互不重叠子块做NCC位移一致回退（每块≥.80、std≥8/最小10px、一致≤1.5px）；不滚动reseed、不降55%/60%/最小48px、不改250ms/500ms。35/35本机检查通过，包括左右已知平移、单块缺失/不一致/背景/过多遮挡拒绝。manifest3d84f9b8…；正常stop702556、fresh checkpoint112ff47f…/确切boot/PID-birth/quiescent/pending0/ZOCL0后承接camera712588，GUI265320保持。

PS continuous_v8r1，manifest217ccf96…，21项session/driver检查通过。每次持续越界累计3us、max10us/s、低起步floor2us/s（解决x=0裁剪脸框比例误差过小导致等一秒以上的数学问题），原方向/边界不改。初始target等于当前width时仅ARM不COMMIT，不为边界假起步反复送相同PWM；已有效转动后回区保持仍保留。视觉失效在精确健康context下使用已有PL QUIESCE完成当前≤1.6ms脉冲，不再无谓截断；PL自然期限仍优先，不开始新脉冲。未知协议/硬件故障保留即刻STOP；finish途中精确同context/ACK/target的自然到期先由原driver STOP确认，再作为已停返回，其他异常仍抛出。源250ms/20ms余量/每图4us/20ms tick与所有权不变。相机/GUI没有随PS版本再重启。

该版本是幅度/方向/边缘响应的小步诊断模式，长距离连续跟随尚未验收，不将3us预算模式冒充完整跟随。当前60秒测试窗口已开启，实体效果等待当前用户反馈。旧v6/v7所有失败与用户反馈已留档，未以纯数学/命令步长替代实体认可。


## 用户同意左线内收后的实际画面验证（UTC14:41）

用户在异步选项后回复“可以”，明确同意左起动线内收实际画面10%并显示。continuous-v9仅扩展已有settings left_camera_ratio=.1映射；legacy left_ratio0/widget域right_ratio/右线位置保持。23项本机session/driver/映射检查通过。consumer manifest cc189b44…；只替换own控制release/配置，停止状态没有ARM/COMMIT。

zone-editor-v5从v4独立复制，新增5px绿线中心x132/y112/高300、input passthrough，面板初始隐藏，只随vision页面显示；右线拖动/保存保留left_camera_ratio及原未知字段。7项stubGTK/math/实际保存软件检查通过。源SHA c35b328e…；只重启独立editor，camera712588/GUI265320保持，editor724980。先备份原settings，再原子设left_camera_ratio=.1，新editor保存后右线仍widget0.7158253629442671/实际相机0.8064720153808593/屏幕414.5888；左线实际相机0.1/屏幕132。

X11实际绿线像素55纵向样本54绿色，通过；没有把metadata通过当可见通过，也没有导出图像。动作写0。实体长距离跟随/过冲/反应仍未验收，当前3us每持续越界的小幅诊断限制未解除。已开启60秒新左线真人测试，等待本轮结果与用户反馈。必要源码/过滤证据LEFT_LINE_ACTUAL_VERIFICATION.json已共享，未写他人回执。


UTC14:51用户要求核对另一个Codex终端的全部工作。已只读识别其平滑调研与全项目审计，核对用户可见交付及当前v9/v11代码，不读取/采用其他会话隐藏推理，不改其工作文件或服务。新增共享“2026-10-25_两终端转轴对齐/README.md”和过滤证据：说明研究基于v2r2而当前已接OneEuro/Ruckig/同脸历史、源授权有限轨迹；当前3us是诊断限制，不是完整随人行走。原图像速度正反馈已因用户过冲反馈关闭，不能宣传仍完整实现该增益。

最近重测实际178.786s/142ACK/40目标变化/102保持/31会话，width1441..1474、最终1448、fatalfalse；17次完整脉冲视觉停。测试已结束，manual READY、flags0/lease0，没有新的自然跟随验收确认。多人/跨天身份、物理波形/轴角、连续长距离跟随均未由该窗口证明。两终端对齐只读文档，不新增运动/服务操作。


## 实验室停电：离线封存与来电恢复交接

记录时间UTC 2026-10-25T15:20:51.066608+00:00。用户报告板卡及实验室断电；未连接串口、未发送STOP或运动命令、未重启板端服务或改板端配置。不能称已取得这次断电的正常关闭checkpoint；板端文件系统/数据库影响待来电检查。旧boot463c…/camera712588/GUI265320/editor724980均改记历史，不作当前在线事实。

本机复核continuous_v10_candidate 33项测试通过（本次运行0.231s）、Python编译通过。最终同输入回放按当前源码SHA重新生成SAME_INPUT_REPLAY_FINAL.json：六轮20帧越界+1帧回区，v9累计18us，候选3us；这不是实体结果。候选要求稳定回区250ms且至少3张不同新图才放行下一纠偏，回区立即停保持；严格匹配的v11短暂EXPIRED刷新不产生新授权，只能保留原批准图像的原截止，真实源过期/错上下文/丢脸/多人/硬件fault仍停。未上板，也没有声称原3us诊断模式已成为完整持续跟随。

已新增共享《2026-10-25_停电交接_转轴与来电恢复》：README、STATUS、55文件源码快照及SOURCE_SHA256、最小ZIP与独立SHA。ZIP 238191 bytes，SHA256 261a1e85ea650bcffeef4f299faca0b081050cbeee94051b5a1e253ff50a3d5e，55项SHA核对和ZIP testzip通过。初次本机归档因旧报告外层trial字段读取错误中止，修正层级后完成；影响仅本机打包，0板端操作。未复制人脸/录音/身份库正文/大模型权重/虚拟环境，Windows同步接收未代填。

来电按新启动核验：先板卡/USB与视频，转轴动力保持断开；核对boot/FDT/联合固件/VART/服务与原故障历史，再无动力STOP及新参考位置确认，最后小步试转。旧702556 checkpoint112ff47f…已用于随后启动712588，不能冒充此次断电正常停机或直接复用给新boot。不能只改旧boot字段、重放旧命令或清预算恢复。完整实体跟随、物理角度/波形和冷启动组合仍未验收。


## 停电离线接续：v10r1修正与独立复验

记录UTC 2026-10-26T01:51:14.924684+00:00。用户要求继续，整轮没有连接UART、相机、HTTP业务服务或MMIO，未重启服务/试转/部署。旧v9/v11/editor-v5仅作断电前最后版本。原停电ZIP及旧v10候选保留，新增独立continuous_v10r1_candidate。

深查并修正旧v10遗漏：此前有限轨迹只钳制source+250ms，未将真实检测锚+500ms传给驱动。r1对实际源要求精确anchor provenance，截止取两者更早，并扣既有20ms提交余量；错/过期/被同源改写的anchor均拒绝。EXPIRED刷新只能保留原有限授权，不能扩展任一截止；没有ARM后新图则不输出。未确认/大跳输入也不再积累稳定回区确认。

新增可复现时序：合法新图到达时旧硬件lease仅剩约10ms，原会话等下一20ms tick再提交，导致本可避免的丢ARM。r1仅在已输出、精确新图通过全部验证且旧lease≤40ms时，立即用新图原截止提交相同角度；不增加角度位移。重复/失效/旧源不得续交，短anchor截止同样钳制。

48项本机session/driver/边界/期限回归及Python编译通过。13组成对合成回放：左右六轮单帧回区v9累计18us、r1 3us；四轮稳定回区均12us、ARM4→1；anchor仅剩50ms时v9合成许可越过锚界120ms，r1为0；真丢脸/多人/冻结/错boot/身体仍停/拒绝。真实Ruckig主机库＋FakeDevice，不是实板或机械实验；仍3us/轮、10us/s小幅诊断模式，未称完整随动通过。

新增只读来电检查脚本read_only_resume_after_outage.py：采新boot/FDT/固件/VART/服务及STOP元数据，不启运动/改配置；x86主机拒绝执行检查通过，目标板尚未运行。新共享包“2026-10-25_转轴停电离线修复_r1”30个文件SHA通过，ZIP 235584 bytes，SHA dab01dae44aa71084b3044bc40a99a07d2abb8c8ae0ba95223857bcb414cd353；独立临时目录解压后重新跑48测试/13组回放及完整性验证通过。Windows同步接收、冷启动、板端依赖与实体随动均待来电核验。其他终端指南估分/提交材料未改。

## 来电恢复、真实影子r2与用户中位更正后暂停

UTC2026-10-26T02:00～02:34接续。用户明确板卡和转轴都上电；首次只读核验新boot16a07283-9e14-45e6-816d-3bda4cf333a7，原启动是官方DPU固件，旧boot GUI manual FAULT/自动关闭。正常停止新camera1322，fresh checkpoint SHAad33a40bf60451c2834133143e1b04b9bf7104716cf09ae3192f5efd7e2ca5f8的确切PID/birth/同boot/quiescent/pending0/ZOCL0通过，正常停GUI后恢复配套联合VSRV/2固件；FDT新基底fcecf9…/overlay2ec4fc…合并b18b9d…通过。ID/STOP flags0/lease0，未在该阶段ARM/COMMIT；复位寄存器1500不称机械零点。原生unit7cf7eae…未换，当前boot计数承接；旧boot primary26/可选3、7保持历史，新boot初始primary1、后续2，不能以断电清零宣称长尾修好。

业务恢复camera13537/GUI监督13573/editor14694；258个GUI源码pins通过，SFace/YuNet RUNNING、identity ready、可选超限0，仅表示服务可用，不代表真人身份准确率验收。X11十二次采样均匹配当前相机、十二个不同画面，左绿线55/55样本通过；用户选择的左画面10%/右80.647%及不同脸框/脸中心语义保留。

首次r1真实人脸虚拟执行器影子因INVALID_FACE_ANCHOR退出，物理ARM/COMMIT均0。r2将发布时有效但到达时正常超过500ms的锚归为SOURCE_EXPIRED可恢复路径，未来时戳/类型/因果异常仍拒绝；没有放宽250ms图像、500ms锚及20ms余量。r2影子manifest51265395999f650b9e00465a5a56f7000d447113c0ff6d53de66db33cefd63ec。10.054s/283包/281READY/8虚拟提交/3目标变化；30.048s/849包/750READY/29虚拟提交/12目标变化，均无fatal、无MMIO/实体驱动/实体ARM/COMMIT。30秒仍82个UNCONFIRMED、17个EXPIRED，输入连续性仍未闭环。r2只传影子目录，自动实体consumer尚未启用，仍3us/次、10us/s诊断约束。

用户确认“在”能观察后，按已有20us授权执行本次新启动有限初始化1448→1445，再往返1445→1465→1445；往返43ACK、最终1445/flags0/lease0。用户起初说约100度，已先追加ID/STOP且不试转，未清计数或篡改证据。用户随后明确“初始化没问题”“100度是转到了原来的中间位置，中位校准位置”；因此撤回“20us增量产生100度异常”的错误解释，不继续将初始化当作已证实故障。软件脉宽不是实体角度，首次上电重新定位不能用相对步长保证总机械幅度；前面称全部过程“小幅”不严谨，已向用户说明。

用户确认当前到中间后，单独从当前已停命令做一次相对20us往返，不重复初始化；42ACK/epoch3/ack42、1445→1465→1445，最后flags0/lease0。trial SHAeb7ec28fbc083be7a312d10b6d26d736c96fe992106ada0821fe94f8d1e3f341。用户确认“看到了小幅度来回，已经停住”，同时要求“等一下”并明确“1420是中位”。因此实体动作暂停，当前最后指令1445us，不自动回1420；1420作为用户报告的中位记录，不能把1445或复位1500称本次机械中位。

板端仅追加观察与暂停元数据，未为记录再次开MMIO/试转；state阶段USER_PAUSED_OUTPUT_STOPPED_20US_OBSERVED_CENTER_1420，新增center-reference.json和relative-20us-human-observation.json。GUI仍旧boot保护FAULT，自动关闭；未只改boot字段绕过、未伪造新方向或完整随动验收。用户“等一下”约束后续动作，不能自行继续运动。当前暂停不同于断电停机，板卡服务仍运行。

共享“2026-10-25_来电恢复与转轴验证_r2”：README、13份过滤报告及用户更正、42文件源码快照与指纹；共享副本独立49项回归/13组成对合成回放、7项影子执行器检查通过。无原图/录音/身份库内容/模型权重/UART原文，未代填Windows回执，其他终端指南估分文件未改。串口传输中断导致一次未完成shell引号，仅确认PS2后取消该不完整输入并恢复echo；已传10文件逐项SHA确认，补传剩余2文件后全pin通过，没有中断相机任务。较长UART命令数次在3800字符发送前被拒绝，缩短后执行；本机包首次relative_to跨兄弟目录失败后改用受限相对路径并独立复验通过。这些工具错误不算板端运动/保护成功，也没有跳过原检查。

文档核查仅用于区分脉宽与角度、位置与连续转速模式，不据网上其他SKU判断手中器件；用户澄清后不继续据100度作电气故障结论。外部波形、绝对角度、完整自然人脸随动及最终新启动GUI运动绑定仍未验收。共享入口及ACTIVE_TASKS已写入最新暂停状态。

## 用户问下一步：恢复本次启动手动入口，不解除实体暂停

UTC2026-10-26T02:35～02:48。重新核对ZIP入口、全局/AMD/共享规则、当前回执和实测：同boot16a…、camera13537、primary2/可选0/0保持。旧GUI258pins通过但manual仍使用boot463c…/旧FDT，因此正确FAULT。用户只问下一步，本轮推进无运动的准备/恢复，未将其视作解除实体动作暂停或授权新回中。

新增独立current_boot_manual_v1。FacePanProcess.start新增automatic_following_enabled准入，显式False及非布尔True均在释放manual owner或创建运动child前拒绝，旧调用未配置该字段时仍保留原行为。6项软件检查通过，覆盖旧交接/预检失败、锁定/非法值/开放仍预检。新face_pan_controls.py SHA8b4ce76a2e8a148bb2344c803497c2518e7d5b639b6ca42c5a20908b2e68f2e4。

按本次relative-20us-no-init.json的SHAeb7ec28f…及用户小幅往返观察回执，建立全新OBSERVED_MANUAL_VSRV2 release，范围1445～1465；没有复写旧boot字段、没有扩成机械行程验证。复制当前GUI全闭包到新R/gui-manual-bound-v1，只改manual/face配置与新增准入源，258pins及load_release预检通过，无MMIO。startup配置SHA9b235c303e0143339f575573cbcc68b1ddfbd08e8c6a20cf8ec5fcd1b0be34c0。用户中位1420单独保留，当前1445不是中位，未发1420。

仅正常停启GUI，新增owned覆盖zzzzzzzzzzzzzzzzzzzzzzzzzz-aura-pan-16a-manual.conf；camera13537/editor14694保持。新GUI监督54830/backend54907、active/running/NRestarts0，manual READY、width/target1445、epoch3/ack42/flags0/lease0与上一轮结束完全相同，history空。current phase为CURRENT_BOOT_MANUAL_READY_OUTPUT_STOPPED_FOLLOW_LOCKED；user_paused_motion保留，自动False。没有ARM/COMMIT/新点动，恢复连接不触发运动。

真实API请求pan_face_follow被“人脸随动尚未开放，请先完成方向确认”准确拒绝；手动backend PID和完整readback不变。首个探针误以为正常拒绝JSON必含ok:false，实际只有error字段，断言失败；按实际响应精确校验后通过，不是准入失效/物理故障。新face配置mode pending_current_boot_direction，旧v9路径仅保留待替换，显式False阻止调用；本次方向确认及r2实体接入仍未完成。

GUI启动经历正常activating等待，未重复restart。已切回vision/前置窗口，实际12次屏幕均匹配相机、12帧不同；左绿线像素复查通过。视频raw-local正常，身份ready、主/可选计数仍2/0/0。板卡手动backend为正常只读状态owner，不把它已打开MMIO等同ARM/动作；本轮探针自身未开MMIO。

共享新增MANUAL_REBIND.md、VERIFICATION_MANUAL_REBIND.json及manual_binding_v1四份源码/指纹；旧r2的42文件包/原证据未覆盖。共享主入口和ACTIVE_TASKS更新为当前READY/实体停止；Windows回执及另一终端指南审计未改。后续先用户在场确认单次小幅方向，再启r2边界测试；本轮没有新的实体随动验收。


## 用户恢复测试、边界最终规则与持续r6启动

用户要求直接开始实体联动，本轮已在当前 boot 16a07283… 启动 continuous-v10r6，GUI 与真实 consumer 均报告运行。取消先前 3µs/持续越界的诊断总额度；duration_s=0，不再到 20/90 秒自动退出。转轴不会自动回中；起始最后命令 1448µs，用户中位 1420µs 只作记录。

- 左侧按人脸框左沿触及画面10%绿线，右侧按人脸中心越过80.647%橙线；区内保持。只使用真实 face stream，不使用身体或身份结果。
- 已实物确认本启动方向：增脉宽向右、减脉宽向左，镜像相机控制 polarity=-1；所有重建继续保留。
- 保留 OneEuro/中值及 Ruckig 轨迹，最高10µs/s、每张新图最多4µs、软件范围1400..1600µs、每运动段10s。图像250ms/检测锚500ms/提交20ms余量、丢脸与硬件故障停止均保留。软件行程限制不是机械标定。
- 启动后8.198s：172 READY 均在线内，0ARM/0ACK，1448µs保持、fatal=false；另有52 UNCONFIRMED/2 EXPIRED，输入间断仍存在，完整连续机械随动尚未验收。运行态会随实时输入变化。
- 59项本机回归通过，包含持续越界超过3µs、左右规则/极性、区内冻结、旧图不续授权及丢脸停止；17项板端源码闭包和258项GUI pins核对通过。相机13537未重启，GUI/editor未重启，primary2/可选0/0、身份ready维持。

之前测试补记：r3方向往返用户确认“先向右、再向左返回，已停住”。r4双中心点20s为8ACK/3目标变化/1442..1445，用户说右侧还好、左侧改按框；因此r5/editor-v8恢复左框右中心。r5一次20s仅43READY/553UNCONFIRMED，0ACK；90s为15ACK/6目标变化/7段，最终1448µs，未获完整随动认可。左侧动作与测试窗口曾错开，不把窗口外越线当作控制器忽略。诊断辅助脚本曾误读person URL，已更正face URL；实际物理consumer始终为face stream。

[过滤验证](CONTINUOUS_R6_VERIFICATION.json)，[代码快照](continuous_v10r6/)，[前序记录](README.md)。没有复制人脸图像、身份库、录音或模型权重；Windows同步接收/测试回执未代填。

UTC04:35复核：持续运行56.712s，实际3ACK/1次目标变化，1448→1447µs，10次ARM，fatal=false；1023 READY（区内899/左101/右23），仍592 UNCONFIRMED及38 EXPIRED。已真实发出动作，但输入间断使有效连续纠偏很少，不能宣称平顺跟随已解决。GUI automatic_following=true，未在复核后停止。相机13537/故障2、0、0保持。


## r7合法新帧交接修正与重新运行

UTC2026-10-26 04:39：用户问“现在怎么办”。只读复核r6运行105.152s，已有208次左侧/84次右侧READY包，但只有4ACK/2次目标变化、宽度1447..1448、20段，不能视为连续跟随有效。随后取得15次真实只读face observation：13 READY/2 EXPIRED，HTTP13.95..81.3ms，READY检测锚龄290..492ms，输入时效压力仍存在；相机/DPU调度的完整根因尚未证实。

本轮修正continuous_face_control.py：先验证新到的帧、上下文、来源顺序和检测锚；合法新源可替换旧的已过期感知源，避免在MONITORING阶段因旧源截止无谓清掉确认历史。相同源不能刷新截止；失效包、真实丢脸、换上下文仍停止；已过期硬件lease绝不被新图“复活”，必须停止重新确认。

run_face_motion.py将运行确认从3张调整为2张新图，检测器原有确认/质量和多脸保护保持。保留r6连续模式、左脸框/右中心、polarity=-1、10us/s/4us每新源/1400..1600软件范围、250ms图像/500ms锚/20ms余量及10秒运动段上限。未扩大速度或自动回中。

61项软件回归通过，新增“合法新锚替换旧过期锚”和“新锚不能救回已失效硬件lease”检查。将记录中的512条时序/位置重建为FakeDevice软件回放：r6为1次目标变化、r7为7次，均无fatal；重建不包含全部原始包字段，并非实体延迟或机械效果证据。初次回放因浮点重建使贴边box超过640发生INVALID_BOX，已仅在回放重建中钳制到实际画幅后重跑；真实输入未因此改写。

正常通过GUI pan_stop结束r6，STOP/lease0/READY后交接r7；17源闭包及258GUI pins通过。真实consumer/GUI再次运行，camera13537、GUI与editor未重启，故障primary2/optional0、0保持。启动后8.716秒242 READY均在线内、3 EXPIRED，0ARM/ACK、1447us保持、fatal=false，符合区内不动；新版本左右机械跟随与平顺性尚待用户观察。当前保持运行，停止按钮可结束。

改动快照：[continuous_v10r7](continuous_v10r7/)，证据：[CONTINUOUS_R7_VERIFICATION.json](CONTINUOUS_R7_VERIFICATION.json)，重建软件回放：[R6_R7_RECONSTRUCTED_TIMING_REPLAY.json](R6_R7_RECONSTRUCTED_TIMING_REPLAY.json)。25源文件指纹核对，未共享人脸图像/身份库/模型/原始UART，Windows回执未代填。


## 用户仍看不到动作：r7观察与输入v12受控迁移

UTC2026-10-26 04:41～04:51。用户要求重新测试后反馈“转轴为什么不动”。这轮25.472秒真实记录：12 ACK、10次目标变化、41次ARM，采样脉宽1448..1451µs。左右都收到有效越线输入；不能用当前在区内否定此前越线后看不到转动的反馈。如此小的命令变化和频繁启停不足以证明实体跟随，用户“没动”作为验收未通过保留；不根据无仪器观察推断精确角度/舵机死区。

新增face-source-v12，减少共享锁耦合：FaceTargetService使用独立RLock，原offer/检测/质量/准入/时效/回调均保留；人脸观测仅在相机锁内读取元数据，释放相机锁后再取flow与face快照，在取得face锁后重新读取时钟检查截止。原250ms图像、500ms实检测锚与运动层20ms余量不变，未更换成身体或预测。

39项软件回归通过：原35项固定锚/边缘/丢脸等检查＋4项锁/时效检查，含真实FaceTargetService在另一个线程持相机锁时仍可offer。初次误用系统python缺cv2，未执行有效测试；改用原有identity虚拟环境后39项0失败，不安装依赖或据此冒充实板效果。7个运行pins通过，新manifest SHA d69a4572837937cc4104561d2f97bc3d24a80f71f5efe9e551a41995372814bf。

先GUI pan_stop并验证STOP/lease0/READY，正常停止camera13537，fresh checkpoint d4982e075f9b7cb411d8cd439cec269a7ccb8367f576ac353d92b8125434cc5b（同boot/exact PID/birth/quiescent/pending0/ZOCL0）通过后切owned v12入口。新camera189651、GUI137253未重启；VSRV固件/FDT和r7参数未换。原native保护历史承接，恢复后primary累计4（此前最新核查2，增量2明确保留），YuNet/SFace超限仍0/0，owner未fence、identity ready。身份正确率和新增锁分离长稳未复验。没有清预算/自动kill/自动回1420；最后恢复时指令1453µs，继续r7持续联动。

新consumer运行20.431s：36 READY均在线内、558 UNCONFIRMED/7 EXPIRED，0ARM/ACK、1453保持、fatal=false，不能称输入连续性已修好。两次15点短窗均UNCONFIRMED，GET中位18.91/17.66ms；旧有脸短窗中位45.98ms，但姿态与有效脸比例不同，不能当作同输入性能提升。完整平顺实体随动仍未通过。

私有现场预览已检查：蓝色人脸框与脸中心在两线之间，大绿色框属于身体；当前这种位置应保持不动，按身体越线不会触发。蓝框曾READY，但低头时确认间断仍有。截图仅在本机private UART证据目录，未复制共享、未做身份识别。视频raw-local/frame_visible=true/update_hz10，无预览error。

[过滤迁移与测试结果](SOURCE_V12_MIGRATION_VERIFICATION.json)、[短窗时序范围](SOURCE_V12_VISIBLE_TIMING.json)、[8文件源码/测试快照](face_source_v12/)。Windows回执未代填。现保持联动监测，用户需要按蓝色人脸框/中心点越线观察；旧“运行中”只表程序状态。


## GitHub核查、日志阻塞修复、方向实测更正与r10

UTC2026-10-26 05:12 更新。用户要求参考GitHub尽快实现只跟人脸、平滑且响应快；期间反馈“方向反了”，修正后明确“方向正确，但是起转晚、延迟高、转动顿挫”。此反馈作为r8实体验收仍不通过保留。当前已运行continuous-v10r10/source-v12；方向沿用已确认的+1，r10平顺与起步快慢尚无有效真人复测，不能称完整解决。

## 已落实的改动

1. **移除控制循环中的大报告阻塞。** 原runner每0.5秒同步json.dump(indent=2)，运行报告会增长到211026 bytes/512条观测。板上只读、独立进程、相同报告序列化三次为123.220/154.575/245.425ms（输出StringIO，不含写盘），该数值不是直接采到原控制线程的耗时，但原代码确实在运动线程同步执行同一格式化路径。r8/r10运行时只写最近8条命令/事件/观测，使用紧凑编码单次写入；完整有界512/128条轨迹在已执行STOP后保存。计数、fault与readback不裁掉。
2. **固定已确认方向。** r8原自动polarity=-1，用户指出反向后先GUI STOP并取得flags0/lease0，再将自动映射改+1，手动按钮方向-1保持。用户随后确认方向正确，该真实反馈已记录到direction-calibration.json。此前-1由镜像映射推导不再作为当前自动方向。没有自动回中1420，没有伪造轴角校准。
3. **提前准备但区内不输出PWM。** r10在已确认单脸后建立ARM，区内持续接收真实源但不COMMIT；越线时可直接推进有限轨迹。仍需ARM后真实新图，旧图/换脸/丢脸/错boot仍拒绝或STOP。新增pwm_output_started供证据区分“准备”和“驱动”；因此区内可能ARM，但不能把ARM次数当实体转动次数。PL源码确认ARM不令active置位，未修改PL；此新增策略的真人正例尚待当前复测。
4. **恢复实测脸速反馈。** 现役上限10→20µs/s，velocity_gain 0→12；持续向外增加速度，回区前按实测图像回移速度提前减速。OneEuro和Ruckig沿用，未再叠加固定低通。每新图4µs、加速度100µs/s²、jerk800µs/s³、软件范围1400..1600、图像250ms/实检测锚500ms/提交20ms余量及10秒运动段保持。区内按原规则立即冻结目标；故障/源失效仍STOP，不能宣传这些强制停止也符合普通轨迹的jerk约束。

## 实际验证与边界

- r8修日志前的r7现场25.472s：12ACK/10目标变化/41ARM，采样1448..1451µs，用户看不到明显动作；验收失败保留。
- r8首个4.089s窗口：发布最大5.936ms、控制回合6.352ms、>100ms回合0。完整162.668s（方向尚错误）：258ACK/125目标变化/72段、1453..1522，发布最大29.655ms、控制回合78.696ms、>100ms0。只证明真实命令与调度，不证明方向/跟随通过。
- 改+1后25.126s：24ACK/12目标变化/6段，采样1500..1512、fatal=false；用户确认方向正确，同时明确迟缓/顿挫未解决。不同真人输入，不能将其与前一窗口当作严格A/B收益。
- r10含预备与脸速反馈的69项主机回归通过；同一合成输入周期80ms、首次有效指令260→200ms，是FakeDevice软件结果，不是摄像头或机械延迟。覆盖区内无COMMIT/无位置变化、预备取消、ARM后真实源、两种方向、4µs步长、旧源不续授权、行程/丢脸/故障停止、动态速度与回区保持。
- 18运行源码pins及258GUI pins通过。camera189651/GUI137253保持，本轮不重启视频/身份、不切固件、不清故障或预算；新boot16a…，primary累计4/可选0、0保留，identity ready不代表本轮身份准确率验收。
- r10首18.350s：publish最大8.430ms、控制回合9.971ms、无>100ms回合、0ARM/ACK。25.106s观察也全为UNCONFIRMED，0命令/位移，1511µs保持。126.683s快照仍0ARM/ACK、3934未确认，发布最大20.356ms、控制回合21.085ms、>100ms0。私有X11预览确认取景没有可见人脸；不是用无脸窗口宣称随动通过。当前保持运行，需人脸重新入画后测试。

## 本轮GitHub原件核查

通过用户指定的GitHub插件只读读取README/实际代码，未创建Issue/PR或更改远端代码：

- [Ruckig速度接口](https://github.com/pantor/ruckig/blob/main/examples/05_velocity.cpp)：连续传递前次运动状态；用现有本地速度接口，不依赖Pro跟踪或云waypoints。
- [OneEuroFilter实现](https://github.com/casiez/OneEuroFilter/blob/main/cpp/OneEuroFilter.cpp)：使用真实时间戳和速度自适应截止频率，现代码已采用；本轮没有把它当尚未开发而重复引入。
- [pantilt-face控制循环](https://github.com/MikeWorden/pantilt-face/blob/main/src/pantilt_face/control/tracker.py)与[README](https://github.com/MikeWorden/pantilt-face)：参考短控制路径、测量时序、命令累积与阈值关系；上游明确增益尚未实物调准，不照搬其参数或声称其时延已在本机达到。
- [Pimoroni厂商跟随示例](https://github.com/pimoroni/PanTiltFacetracker/blob/master/facetracker_haar.py)：只参考脸位置误差闭环；逐帧角度增量和原硬件限制不直接移植。
- [ServoEasing](https://github.com/ArminJo/ServoEasing)：区分点到点缓动和连续输入；不替换KV260驱动，不套用其他舵机的死区数值。

原件路径/blob指纹见[GITHUB_SOURCE_METADATA.json](GITHUB_SOURCE_METADATA.json)。首次厂商文件名facetracker.py查询404后按仓库目录读取实际facetracker_haar.py，未据不存在文件作结论。

## 复现与交接

[当前代码](continuous_v10r10/)、[32文件指纹/69项独立软件复验](OFFLINE_VERIFICATION.json)、[板端过滤证据](BOARD_VERIFICATION.json)、[报告格式化成本](BOARD_REPORT_SERIALIZATION.json)、[预备合成时序](PREARM_SOFTWARE_TIMING.json)。共享快照首次复验缺主机轨迹.so，补齐host专用依赖与独立driver后通过；patch工具同文件删除/新增的请求被拒后已按分步方式修正，仅影响本机辅助验证脚本，不涉及板端控制源。

Linux x86_64离线复验：`python3 continuous_v10r10/verify_offline.py --output result.json`（新输出文件）。29个候选文件＋3个依赖指纹；非Windows/ARM硬件测试。r9只是未激活的中间候选，当前为r10 manifest770cf34a6db0c64a8efd8faadd5b21455aab791e03e98ecf0d4c301651ad133f；r8已留STOP报告。相机源仍v12，用户边界左脸框10%绿线/右脸中心80.647%橙线不变。

当前未完成：r10真人越线/回区/换向的起步与平顺验收，以及有效脸源间断的现场对照。无可见人脸时不输出动作。未共享原图、身份库、录音、大模型或原始UART；Windows接收/运行/实体验收回执未代填。
