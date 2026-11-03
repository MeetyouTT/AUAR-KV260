# 2026-10-17 摄像头固定身份与拔插恢复

用户反馈摄像头拔线重插后不能使用，要求固定摄像头位置。按设备身份定位和自动重连处理，并部署到当前KV260。开工重新查阅资料包README、B执行手册相机断连恢复要求、当前规则及当天实测。

## 修复前实测

UTC11:09，同一boot `25c4401f-471d-4383-8159-03b8bcaf480b`，摄像头重新出现于USB `1-1.3`（此前为 `1-1.2`），HD 720P Webcam、VID/PID `0c45:6341`、序列号 `20130901`，采集索引0、元数据索引1；系统已生成稳定by-id链接。相机服务再次failed、NRestarts=7。不能把/dev/video编号变化当作本次已证实的唯一原因；原代码写死video0及启动限流均影响重连。

## 实际修改与部署

默认配置改为 `/dev/v4l/by-id/usb-HD_720P_Webcam_HD_720P_Webcam_20130901-video-index0`。新增设备校验，每次启动核对USB身份、字符设备和索引0后再打开当次videoN。元数据节点、错误身份与普通文件拒绝，设备缺失不悄悄切换其他相机。缺相机时在加载DPU之前退出，避免无设备仍重复运行模型自检；相机代次每次重启更新。

服务 `StartLimitIntervalSec=0`、`Restart=on-failure`、`RestartSec=3`，取消原90秒/3次停止重试。修正别名路径的占用检查。保留旧CPU/IoU配置的显式video0兼容入口，默认运行配置使用稳定身份。

发布 `f4459770ade95f0e`，6个板端目标文件（模块、服务程序、配置、发布unit、安装unit、新增测试）实际SHA核对后原子替换；部署前与主机原件一致，板端备份到 `/home/root/aura-camera-hotplug-20261017/release-f4459770ade95f0e/backup/`，失败回滚机制就绪，本轮没有触发回滚。仅重启相机，GUI PID1357保持active；未操作FPGA、运动、音频或整板重启。

## 验证

主机45项、板端45项全部通过，无跳过。初轮主机默认Python缺NumPy导致12项跳过，切换现有NumPy环境后完整45项通过。7个新增测试覆盖videoN变化、设备缺失/悬空链接、元数据、错误USB身份、普通文件、禁止静默回退及别名所有权。

板端已实际解析服务属性：StartLimitIntervalUSec=0、RestartUSec=3s、Restart=on-failure。主机systemd语法检查返回0，主机无关单元/Varlink告警保留，不用其代替板端属性实测。

受控软件拔插：只对身份匹配的摄像头 `1-1.3/authorized` 写0，等待14秒后在finally中恢复1。缺设备期间稳定链接消失、GUI frame_visible=false/link=OFFLINE，服务NRestarts=3且仍auto-restart；恢复后自动运行PID8458、NRestarts=4，采集5→30、检测4→24帧，三类错误为空，GUI READY/可见，PID1357保持。新旧camera_epoch不同，旧图请求404，未复用旧画面或轨迹。该测试是USB逻辑断开/重连，不能写作人工拔插线已验收。

已请用户做一次真实线缆拔插，尚待回复；冷启动、长稳、USB hub整体掉线恢复未新增验收。

后续30秒31次只读采样均在线、三类错误为空，采集594→974（+380）、检测474→775（+301），同一PID8458/相机代次，界面READY/可见。6个已部署目标SHA独立回读一致。观察证据 `20261017T111800.923205Z/watch_camera_hotplug.json`；最终截图 `20261017T111924.990828Z/screen.jpg` 已回读查看。观察期间没有人工拔插完成反馈，也未看到相机换代，不追加实物拔插通过结论。

## 工件与限制

主机工作目录 `/home/ghmd/aura-camera-hotplug-20261017/`，含备份、独立修复ZIP、manifest、部署脚本、报告及validation。部署证据 `evidence/20261017T111414.446398Z/`，21份响应；软件拔插证据 `/home/ghmd/kv260-display-check-20261017/evidence/20261017T111650.775138Z/`。传输SHA、ZIP与6载荷哈希回读均通过，串口回显恢复。

主仓修改见 [交付报告](/home/ghmd/aura-camera-hotplug-20261017/REPORT.md)。完整运行包收集发现既有 `docs/BOARD_ASR.md` 缺失，未擅自补写或重建整包；这不影响已核验的独立相机修复包。全部源码改动前保留原件，仓库目录没有Git元数据，未声称提交或推送。
