# 与YOLO、YuNet和SFace共存的恢复顺序

这是供主窗口审查的恢复方案，只有只读纠正包可直接用于下一轮诊断。当前没有写设备的执行器，也没有生成已放行的运动绑定。v24、PAUSED、原动画窗口、板端业务/存储与Windows仅27B/OmniVoice的归属不变，不添加Qwen视觉模型。

## 已有条件与未成立条件

最新只读回执确认：加载benchmark/VART benchmark；wide四个文件已在盘上匹配；独立控制器25项、GUI before和手动payload已匹配；boot/FDT/方向绑定不符；实体停止参考未知。只读探针三条路径已纠正，正确driver目录尚待主窗口复读。

因此恢复不是重新下载模型或只开跟随开关。需要分开完成平台共存、相机owner承接、当前启动机械资格和用户随动验证。标称B4096及源码中的DPU fingerprint一致只是必要条件，不代替当前模型/端口/调度和实物验证。

## 阶段与主窗口的停止条件

| 阶段 | 主窗口准备/检查 | 通过门槛 | 不通过时 |
| --- | --- | --- | --- |
| A，只读补齐 | 执行V2固定policy；核对有效相机argv/配置/Native源码闭包、模型和图库配置来源 | 正确`release/driver`三项匹配；当前相机owner/source pins有新鲜依据 | 保持follow=false/FAULT，不改绑定来满足校验 |
| B，冻结现场与回退材料 | 保存当前v24 startup/380组件映射、GUI配置、监听偏好、当前camera owner及benchmark回退路径/指纹 | 全部绑定同一现场上下文；无登记/模板更新或播放/采集 | 不进入平台切换；不改原记忆或动画组件 |
| C，正常释放视觉owner | 由既有受控相机流程停止采集和worker、关闭YuNet/SFace runner，取得最终静止Native checkpoint | YOLO worker确认退出、身份worker/aux runner完成、无未确认native completion，最终检查点SHA及source PID/birth等齐全 | 保留fence/保护状态；禁止强制清锁、改marker或伪造新seed |
| D，成套平台恢复 | 已确认没有活动DPU用户后，由主窗口既有加载流程成套处理wide bit/DTBO/XCLBIN/VART并核对当前FDT | 实际wide/operating、精确wide VART、成套指纹及当前DT上下文通过 | 不新开runner或运动；仅使用已审查的回退流程 |
| E，恢复原相机服务 | 用实际C阶段最终检查点及原受控入口恢复原模型/来源，核对YOLO primary、YuNet与SFace可用性 | 只存在一个相机owner；源帧推进、无新fence/异常，独立阶段计数合理；SFace模型/图库与0.85保持 | 保持运动关闭；不因ready缺失清除历史计数或降低阈值 |
| F，重新绑定业务读回 | 新相机PID/birth/服务或camera epoch变化后，使用主窗口既有同boot证据链和正常发布事务承接face readback | 新旧owner、checkpoint/恢复回执和相同原图库模型可对应；新source pins生效 | 原身份/个人权限校验继续拒绝，不能只写新PID或boot绕过 |
| G，建立本次机械资格 | 保持无主动跟随，核对驱动及同boot停止状态/STOP、实际安装/方向和当前位置连续性证据 | 当前输出关闭/lease0及本次位置参考可证明；本次范围/方向/随轴安装有依据 | 不用重载1500或旧wide READY当实物参考，保持FAULT |
| H，新R2发布与联测 | 以当前v24基线派生新独立控制器完整26项清单与GUI/必要配置，保留原业务及动画 | 前后SHA、停止收据和当前启动资格完整，随后由主窗口安排显式新会话测试 | 不改冻结旧清单，不恢复旧动作或自动开启监听 |

阶段C/D/E/F/G都涉及主窗口保留的设备/服务串行权，本窗口没有执行，也不由本文件直接调用。

## Native检查点必须保留什么

