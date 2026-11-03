# HDMI重新检测失败及首次AUX延时候选

UTC13:35～13:39后续已实读原2022年#1内核运行，boot bec99c5a…，USB/业务恢复；用户仍见条纹后缓慢闪屏，实体修复失败。[最新基线](2026-10-21-HDMI-ORIGINAL-BASELINE.md)更新下方待人工开机状态；候选失败事实保持。

最后被动观察180秒未收到新开机数据或root提示，未向U-Boot发送输入，已关闭本机UART。原内核启动选择已经恢复，但运行状态仍等待现场12V重新接通后复核；不能称整机已恢复。候选归档48份内容哈希复核通过，物理修复状态仍为失败/未完成。主机终端设置已由端口关闭流程还原；启动阶段没有Linux回显恢复命令可执行，因此观察结果中的console_echo_restored=false不作业务验证成功解释。

2026-10-21 UTC13:14～13:22更新：首次AUX延时候选软件重启曾通过（EDID128、5.11581秒、实际相机/检测正常），用户自行断电后新boot e93b105e…黑屏，USB hub/触摸/MCP01/相机约60秒后整体掉线，相机/界面未就绪，冷启动验收失败。已受校验回退uEnv至原Image选择，保留较新audio-frontend业务入口；随后的软重启串口停U-Boot早期，尚未确认原内核运行，已请求现场12V断电待灯灭5秒后接回、HDMI不动。当前被动观察，无bootloader输入/QSPI写入/运动。[完整实施、失败和回退证据](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_hdmi_preinit_candidate/README.md)。

2026-10-21修复执行中：DRM status detect已单次执行，EDID前后仍0，用户反馈仍黑闪；标准DP AUX DDC读取返回Remote I/O error。首次AUX注册前等待候选已完成完整Image构建、13085导出符号集合保持，正在通过带校验串口暂存，尚未替换活动内核或重启。[候选、回退与阶段状态](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_hdmi_preinit_candidate/README.md)，[单次检测失败证据](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_hdmi_redetect_once/README.md)。

单次写detect7字节约0.068秒完成、退出0；立即与3秒后EDID仍0，GUI1063/相机1002/Xserver1062及六配置SHA保持，无模式设置、重启或运动。额外DDC读取仅在已核实适配器2向EDID地址0x50设置偏移0并读128字节，返回Remote I/O error；不是分配器寄存器写入或系统I2C扫描。

原理图来源核查发现名为xtp682-official.zip的历史文件实际是HTML，不能解压；改读历史镜像kv260_b03.pdf（图号038-05058-01/RevB03），渲染第10页确认RESETN关联PS_POR_B、HDMI控制由分配器GPIO承担；实物修订版未核实，不据此控制GPIO。厂商接口协议不足，未写未知寄存器。

首次通信延时实现为DP probe中PHY初始化后、AUX注册前一次等待，可配置0～10000ms，默认0，本候选5000；不是所有HDMI线路从接电起静默5秒，也不阻止分配器自主动下游通信。

源码和历史构建独立复制到/home/ghmd/aura-hdmi-preinit-20261021/d977bdda5e7c9877。DP目标编译/完整Image均退出0；checkpatch最初误用Python执行Perl脚本，已纠正，代码检查0错误/0警告（忽略提交元数据）；补丁干运行通过。Image SHA8bfafe01…，27089408字节；配置与历史构建完全相同，和实际config仅编译器名称文本差异。13085导出符号集合保持，不能代替实板模块/推理验收。

网络单端点读取和路由查询均Network is unreachable；未改网络，临时HTTP服务已退出。候选通过既有校验协议暂存，接收端20秒空闲超时恢复终端速度，保留原内核。最终安装/启动/实屏结果待阶段补记；不将进行中状态称为已修复。
