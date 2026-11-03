# 转轴上板预检通过，随后串口无响应，未切换或试转

用户明确现在可以上板测试，承接此前无测量仪器也允许小步观察的授权。本任务接管维护窗口，未新建代理；先读ZIP/项目规则既有上下文、最新共享入口、主统筹及当日实测，不复用旧boot/PID或原生r4以前的业务根。

## 已实际完成的板端只读检查

独占UART的context/health/inventory/entries四次探针exit_code0，响应SHA及console echo恢复通过。首次组合探针超出3800字节串口行限制被本机拦截，已拆分；该失败未发送任务命令。

- 实际boot `c5f247b9-76b9-40a3-85ca-96578055eb5c`，SD身份匹配，当前官方`kv260-benchmark-b4096.bit.bin` operating，VART仍官方路径。当前FDT SHA `22516e08c2c862dfe3ee999a962ff62ed7830ad8e1183e36432cd22acde77762` 已读取并在本机与候选DTBO合并通过，合并后firmware-name正确。
- camera1309/GUI1310/X1077，三服务active、NRestarts0；相机实际原生r4根和GUI实际66cde810启动根已定位。motion锁不存在/无持有者，未开MMIO。
- 13:37 UTC前后最后成功health样本：YOLO9.94Hz、29796帧、native_critical=true、owner未fence、worker及身份ready；YuNet10929完成/累计超限0，SFace442完成/累计超限0，gap0。主周期累计1保留，不能称生命周期零超时。GUI IDLE/IDLE_READY/未播放，录音IDLE、无待转写。pan FAULT具体为Boot mismatch、pulse/target null、自动跟随false。
- 当前服务及drop-in、配置、身份库只取SHA，未复制数据库/照片/音频/向量。读取了实际原生启动/关闭代码，确认当前native_entry会自动承接最新quiescent checkpoint；未来停服务仍须核对原PID/birth、无在途任务及完整计数，不改源配置清历史。

## 已完成的本地传输及恢复准备

板内v1固件SHA与本机封存基线一致：`a8b783…`。对已通过离线审计的v2整文件生成COPY/ADD差分；本机完整重建逐字节及SHA通过，目标`dc708cb21c3c99c3e2de9f6969d9c1ec7c5c97d347d675b15014d6686931902d`，7807932B。差分gzip213800B，相比全文件gzip3163392B减少串口传输；包含驱动/元数据/脚本的独立包287936B。

差分5项正反例通过；恢复检查点7项门槛通过（精确PID/birth、源清单与unit、无pending、fault计数不减等）。`firmware_trial_controller.py`已准备：默认仅报告就绪，真正执行才装独立应用、停GUI/确认PCM关闭、正常关闭原生owner并核验检查点；持DPU/运动锁且无ZOCL客户时才切换，失败有独立恢复守护，不能强杀未确认owner。该控制器尚未上传或板端验证，不当作恢复已经通过。

## 实际阻塞及影响

上传包前的connect失败，提示`Root shell not confirmed; no task command sent`。后续两次隔离重连仍失败，三份raw接收长度均0。四路FTDI设备仍枚举、未发现串口FD持有者；宿主自最后成功查询以来无新USB/UART内核错误/断开记录。备用SSH到192.168.50.2:22也超时，但Ubuntu当前网络拓扑不能据此证明板卡断电。

目前不能确认主电源、PS运行或console通路的实际状态；已向用户请求确认板卡主电源/指示灯及USB接线。没有发送中断、复位、登录猜测或强制恢复。

**本任务没有安装/加载新固件、停止/重启模型服务或发送运动指令。** 文件接收器未启动，未开始板端差分重建；不能把本机差分通过写成上板通过。当前业务是否仍健康已因无响应而未知，前述正常值仅对应最后一次成功样本。原始UART、完整FDT及生产元数据仅在本机私有目录`/home/ghmd/aura-pan-board-20261024`；共享交付只含过滤数字、源码与校验摘要。

