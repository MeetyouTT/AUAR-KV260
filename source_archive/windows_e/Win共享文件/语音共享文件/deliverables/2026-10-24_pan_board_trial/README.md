# 转轴VSRV/2已上板：共存、有限指令与停止通过，实物反馈待确认

**UTC03:34最新：当前boot已重载VSRV/2联合固件，手动面板READY；本boot20µs往返也已获用户确认、最终STOP。** [当前结果](../2026-10-24_pan_follow_shadow/CURRENT_BOOT_RESTORED.md)。下方官方固件/FAULT说明是本次恢复之前的记录。

**当前冷boot状态更新：** 以下为boot1236…的历史联合固件/有限动作证据。当前boot463c…加载官方`kv260-benchmark-b4096.bit.bin`，VSRV/2未恢复，manual backend正确拒绝上下文并显示FAULT。视觉只读stream已在camera17671/GUI1307通过完整10秒shadow；实际方向/机构/实体随动未验。[最新状态](../2026-10-24_pan_follow_shadow/STREAM_V2_REPORT.md)。

**最新20µs重复：** 继此前用户确认看到了20µs往返后，应用户“再试一次”再执行一次1425→1445→1425µs、2秒、44 ACK；epoch3，最终flags0/lease0、输出关闭，相机PID8272不变，primary/optional新增超限与gap均0。本次这一次的肉眼反馈待确认；不影响此前已确认的那次往返。结果见[evidence/observed-20us-summary-03.json](evidence/observed-20us-summary-03.json)。

**当前boot `1236ccf4…`，v2联合固件已加载，原生r4与GUI保留。** 已执行一次2秒小步台架，1420→1425µs、44次连续ACK；正常完整结束及最终STOP均通过，当前flags0/lease0、输出关闭。用户尚未回报是否看到转动与停稳，不能把指令回读当成机械效果通过。

[当前状态](PROGRESS.json) · [最终实板审计](evidence/final-board-audit.json) · [共存与停止结果](evidence/trial-accepted-stopped.json) · [离线固件与报告](../2026-10-23_pan_joint_firmware/README.md)

| 已实际完成 | 结果 |
|---|---|
| v2身份/停止 | ID `0x56535256`、ABI2、build `0x778d2512`及STOP通过 |
| 原生r4共存62.651秒 | YOLO9.94396Hz；YuNet220/SFace95次新native完成；新增optional/primary超限、gap均0 |
| 有限台架 | 1420µs初始化试验点1秒、1425µs1秒；44 ACK，最后事件1988.53ms |
| 最终寄存器 | width/target1425、epoch1、ACK44、flags0/lease0、active/armed均false |
| 源与数据保持 | 222相机源、原生库、GUI入口及251项component pins、原unit/drop-in、配置与身份库SHA核对通过 |
| 当前业务 | camera8272、GUI8299、Xserver1076；原生r4/身份/worker正常，GUI IDLE/IDLE_READY |
| 清理 | 第二轮activation成功退出；guard timer/service inactive；第一轮失败日志及实际回退均保留 |

累计主周期超限4含本轮多次正常启动，完整保留；窗口4→4无新增，不能称整个维护全程零超时。之前启动域的YuNet故障/恢复沿原检查点归档链保留。没有改30ms/5ms保护、身份阈值、数据库或监听偏好。

## 第一轮失败与恢复

首次加载v2后ID/STOP过，但维护控制器只等GUI70秒，短于其90秒display＋90秒ready宽限，验收拒绝。第一次回退又遇GUI接口尚未启动而停在RECOVERY_HOLD；未强杀原生owner。扩展等待后，实际恢复官方固件及相同原生r4/GUI，恢复程序success退出，原guard停用。第二轮只修维护等待为210秒，新增“95秒就绪”和“始终不就绪”检查通过，固件与业务源不变。第一轮没有被追认为接受。

末次审计脚本曾误用GUI启动包装器的SHA检查GTK主文件，正确拒绝；已按原launcher的实际校验对象修正并通过。真实包装器和主文件component pin均保持，失败记录单列。

## 先前断连与传输

前一boot c5f247b9…完成只读预检后，UART曾三次0字节回包，未传候选/停服务/发动作。用户给转轴上电后通信恢复且boot变为1236ccf4…，旧上下文已归档，CID/FDT/服务/owner重新核对，新FDT与候选覆盖在本机合并通过。

差分基于板内同SHA旧v1，gzip213800B，板端重建7807932B目标整文件SHA正确；第二轮成套包287935B，0传输重试。一次控制器上传因上一重建仍占UART被互斥保护拒绝，等待后串行重传，无任务命令重叠。原始UART、FDT及生产元数据仅留本机私有目录；共享只含代码和过滤数值。

## 当前GUI接入状态与限制

GUI手动转轴控件已接入窄范围VSRV/2适配器并在板端运行，允许用户直接点击控制；范围限定1425～1445µs，支持5/20µs步进，程序化/积压命令被拒绝。接入候选及交付见[GUI交付目录](../2026-10-24_pan_ui_v2/PROGRESS.json)。本次没有再点GUI控件，台架试步仍由受限控制器执行。没有只改旧boot字段绕过保护，也没有制造QUALIFIED发布清单。外部波形未测、机械参考/方向未标定、自动跟随未启用。

当前v2是本次启动的活动应用，下次冷启是否仍加载v2尚未复验。下一步按用户对最新一轮的观察更新记录；若继续机械核对，仍限于用户明确授权的小步实测。后续部署保留原生r4、当前VART应用及持久历史，不能用旧相机/GUI整包回退覆盖。

板端墙钟仍为2021年，事件关联采用boot/PID、单调时间及宿主UTC，不将板端墙钟当真实日期。本轮未修改系统时间；Windows同步接收未代确认。
