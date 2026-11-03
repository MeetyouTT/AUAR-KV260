# 摄像头画面消失：完整界面与进程审查

## 用户明确的故障及实际定位

用户补充“就是摄像头画面没有了”，要求整个界面、卡进程和冲突审查。此前10:40的1410µs左20步长越界诊断仅能解释左按钮灰，不能解释摄像头；本轮重新读ZIP入口、项目/共享规则和最新记录，从现场证据核查。

UTC10:50采集4个连续样本：相机106060、capture约12.5Hz、DPU detection9.93Hz、epochs不变、错误为空；GUI206098/API持续更新、队列0、手动READY/1415/epoch31/ACK41/flags0/lease0。一次UI.frame_visible=false但sink仍11.73Hz，其余true。实际1024×600屏幕中调轴模态窗遮挡预览，收起后400×300相机区域残留原弹窗内容；随后32个样本全部true且sink持续送帧，残影仍在。新开的独立放大预览能显示真实相机图像，定位到原native预览窗口恢复。不能以unit active、HTTP可用或sink入口计数宣称画面正常。

实际GTK在帧龄超过250ms时set_visible(false)使DrawingArea unmap；恢复map后同XID命中preview_bindings缓存，跳过重新attach。源帧新鲜度与控件生命周期耦合使显示不能恢复。另发现原pan弹窗按钮注册在主controls，save_evidence却跨顶层窗口translate_coordinates后直接索引，存在None错误路径。本轮不把这一静态错误路径编造成已发生的相机根因。

## 全栈占用和版本核对

4核CPU的2秒差分：GUI194.20%、相机107.94%、音频15.22%、Xorg11.99%、独立转轴7.38%，约3.4核；load6.47/6.30/6.08。内存可用2966MiB、/run可用775MiB、根分区剩余20GiB，无内存耗尽迹象。CPU繁忙属实，不能声称余量充足。设备所有者：相机仅106060（同进程两份video0 fd），独立转轴207278持Native锁，音频206158唯一pcmC1D0p，Xorg拥有card0、相机DPU拥有renderD128；没有第二相机/重复GUI抢占的证据。GUI和相机NRestarts=0，当前运行日志无Traceback/Error/critical。采样期间无epoch变化/USB离线/OOM证据，不能泛化为所有历史故障已排除。

UI本机服务link READY、pending_count0、phaseIDLE，免点击对话PAUSED/enabled=false且无错误，录音IDLE。这是暂停状态，不是后台录音死锁。UI语音主机待接入，Windows回执仍未填写；未新发起ASR/27B/TTS业务，不能升级为Windows语音或身份准确率验收。GUI与相机来自不同已知候选目录但协议/boot/epoch匹配，是当前分工的实际部署；共享GTK比板端旧，不能整文件覆盖较新voice-barge-in/native版本。

## 改动和主机验证

共享tools/board_avatar_gtk.py只改两处原生预览逻辑：保持DrawingArea本身visible，新鲜度只控制占位/问图/过期清屏；每次map无条件重新attach本命名sink，detach旧实例，避免同XID缓存。源250ms、过期黑帧、问图及运动门槛保留。实际板端从a4b64d02…源码另生成相同两处补丁，未灌入共享旧GTK。

tools/pan_controls.py把原模态窗改为右侧423×516以内的同窗口面板，保留左/右/停/20/5/互换/重连；离页、返回、退出STOP；关闭后移除controls引用。新增pan_close便于可复核的UI关闭，manual控制/驱动/租约未改。docs/BOARD_PAN_MANUAL.md同步流程和版本合入说明。

347项主机完整回归全部通过。真实GTK/GStreamer/X11合成像素集成测试14次实际屏幕检查通过：过期黑屏、恢复、5次同XID切页重绑、3次面板开关、布局/坐标/假硬件细调和互换；旧GTK同测试在过期帧导致canvas unmap处失败。主机没有实体运动。初次测试脚本用Python3.8不支持的ast.unparse，在启动前失败，改用AST属性匹配后完成验证；首次暂存调用相对__file__路径断言失败，UART未连接，改用绝对脚本入口后成功。这些没有算作板测通过。

## 实板安装和验证（UTC11:02～11:06）

新camera-fix-v3目录暂存、SHA核对后单次激活。完整238项旧启动清单、精确boot/入口/空闲/输出关闭通过；只重启UI一次，没有回滚、没有重启相机。新监督225296、转轴225369，startup指向camera-fix-v3，仍是现场voice-barge-in/667b70d586ca runtime。新GTK SHA21b15787bda2abad4ee8064dd76365506bde627db8aa5e5e5332cc54343a2ee9，pan_controls SHA3fe32d5cf02b93a18d11bdcd273d6af642eff07e4578f4e38161094e97fb0d89。原230项核心中229逐字节保持，新238项SHA全部匹配，原生库/语音/身份/相机配置保留。HDMI每boot off2秒及同boot标记保持。

实屏确认左侧实时画面恢复、右侧调轴不遮挡；按钮x605/742/879，125×64，均在右栏，窗口无模态dialog。实际保存诊断COMPLETE/errors空，证实坐标路径可用。屏幕400×300区域与同时原始源帧缩小后的RGB平均绝对差5.061/255，并私有查看真实图像；不把帧计数当作实屏验收。真实照片不进共享目录。

两次实际关闭调轴→交流→视觉→打开调轴均ACK成功，实际屏幕/源帧平均差2.067、2.057，最终2.594/255。持续20秒40API样本、无link/preview错误，39次新鲜、38个不同源帧，序列前进；1次原250ms截止清屏后自动恢复。最大采样tick149.14ms，不能称零掉帧、CPU问题已消失或长稳通过。

运动命令发出0，始终1415µs、flags0/lease0/epoch31/ACK41、history空。未中位标定/自动跟随。后段面板读回已关闭，尝试恢复旧5µs偏好的脚本在UI动作前检查退出，未点击/改偏好/发运动；未为了测试反复覆盖现场页面。若重新打开默认普通20，1415左目标1395越界会灰，选5即可继续合法左调，这仍是范围规则。

## 交付和限制

新共享[审查/修复交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_camera_preview_pan_audit/README.md)保存过滤审查/部署/实屏数值/切页记录、两份修复源码、两处补丁、347结果及合成像素截图，32份内容清单SHA/长度复核通过（不含清单自身）。私有UART、真实相机/全屏、人像/身份库和模型不共享。共享入口、Ubuntu回执、导航更新；Windows回执保持，不把文件交付写成对端执行。后续Windows只合入相同显示修改，保留较新语音基线、manual_process入口、2秒HDMI和准确清单。

当前修复完成并有实屏证据；CPU尾部压力、真实冷启动/断电显示、人为反复拔插与长时间运行、Windows新语音业务、机械中位和完整跟随仍分别待验收。没有通过放宽250ms源期限或100ms硬件租约凑通过。
