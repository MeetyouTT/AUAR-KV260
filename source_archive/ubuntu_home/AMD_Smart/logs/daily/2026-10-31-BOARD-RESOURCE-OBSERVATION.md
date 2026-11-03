# 当前板卡正常业务资源实测

用户要求检查正常运行时 DPU、CPU、GPU 和内存。先读 ZIP README 和实施方案相关职责、项目规则/索引、最新日志、共享入口及较新 v14 状态，再独占 UART 以当前实读为准。沙箱内串口不可见，首次连接失败后按授权在主机环境连接；用户误发消息中断后，续接确认原命令 exit 0 与 echo 恢复，再继续观察。

主机 UTC2026-10-31 11:24:52–11:25:32 内，连续30.004秒：整板CPU平均78.6484%、一秒峰值96.9773%，四核平均84.3856/75.2035/78.5884/76.4646%，cpu0/2/3各有一秒100%。DPU驱动CU忙时加权6.2666%、峰值8%，598个新完成驱动任务。MemTotal4023988KiB，平均MemTotal−MemAvailable1.4660GiB/38.2015%，最高1.4778GiB/38.5080%，最低可用2.3598GiB，无swap。

开始SPEAKING/playing，结束IDLE/WAITING_SPEECH、麦克风打开、自动聆听true；主页面保持。状态边界YOLO+309/YuNet native+304/SFace+11，detector约9.92Hz、capture/preview约12.49Hz；边界含预热，不直接用这些差除以30秒。主任务累计超限39保持，可选各0。boot8100a7fd、camera260102、GUI887178/supervisor887170；跟随关闭，原机械FAULT保留。

UTC11:39的12.162秒另窗，视觉服务CPU26.9696%、PSS156.639MiB，界面/业务服务至少51.1847%、PSS约1033.916MiB，Xserver2.7956%。GUI主进程21.8511%、音频前端24.6262%、GStreamer音频4.0084%，均按整板100%。界面子进程集变化导致漏短命进程，合计为近似下界，不与30秒主窗合并或作收益比较。XRT memstat_raw24985600bytes/18BO，即23.8281MiB，仅缓冲分配，不等于所有DPU相关内存。

GPU utilization_gp/pp/gp_pp均0，但Mali内存31801344bytes=30.328125MiB。UTC11:40补查约2.073秒，共享IRQ9753303→9753681（+378）、native_yuki_egl sequence51341→51372，证明GPU路径有实际活动，不能报告“GPU未使用/实际0%”。真实忙时百分比未获得，计数原因未定，未调驱动或压测。查询AMD Mali驱动说明仅用于EGL/驱动背景，实际结论以板端metadata为准。

CPU按/proc/stat前八列排除idle/iowait，四核100%；DPU是CU运行时忙时，不是PL静态资源率。内存用MemTotal−MemAvailable，CMA、缓存、GPU/XRT均在同一DRAM内，不能重复相加。CMA末端约631.711MiB已分配，不全属于DPU。温度无可用接口，温度/降频未验证。

五轮固定metadata探针全部exit0、SHA回读完整性及UART echo恢复通过。DPU开始前确认统计计数静止而真实视觉推进；临时统计附45秒独立清理进程，finally关闭后计数静止且视觉继续，清理进程已回收。未新发模型/语音/运动任务、部署/重启/改配置/固件/真实库或清业务计数。源码及私有UART证据在/home/ghmd/aura-resources-observe-20261031/；共享报告/逐秒过滤metadata在/home/ghmd/Win共享文件/协作任务/2026-10-31_板卡资源实测/。Windows同步未核验、未代填回执。

本轮为短时正常业务观察，主要资源压力在CPU；不把DPU低忙时外推为可无条件提频，不将内存余量当语音实时性能保证。GPU可信百分比、长期稳定、持续ASR峰值与全功能并发未验；旧10月29日监听关闭的CPU51.73%仅历史，不作严格收益比较。