通信恢复后先重新确认boot、CID、FDT、服务源和当前owner；若启动改变，重做上下文与包的boot绑定，不能只改旧脚本常量。随后继续候选重建/ID-STOP/原生r4共存，再做用户已授权的2秒有限试转。Windows回执未改。

## 用户给转轴上电后的接续：新boot，已完成有限指令与停止

用户明确“继续，我给转轴上电了”。UART恢复，实读新boot `1236ccf4-7df1-420e-83e7-8df17e2c53a4`；归档c5f旧上下文并重新取CID/FDT/服务/模型/库SHA，无运动锁。官方固件operating、原生r4与GUI原根保持，初始camera1295/GUI1296/X1076、身份ready/gap0。新FDT SHA `ea23969f6b92f044d1068165100202cea6121b14c85160aa415d252ceaa63dd7` 与候选DT覆盖在本机合并通过。

差分与成套小包重新绑定新boot，287921B包传输0重试、板端重建7807932B目标整文件SHA正确。一次控制器上传因上一重建仍持串口锁被拒，未发命令，等上一操作结束后串行重传成功。未并发持有UART。

### 第一轮：硬件ID/STOP过，GUI等待门槛失败并实际回退

控制器ce911160…安装独立v2应用文件；正常关GUI并确认PCM释放，正常结束原相机，精确核验quiescent checkpoint的boot/PID/birth/无pending、源manifest/unit以及不减的计数。checkpoint SHA `208702a61808ae0f78b69665b481e7b4c97d612324d3a49fb28437068bcfd930`。在DPU/运动独占锁与ZOCL无客户条件下切v2，ID `56535256`/ABI2/build778d2512及STOP通过，flags0/lease0，无ARM或COMMIT。

首次维护控制器只给GUI70秒，短于其已有90秒display＋90秒ready宽限；未确认GUI就绪即拒绝。自动回退最初又遇GUI接口未完成启动而拒绝，记录RECOVERY_HOLD，没有强杀任何原生owner。补足原GUI等待后，经独立有锁恢复程序实际停同版原生r4、保留新quiescent checkpoint、切回官方固件并启动原业务；最终BASELINE_RESTORED_AFTER_TRIAL_FAILURE、恢复单元success退出、旧guard timer inactive。原生r4/GUI正常、计数承接，未将该轮追认为成功。

第二版只修维护GUI等待，按既有配置计算总宽限210秒；95秒就绪成功且不重复启动、永不就绪仍有界失败两项测试通过。固件/RTL/Native/业务源码未因此变化。第一轮所有拒绝、实际回退及source/controller pins保留。

### 第二轮：原生r4真实共存窗口与2秒台架通过

独立root `.../778d2512-1236ccf4-r2`、控制器ded9704e…，候选包287935B/0重试。重新绑定恢复后的实际PID与完整检查点，加载相同v2固件，ID/STOP再过；原生r4 camera8272、GUI8299、Xserver1076，GUI按原宽限启动成功。

62.651100559秒窗口：YOLO623新帧/9.943959Hz，YuNet220次新native完成，SFace95次新完成；optional超限/gap/主周期超限新增均0，身份及worker ready，owner未fence。主周期累计4保留（含多次正常启动），不描述整个维护过程零超时；更早启动域故障历史仍经原生检查点/归档链保留，没有修改配置或重置预算。

14:44 UTC左右在原GUI IDLE、音频IDLE_READY、无录音/待转写条件下，只执行一次用户已授权的有限台架：1420µs初始化试验点1秒→1425µs1秒，100ms独立租约，44条连续ACK，末次事件1988.53ms。正常QUIESCE完整结束与最终STOP回读通过：flags0/lease0/active=false/armed=false，width/target1425、epoch1、ACK44；Native关闭也STOP，随后独立再读并STOP核验同样关闭。没有自动跟随、开机ARM或追加扩大试步。

用户已被请求确认实物是否轻微转动并停住，**反馈尚未收到，不能称机械效果通过**。无外部测量设备，external_waveform_verified=false保持；历史1420只是初始化试验点，没有当作本次已标定机械参考。