已核查的`native_startup.shutdown()`只允许在相机/身份worker join、runner关闭后工作；它要求完整最终SFace特征计数，随后从Native owner取得checkpoint/snapshot，并带上source unit、SFace计数、YuNet/SFace各自恢复历史及前一内核归档链。`ui_camera_service`在YOLO worker仍存活时会拒绝检查点，身份关闭不完整也必须保留owner。

本次health投影仅含少量计数，缺少pending token、inflight/lease、完整辅助恢复状态等，**不能用于构造或修补checkpoint**。同boot承接不能换成isolated maintenance seed，不能把累计primary overrun5清为0；若后来确实重启，应按已有新内核入口另开计数域并归档前驱，而非改旧boot字段。

上述实现依据仍来自已保存相机源码快照，切换前需要当前相机源闭包的新鲜核对；本次GUI/控制器文件MATCH不能代替独立相机源码闭包证明。

## 三套代码根必须分清

1. 当前业务GUI运行树承载v24、记忆与角色动画。R2只改视觉/转轴层，不用旧gui-wide-v1整包覆盖当前运行树。
2. 独立控制器root现有25项已经本次核对；R2替换会话文件、增加匿名锁模块后为26项，其他24项原字节保留，另建完整新清单。
3. `validated_context`的返回值是**固件release下的driver目录**，不是manifest同目录。实际搜索路径插入顺序为控制器root、`release/driver`、app-root；顶层`vsrv_driver/vsrv_transport`与GUI的`board.motion.*`必须分别核对。手动release又有自己的三份payload，本次已单独MATCH。

`pan_manual`的有效face配置、face配置中的context/app-root/方向/人工证据/zone-settings以及manual release均需成套审阅。app-root应派生自当前受控基线，不能沿用旧5515目录就宣称保留当前业务。需要变更的配置由主窗口正常事务发布，不预填本次未验证的boot/FDT/位置或方向。

## 先恢复识别取样，再证明随动效果

运动关闭时先核对新相机owner、源帧/源龄和YOLO、YuNet、SFace独立计数。继续使用本地128维SFace及原0.85身份阈值、图库版本/来源与TTL，不新增模型、改模板或把人脸框当身份。ready只表示后端可用；本次0.244秒窗口内identity_processed不增长不构成准确率结论。

主动随动的最小联测数据应同时记录两个互不等同的生命周期：

- 匿名运动：实际像素源/检测锚是否新鲜、同track/generation是否稳定、是否确实ARM后新图、丢脸停止/换目标需新会话、边界回正与STOP计数。
- 身份结果：原识别目标和图库版本、源帧与源龄是否有效、KNOWN/UNKNOWN/ERROR状态与0.85保持；不导出姓名、person_id、模板或图像。

运动键可在像素连续性证明下跨检测键抖动保留，不必逐字等于身份检测键；二者都不能充当说话者认证或个人记忆授权。未标定声纹仍受原限制。

登记/更新模板先在停止跟随后单独进行。源码中手动`before_move()`检查ENROLLING/SAMPLING两个状态，但实际登记还使用`enrollment_sampling.stage`；自动跟随入口也不能由这个手动检查推定为完整互斥。若未来要求登记时同时跟随，应另审原登记FSM和运动提交的互斥，不能把本轮恢复验证扩展到该能力。

## 最小联测场景与报告边界

主窗口在G/H资格成立后统一安排：单脸在画面中部保持、左右越线回正、短遮挡/离开、第二人进入或更换目标、源重复/断流、专用STOP和子进程退出。保留限位、PL每20ms最多4µs、lease/QUIESCE/STOP及故障保护；实际方向、角度、清晰度、正面姿态和体验由现场验证。

水平居中并不能改变人的侧脸/俯仰，也不能保证无运动模糊。失去目标不自动回中、不沿用旧像素许可、不恢复旧会话；恢复资格或文件MATCH均不表示真实人脸准确率、±90°、扬声器首声、动画物理显示或长期稳定已经验收。
