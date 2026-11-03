**最终状态：本轮代码与板端接入完成，输出关闭；新版真人物理验收待用户回来。** 最新报告：`/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-24_pan_follow_shadow/FACE_FOLLOW_20261025.md`，证据`FINAL_VERIFICATION.json`。当前camera153151/GUI265320/editor238044，identity READY、SFace/YuNet RUNNING、旧超限3/7保留；primary19。新consumer continuous-v2r2/manifest251ec580…，三点中值、80/100ms平滑、脸图像速度反馈、8～60us/s、4us单源步长及1425..1505us范围。手动范围已按独立USER_BOUNDED_MANUAL范围对齐，不称机械限位实测。17项板端PS算法/会话、4项手动授权、4项GUI/画布软件检查通过；60秒墙钟/子进程58.637秒无人实流179/179预览可见、0ARM/0COMMIT，停止后READY/flags0/lease0/1476us/epoch11/ack16。最终12次X11画面均匹配相机，12帧不同，最低相关0.99645，USB新错误窗口0。

当前boot许可与原20us观察证明均保留。机械零点/限位/角度/外部波形、新版真人姓名及平滑度、冷启动组合尚未验收；Win接收/同步版本未代填。原始图像及UART私有，未放共享。现役native runtime unit7cf7eaee…；保存的前代checkpoint仍来自66241且已消费，下一次正常stop会导出新unit。回退需fresh checkpoint后显式兼容迁移，不能直接删24z入口。

以下为过程记录，较早“未完成/激活中”由上述最终状态更新。

当前用户授权与执行顺序（用户已离开睡觉，2026-10-24当地）：

1. 完成未完成项：界面恢复、身份识别异常、可用的人脸边界跟随。
2. 完成后增加：依据实际人脸移动速度的反馈；中值滤波与平滑转动。
3. 保持其他终端成果，独立目录/owned服务/哈希链；不伪造故障预算、真人或物理验收。
4. 用户不在现场，使用有界运动与丢脸即停；不能把无人参与的测试写成人眼验收。

当前已实测：

- 主相机66241/GUI76636未重启；257组件pins通过。
- 右线全widget 0.7158253629442671，实际视频0.8064720153808593，屏幕x414.589；视频rect92,112,400,300；左线实际画面0。
- motion-v3r2：1425..1505us，24..40us/s、120us/s²、80ms滤波，脸中心越线2新源触发/回到区内立即停。
- 9.978秒线内测试0PWM；1.748秒实际越线试转16ACK，1445→1476us，SAFE_ZONE_REACHED，最终flags0/lease0。无该次用户物理效果确认。
- GUI manual原1425..1445不扩写权限；新stopped-face-readback经pinned consumer manifest+report SHA+exact epoch/session/ack/pulse验证，允许只读恢复READY。13本地专项通过。
- 新editor原Gtk主窗被WM最大化并中文缺字体，覆盖视频；撤掉后恢复。v3改POPUP/默认隐藏panel/本进程原中文字体/绘制橙蓝，截图核验正确；旧v1/v2错误保留历史。
- editor当前transient PID130474，不自动开转轴；25样本25不同帧可见、0预览错误、STOP保持、0新超限，camera同PID。
- SFace故障3/恢复尝试2/恢复2，LATCHED预算耗尽；YuNet故障7/尝试6/恢复6，同LATCHED、CPU检测回退。primary18，当前boot保留。旧断电跨boot4→1计数断档保留。

下一步正在定位：原生保护锁没有合法现场恢复API。候选应显式人工请求、原历史全保留、旧预算窗口自然满600s、当前primary连续健康30s/真实进度、无active/pending/fence，再转cooldown10s/3探针。不能篡改checkpoint当原样恢复。需新增native API并测试，降低偶发调度拖延可在native optional调用期间限定当前线程RT优先级，调用后精确还原，不调大30ms cap。

证据入口（均本地私有，无图像共享）：

- pan-board/latest-user-zone-faster-live.json 线内0PWM
- pan-board/latest-chosen-right-zone-gated-trial.json 16ACK/区域恢复
- pan-board/latest-ui-anomaly-private.json 覆盖错误
- pan-board/latest-corrected-zone-visible-private.json 修复后截图
- pan-board/latest-final-face-zone-ui.json 257pins/25样本
- pan-board/latest-identity-current-after-zone.json 原故障记录