### 当前保留与最终审计

当前同boot、v2联合固件active、camera8272/GUI8299/X1076；原生r4继续运行，最终YOLO累计约9.9Hz，YuNet/SFace本启动超限0，旧计数历史保留。现役222份camera Python完整source manifest、原生库、GUI启动入口及251项component pins、所有旧unit/drop-in、配置和身份库SHA通过。首轮终审脚本误把启动包装器的gui_sha256用于GTK主文件，断言拒绝；已按实际launcher修正校验对象，真实主文件component pin保持，复测通过，失败原件保留。

控制器phase `CANDIDATE_STOPPED_RETAINED_PHYSICAL_FEEDBACK_PENDING`，activation单元success/inactive，guard timer与guard service inactive，运动无owner。产品GUI仍使用旧v1/旧boot的手动适配器，manual_pan仍FAULT/Boot mismatch；**本轮是独立台架通过，尚未迁移GUI按钮/正式放行或实现随动**。不能只改旧boot字段、伪造QUALIFIED或把新固件寄存器回读当实物角度。

板端墙钟仍是2021年且未经校准，阶段关联使用boot/PID/单调时间及宿主UTC传输记录，不采信板端墙钟为现实日期。本轮不顺带调整系统时间。当前应用配置是否跨下次冷启动保留尚未复验；不承诺冷启动自动恢复到v2。

## 用户未留意首轮后明确要求20µs往返及再试一次

用户反馈“没有，我没注意”，仅记录首轮未观察，不归类为确认未转。随后明确“20us”，本轮改为从已回读停止的1425µs出发，1425(0.5秒)→1445(1秒)→1425(0.5秒)，共2秒；保留1400～1600范围、硬件每帧4µs斜坡、100ms租约、迟到/上下文/许可失效拒绝及正常QUIESCE和最终STOP。新工具5项正反例通过，冻结的5µs台架工具未改。

20µs第1次（总台架第2次）在执行前提示3秒；44 ACK、末次1978.625ms，回读最大1445/最小1425，最终flags0/lease0/width=target1425、epoch2。相机PID8272保持，新primary/optional超限和gap均0。用户随后要求“再试一次”，未据此推断前轮机械结果。

同范围再执行一次（总台架第3次），仍提示3秒并只发一次；完整上下文要求前一次STOP的session/epoch/seq匹配，新增独立结果文件，未重放旧动作。44 ACK、最终flags0/lease0/width=target1425、epoch3；具体单调时间与前后模型差值见observed-20us-summary-03.json。两次20µs动作后都不自动重复；当前实物观察仍待用户反馈，方向/真实位置/外部波形不填写通过。GUI旧按钮未迁移，模型服务未为这两次试步重启。

用户在第二次20µs后反馈“看到了”，确认那次往返实物反应。随后用户又要求“在试一次”；再次按1425→1445→1425µs执行2秒，44 ACK，最终epoch3、flags0/lease0、宽度与目标1425，转轴输出停止；相机PID8272保持，新增主/可选超限与gap均0。最新一轮肉眼反馈仍待确认，不能把前一次确认自动套用到这次。共享交付的历史说明已同步GUI实际接入进度：板端UI候选已经运行，窄范围1425～1445µs，仅直接手动点击，不启用自动跟随；本次动作用受限台架控制器执行，没有点击GUI按钮。

### 接入视觉 Shadow 的准备（PWM仍关闭）

用户同意开始视觉 shadow。只读板端探针发现当前 `GET /v1/motion/observation` 返回404；未读取图像、未改服务、未发送转轴动作。对运行相机源码做AST检查，shadow扩展依赖的13个CameraState时间戳/已选轨迹字段和`handler_for`/`main`均存在，源码SHA `9d714b9b…`；这是静态接口匹配，不是动态部署验证。

