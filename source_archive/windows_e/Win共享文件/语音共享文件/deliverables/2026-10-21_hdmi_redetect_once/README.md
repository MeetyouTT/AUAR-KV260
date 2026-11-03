# HDMI单次重新检测：已执行，未恢复

用户授权开始修复后，在同一故障boot5cd17bb7-30da-4a4f-bf18-8167508de1f4执行一次DRM status detect；用户随后反馈“仍然黑闪”。本次重新检测未能替代物理HDMI拔插，不加入开机流程。

## 实际操作与结果

- 守卫核对板卡CID、boot、5秒参数、三服务active、DP-1 connected/enabled/On、EDID为0；force为unspecified、没有EDID覆盖。
- 唯一写入动作：向 `/sys/class/drm/card0-DP-1/status` 写入 `detect\n`，7字节，驱动返回成功，写入耗时约0.068秒。
- 检测前、立即后、3秒后EDID均0字节；当前输出始终1024×600/59.85Hz。没有关闭输出、提交新模式或重复检测。
- GUI1063、相机1002、Xserver1062前后PID/active/NRestarts0保持；人物帧推进，UI IDLE/error空。六份启动/业务配置SHA保持。
- `/run/aura-hdmi-redetect-once-<boot>/`保留before/result，目录排他创建防止同boot重复执行；写入子进程超时12秒后停止后续DRM读取。本次没有超时。

追加一次标准EDID读取：已确认I2C适配器2名称为ZynqMP DP AUX，仅针对DDC地址0x50设置EDID偏移0再读128字节。返回Remote I/O error、耗时0.034秒，sysfs仍0、三服务保持。该操作包含标准读事务所需的偏移指针设置，不是扫描总线、写分配器配置寄存器或操作系统I2C总线1；并未取得有效EDID。它支持判断当前不是单纯的界面缓存问题，不能单独据此确定硬件损坏。

## 后续推进

已进入[首次AUX注册前等待候选](../2026-10-21_hdmi_preinit_candidate/README.md)的离线构建，现有内核、uEnv和实际运行状态在此阶段保持。本次只证明重新检测失败，不代表新驱动方案已通过。

原理图资料核查：原先名为xtp682-official.zip的本地文件实际是HTML页面，无法解压；改用同目录kv260_b03.pdf渲染第10页及读取第11/12页。该PDF为Xilinx原图的历史镜像副本，图号038-05058-01/RevB03，本板物理修订号尚未现场确认。图中分配器RESETN经Q22关联PS_POR_B；HDMI OE/DDC/供电控制由分配器自己的GPIO负责。不能将这些GPIO当作PS可直接控制的独立复位脚，也没有据此写入任何寄存器。

板卡至Ubuntu候选文件端点检查返回Network is unreachable，路由查询亦无路由。只运行了读取可达性探针，未改网络；临时HTTP服务已关闭，后续考虑既有带校验串口传输或Windows共享交接。

共享src保留单次检测助手，evidence保留过滤JSON/来源与实屏回执；原始串口日志留本机。没有服务/系统重启、运动指令或永久恢复任务。Windows同步未确认。