注意：GUI当前桥仍硬编码10秒及15秒子进程timeout，尚非持续随动。新consumer增加zone-authorization明确新范围，兼容旧bridge confirmation token。native新release必须正常stop/fresh checkpoint后同boot承接，GUI可保持。

UTC06:49更新（前面状态为历史）：

- 身份可用性已修复：camera153151，SFace/YuNet RUNNING，identity.ready=true/error空。原故障3/7未减，实际新恢复后SFace attempts/recoveries3/3，YuNet7/7；SFace3个合成零输入健康探针实际7.6～7.8ms，同SHA输出，无身份匹配/姓名/真人精度验收。YuNet使用当前自然帧3个有效probe恢复DPU。
- 新原生库/outer hook位于OPS/pan-face-edge-v5/native-operator-v1。原始源码来自schedule-integration，与当前旧lib源SHA相符。新增显式API：仅budget latch/旧两次尝试均自然过600s/无active/pending/fence/当前primary连续健康30s且实际200进度；原faults/attempts/recoveries/timestamps保持，只切cooldown10s再3探针。原30ms cap与5ms guard不变。现线程仅在C optional调用周围FIFO10，finally恢复原调度。
- 新libSHA704f561a50b5f0fb8f9b4cf72c024acce0cdafd888cad0784507f484518fc224；unit7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32。新entry0576a388…，runtime manifest74e011db…；24个z dropin aura-identity-operator-v1.conf已活动。原meta/config/Python闭包保持，通过hook明确ABI兼容迁移，先按旧unit验证exact seed，再写新unit；不是修改checkpoint冒充原样恢复。
- 受控正常stop camera66241，fresh checkpoint的boot/PID/birth/quiescent/ZOCL0核验后同boot启新entry。所有计数原样承接；启动新primary overrun1（18→19）已记录，不归因RT，之后30s稳定保护才允许请求。旧boot4→1断档仍保留。回退必须先正常stop/fresh新CP，再用native_entry_rollback.py显式兼容新unit回旧lib；不能直接删dropin后启动旧unit。
- old手动返回当前1476us flags0/lease0/epoch11/ack16不变；257pins、25样本视频可见，无运动输出。
- 已通过20组旧策略、5组C ABI、8组新API守卫及ASAN/UBSAN、7项Python RT/迁移检查。板端link+ABI不创建context/模型/作业，窗口0新超限；恢复才运行实际作业。源和过滤证据已共享IDENTITY_OPERATOR_VERIFICATION.json，无原图/身份内容。
- 当前正在激活持续跟随基础版continuous_v1，尚未加入速度反馈/中值（严格按用户顺序）。14项本地session/所有权/只读receipt检查通过；10秒单段上限、1425..1505、24..40us/s/80ms，监测常驻、回区STOP后可等下一轮，丢脸STOP后重新确认真实新帧，硬件/协议fault不自动重启。
- 连续版左线用脸框接触实际图像左端2px触发（脸中心完整可见时不可能为0）；右线仍按用户蓝点/脸中心与80.647%线。真实左触边效果待用户醒后验收。
- 连续版已传输F/continuous-v1，consumer manifest01f117448b79ef214bda1e14809feedaaac00e1e0ef070c6b09e7d54bbbd2828。新GUI proxy用主窗内toolbar x604,520提供开始/停止，不再独立TOPLEVEL；runtime SHA已更新257项，启动预检及旧已停止readback继承验证通过。
- 当前GUI正在restart，camera153151保持。旧GUI76450/GTK76636停止，startup可能需要TIME_WAIT70s+显示配置，勿提前宣称失败/反复restart。独立检查脚本check_continuous_gui_v1.py。后台restart tool已完成或需读latest-continuous-gui-restart.json。等API READY后恢复方向sign+1、pagevision、截小JPEG核验工具栏和线/脸框，再做无脸0PWM连续观察与停止恢复READY。
- 当前主GUI仍路径N=R/gui-face-edge-v5，3个修改文件backups在N/continuous-v1-before。新的follow_readback.py支持当前consumer及显式stopped_readback_predecessors哈希清单，因此当前1476超出旧manual1425..1445仍能验证原v3r2报告，只授予读取，手动点动范围不扩大。
- 下一步先完成连续版板验（无用户不用伪造物理结果），然后再独立continuous_v2加入3/5帧中值、实际新图像速度反馈、加速度/速度/步长约束，不能预判越线前转动。完成软件/回放/板端无脸长稳，保持最终STOP供用户回来验收。