从已有跟随实现建立独立候选`/home/ghmd/aura-pan-follow-shadow-20261024`和共享交付`2026-10-24_pan_follow_shadow`：建议范围硬限1425～1445µs，最大步进4µs/帧、40µs/s；明确1425是最后停止指令、方向和机械零点均未知。36项软件检查通过；90帧历史fixture回放86条软件候选，结束DISARMED/REPLAY_ENDED。fixture不作为当前实况或实体随动证据。

实时路由要在当前受保护相机入口中安装只读handler；直接切旧wrapper会绕开native owner/checkpoint，因此未这样部署。服务重启会短时中断相机/DPU业务；按用户“尽量不影响另一个终端”的要求，本轮没有重启/变更相机。实时shadow和相机方向判断仍待合适维护窗口，实体自动随动继续关闭。

用户回复“可以”后，继续按维护窗口准备。复查确认当前候选已包含与旧交付一致SHA的`camera_feed.py`、`common/motion_observation.py`和wrapper；用shim在不改动已pin的`native_entry.py`和相机源文件的前提下，让原native入口仅在加载相机模块时经wrapper安装route。Shim保留原入口的checkpoint消费、启动pin和未确认native owner时hold逻辑，并额外核验当前source文件SHA。专属shadow代码与新ExecStartPre哈希门已传输，systemd drop-in已暂存并加载校验通过；活动进程仍PID8272/GUI29919，未重启，PWM/转轴未触碰。

本次重启门检查发现手动面板打开，虽当前状态READY、1425µs、flags0/lease0，仍未停服务；继续保留交互界面，等手动面板关闭后再做一次即时门检查。分阶段控制器先正常stop并验证PID/birth精确匹配的quiescent checkpoint、owner退出及ZOCL refcnt0，再启动新入口。若checkpoint不符就停在原地，不杀进程、不替换owner。此时live route仍未启用，real-time shadow未运行。

执行相机停止控制器时，独占UART未能确认root shell，返回`Root shell not confirmed; no task command sent`；相机停止命令并未发送。随后用户报告板卡断电。断电前最后核实原相机PID8272还在运行、活动checkpoint仍是旧源PID6351，故无当前PID8272的受控停止checkpoint。已暂存的owned systemd drop-in保存在板卡系统路径，可能在下次启动运行shadow入口；先保持板卡断电，恢复后先只读核验/撤销该入口或重新建立安全checkpoint，再动业务。无实况shadow、无转轴动作。

离线恢复检查：Ubuntu当前只有本机NVMe，没有发现SD/USB启动卡。`/home/ghmd/kv260-sd-backup-20261003/rootfs-mount`是旧备份的未挂载目录，没有修改旧镜像。先离线撤回staged drop-in需要用户将板卡实际启动卡接入Ubuntu并核验设备身份。

### USB接入后的新boot与实时shadow尝试

用户报告先保持断电，随后通过USB接回板卡。Ubuntu只见FT4232串口、未见启动SD。受控stop控制器先前在UART root-shell确认前退出，`Root shell not confirmed; no task command sent`，未发送stop；因此本次是用户power-cycle后的新boot，而非本代理受控重启。已暂存drop-in随系统启动生效，保护shim运行原native入口并启用只读motion feed。

当前boot `463c9307-5e47-49b0-b22f-5fd3fc21451c`，camera1308/GUI1307，YOLO9.89Hz、native owner未fence、identity和worker ready，freshness gap0；`/v1/motion/observation` 返回READY、source age约45ms。转轴手动backend因Boot mismatch为FAULT，readback字段null；自动跟随关闭，本轮不访问转轴寄存器。

**计数连续性断开：** 当前startup checkpoint仍来自PID6351和旧boot1236…；当前health primary overrun为1，而断电前保留的boot1236报告为4。不能把1当故障减少，也不能把旧4覆盖/伪造回当前运行。两个boot计数域分别保留；本次shadow前后新主超限/可选超限/gap增量均0。

实时shadow第三次启动尝试成功执行、受安全边界停锁：1条READY源帧、age165ms，选中目标触发`HORIZONTAL_BORDER`；shadow耗时0.037秒，最终DISARMED，suggestion0，寄存器写0。不是10秒通过。此前两次runner启动分别发现导入名和`PYTHONPATH`打包问题，均在shadow循环前失败、没有硬件访问；补齐只读别名/启动环境后第三次才进入控制器。

下一步等目标完整居中后再跑一次10秒shadow；仍保持`ShadowDriver`和1425～1445µs软件建议界限，物理方向/机械参考未标定且manual backend readback不可用，所以不启用实体随动。Windows回执仍不代填。

### UTC 03:09：推送式只读通道完成10秒Shadow，实体固件与SFace保护仍待处理

用户再次同意居中实测。GET轮询版处理13个新源、8条软件建议后于1.304秒SOURCE_EXPIRED。继续10秒只读诊断：30ms客户端sleep得到99源/208请求，真实EXPIRED1次、最大257ms；5ms sleep得到99源/427请求、当前包均新鲜，但新包抵达时旧源年龄最大266ms，仍会触发连续性停锁。没有放宽250ms源期限或修改停锁。

在独立`stream_v2`目录实现推送route：`CameraState.observed`完成原发布后仅Condition.notify，原owner不做socket/file IO；HTTP线程在相机锁外发送同源协议，单消费者、最多10秒、50ms心跳不刷新源时间、250ms写超时。新consumer不导入VSRV。7项新验证用同SHA r4 CameraState和真实fixture HTTP完成，覆盖慢消费者隔离、冻帧停锁、源时间保持、旧route兼容、完整窗口和长度/并发边界。

专属6文件bundle传至`.../pan-follow-shadow-stream-v2`，新拥有的高序drop-in暂存；原相机/原native入口源码与旧pins均不改。实际正常stop PID1308后独立核验fresh checkpoint（SHA `65c6013e09c4e7493a0f1e54d3ca4a821a8f0f1d4099ae31483f10567570ff19`）、精确PID/birth/boot、无pending/fenced/active、源计数不降、旧owner消失和ZOCL refcnt0，才同boot启动camera17671。GUI1307保持，所有本boot计数和恢复预算承接。旧boot丢失的4→1计数断档不伪造补回。

实板stream shadow10.040秒：99新源/225 READY、最大帧龄202ms/中位102ms、95软件建议全部1425µs，TIME_LIMIT正常DISARMED。相机同PID，113检测帧增量，主/可选超限/gap新增全0，寄存器写0；日志0600。仅说明静态居中目标的短时视觉输入/软件链通过，不说明真实转向、方向、角度、全程最坏时效或长稳。输出范围仍1425～1445µs，物理校准false。

终审发现两个现实阻塞：其一冷启动实际PL仍是官方`kv260-benchmark-b4096.bit.bin`，未加载VSRV/2联合版；manual FAULT报`Exact board/boot/firmware/VART context required; no MMIO`。其二SFace在stream十秒窗口之外又有2次超限，相对clean checkpoint的累计1→3，恢复2次预算用尽后LATCHED、identity_ready=false；YuNet累计1并RUNNING、owner未fence、YOLO继续。最后SFace报告completed=1/result_fresh=1/hardcap=1，start到release约32.657ms。该数据是执行时限保护，不是姓名匹配分数；不归因于用户理发或新stream，也不重启解锁/清预算。保留数值报告交后续原生任务。

源与checkpoint终审通过：相机源SHA9d714b…、原native入口839df5…保持，原8 pins和新6文件全匹配；新drop-in98cdd6…保持Restart=no/SendSIGKILL=no/KillMode=process/stop无限等待。完整业务终审因SFace LATCHED未通过。最新共享报告`2026-10-24_pan_follow_shadow/STREAM_V2_REPORT.md`、各PROGRESS和导航已更新；Windows回执未代写。

### UTC03:34：按用户催促优先恢复当前boot实体手动链

用户要求加快并明确转轴已经上电。重用已安装且SHA相同的VSRV/2位流/DTBO/xclbin/驱动，不重建FPGA。当前FDT与历史boot不同，先导出只读base，使用已有fdtoverlay工具完成新base `27960a4871bd04dd6e33854eab4542c267f3cd3014f210bab0b578e2a2c200e6`合并，merged SHA b18b9dbb…、firmware-name正确。未使用旧FDT证明代替当前核验。

相机PID17671正常stop并导出精确checkpoint d763407d…，PID/birth/boot、无pending/fence、计数单调与ZOCL0通过；再正常stop GUI，持DPU/运动互斥切换联合固件。ID/ABI2/build778d2512及STOP过，未ARM/COMMIT；随后恢复原相机entry和GUI，camera27275，新bootSFace累计3/LATCHED预算保留。原相机源、服务旧drop-in及身份库SHA保持。

提前提示用户后，采用历史已观察范围1430→1425µs初始化2秒，再1425→1445→1425µs往返2秒；44ACK、末事件1992.23ms，flags0/lease0/active=false/armed=false、width/target1425，camera同PID。用户明确回复“看到了，来会停住”。当前trial SHA4379c764…和这条新boot人眼证明绑定，未改旧boot JSON冒充当前证据。

以当前实测创建独立GUI clone和OBSERVED_MANUAL_VSRV2 release，只放行1425～1445µs、每次≤20µs/2秒。254component pins及load_release/preflight通过；GUI-only启用owned配置，新GUI30738/backend30808，manual READY，输出已停。面板已打开但打开本身发动作0；原GUI目录和用户偏好保留。机械参考/方向仍false，不把1425命令值当物理零点，未启自动跟随。

当前联合固件下补stream窗口：5.06秒/51新源/116 READY、最大帧龄192ms、46软件建议1426～1445µs；目标贴边触发HORIZONTAL_BORDER锁停，寄存器写0，主/可选新增超限与gap0。此窗口未达到10秒，不与前序官方固件下完整10.04秒混写；足以记录当前joint短时源输入及保护响应。当前实体自动随动未验，仍需极性/机械范围与受限控制接入。

最新交付CURRENT_BOOT_RESTORED.md、三处PROGRESS、共享入口与资料导航已同步，过滤证据12份/当前trial和human proof链已复制，不共享原始UART或图像。当前boot下VSRV/2已恢复；冷启动自动恢复仍未验证。SFace时间上限问题保留另处理，无重启清预算。


### UTC04:30：按用户要求改为人脸边缘触发；画面闪断已定位并恢复

用户明确中间区域保持不动、靠近左右边界再转。独立控制器已实现人脸框边缘8%进入/18%退出迟滞、150ms滤波、12us/s速度/40us/s²加速度、单新源步长<=2us及1425～1445us硬范围；不用头部yaw、不依赖SFace身份就绪、不以人体框回退。方向用本boot两次实际GUI点动及用户“实际向左，向右”绑定，+pulse实体向左，镜像相机控制极性+1。该绑定只说明方向，不是机械零点。

原生FaceTarget更新受检测计算与检测后等待影响，face-only v1/v2多次shadow因250ms源过期提前停止，未完成连续跟随。v3/v4尝试像素补帧；v3未取得READY，v4只短暂READY后停，不能把等待满10秒写作输入链通过。全部shadow寄存器写0、实体自动跟随未启。r4模型/owner、checkpoint、保护阈值和故障历史按正常stop/fresh checkpoint承接，没有重启清预算。v4诊断已显示YuNet为CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN、recovery_budget_exhausted；SFace此前LATCHED也保留，完整三模型业务验收不通过。

用户报告画面恢复约一秒又消失。初查采集/检测仍持续，preview原250ms过期清屏；撤回补帧至v1后仍发生。进一步发现内核大量“HC couldn't access mem fast enough for slot 4 ep 3”，/dev/kmsg buffer overrun；debugfs slot04明确对应USB1-1.2 Lenovo MCP01（17ef:a03b），不是camera slot05。瞬时CPU测量journald约34.8%/syslogd34%，MCP01播放pcm0p RUNNING，音频worker30855。

正常停止GUI以关闭音频播放，保持camera56342同进程、转轴flags0/lease0；仅对确认的MCP01 /dev/bus/usb/001/004执行USBDEVFS_RESET后恢复原GUI58434，方向映射恢复+1。报错采样由0.301s内4440条降至audio_closed/reset后/GUI恢复后各0条；原生主/可选新增overrun全0，未修改日志级别、清日志、放宽预览或运动期限，也未重置整板/USB控制器。用户现场明确回复“稳定了”。随后12个UI采样均frame_visible=true。证据：latest-mcp01-visual-recovery.json、latest-mcp01-preview-verify.json及各自私有UART response。

跟随工作继续：低分辨率模板位置测量候选v5与带10秒试运行/停止按钮的独立GUI正在准备；它们不是已通过实体随动的结果。v4当前camera62151/GUI58434，输出保持关闭。软件24项face-edge/图像跟踪/驱动交接测试及3项GUI所有权交接测试通过；早期默认python缺cv2，改用现有identity/.venv完成实际图像测试，未安装全局依赖。Windows回执未代填。

### UTC06:12：用户自定右线、有限越线回区试转；覆盖视频的设置窗口已修复

v5相机66241及GUI supervisor76450/GTK76636已启用；显示问题最终通过自身GUI副本placeholder修复和仅预览500ms宽限处理，运动250ms源期限保持。连续30.387秒60/60预览可见、60不同帧、0错误，用户明确“视频好了”。新增有限motion-v2曾7.381秒85ACK/1426→1445µs，用户“看到他动了”；旧速度/限幅过保守，输入短暂未确认后lease失效停止。全部同boot故障历史保留。

用户要求只用脸中心、自定左右边界。左线为实际画面左端；右线拖定widget比例0.71582536，含留黑的视频widget为8,112,568,300，实际内容92,112,400,300，换算右线实际比例0.80647201538/屏幕x414.589。不能直接用widget比例控制，也不能把左0下未验证左触发写成双向通过。

新motion-v3r2限定1425..1505µs、24..40µs/s、120µs/s²、≤4µs/新源、80ms滤波。只看face_center，越界2新源开始，原始测量回区立即停，滤波不移动边界。线内9.978秒0PWM；越线1.748秒16ACK，1445→1476µs，SAFE_ZONE_REACHED，final flags0/lease0/READY，44/44视频可见、新主/可选超限0。新31µs物理效果未获该次人眼确认。原manual点动范围1425..1445不改；新增基于pinned consumer/report SHA/精确hardware身份的只读已停止位置恢复，不扩写权限。13专项通过。

边界设置窗原Gtk TOPLEVEL受WM最大化、缺独立中文字体，用户报告界面异常，私有截图确认整屏遮盖主视频。先停止编辑器恢复主GUI，v3改POPUP/默认隐藏控制面板/原中文字体注册/正确橙蓝绘制与留黑坐标；修复后截图核验主视频及face蓝框、橙线均正常。最终25/25不同帧可见/0错误、257源码pins一致、editor130474无错误，全程STOP、camera66241/主GUI不重启。一次大PNG串口传输超时及重复stop transient已收集单元返回5均保留，后改小JPEG与接受not-loaded停止结果，均未触发新运动。

SFace仍3超限/2尝试/2恢复LATCHED，YuNet7/6/6同锁且CPU检测回退，primary18，最后窗口新增0；未清预算/换身份库/伪造ready。持续随动、机械零点、角度/外部波形/长稳仍未验收。用户睡觉离开，明确授权自行先完成未完成项，再做真实脸移动速度反馈和中值滤波；记录ACTIVE_TASKS_20261024.md，先处理合法原生恢复与连续跟随。共享FACE_ZONE_VERIFICATION及源码已更新；Windows回执不代填，图像/原UART不共享。
