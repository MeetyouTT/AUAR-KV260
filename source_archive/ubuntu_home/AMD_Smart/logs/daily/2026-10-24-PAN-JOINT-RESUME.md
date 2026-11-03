# 转轴联合固件：中断核对与检查点接续

用户再次要求继续。先读最新共享入口、10月24日HDMI/原生推理日志与本任务记录。另一终端已有新的boot、原生三模型r4和显示诊断；未把昨天的499773/535987或旧回退入口用于本轮板卡。板卡交还及现场观察条件尚未明确，本轮仍不访问串口/SSH/API、MMIO或DPU，不改业务服务/监听/固件/运动。

## 中断的实际情况

本机Vivado进程已不存在，自动收尾进程也不存在；旧STATUS/FINISH-STATUS残留“运行中”。`implement-host.log`最后写入2026-10-23本地08:42:05，停在路由Phase2.4。未生成位流、路由后DCP或XSA。中间值WNS0.000/WHS-0.274ns、1007条未完全布线均不是最终验收。进一步查前次启动journal：08:42:57用户管理器停止，08:42:59进入Shutdown/Power-Off，08:43:00向剩余进程发SIGTERM，记录与构建停止紧邻；关机发起者未确定。前次启动该时间范围无OOM/vivado崩溃匹配，日志未显示RTL错误。本机15:01再次启动。原始过滤关机证据保存在interruption-20261024.json。

保留旧状态及`interruption-20261024.json`，纠正运行状态；源码固定SHA全部复核保持。已完成的布局检查点`source_placed.dcp`为127230603B，SHA `5a8d7c591123ef0fa6382a01b1f3090d99961d36815d7e50d315c4f18aa53887`，可从路由继续，不重做源工程/综合/布局。

## 当前接续

独立本机用户服务`aura-pan-offline-resume-20261024.service`，Nice15、Vivado最多1线程，由`run_resume_20261024.py`顺序执行路由、物理优化、最终时序/DRC、位流和XSA、独立checkpoint审计及打包。服务只操作`/home/ghmd/aura-pan-joint-20261023`，以flock防重复；结束后写FINISH-STATUS。启动后实际active/running已核实，启动不等于实现通过。

已据本机2022.2随工具文档核对DCP打开/硬件导出流程；placed DCP带hwdef。若导出失败，保留结果再处理，不伪造源工程配对。发布报告8项正反例在本轮收尾代码改动后复跑通过；未重复全量软件/RTL。

用户此前明确无测量设备但允许用历史J2.3做小步观察；本轮外部波形仍未测。新的2秒/<=5µs台架工具已准备并有反例验证，但从未执行实体动作。只有当前固件/上下文匹配、板卡交还和现场条件明确后，才安排ID/STOP及有限步进；不自动启用随动或填写QUALIFIED。

## 最终结果：离线联合包完成

UTC13:21:53服务顺序完成路由、位流/XSA、独立Vivado复核及封包，后查inactive/dead、ExecMainStatus0。正式及独立报告一致：WNS0.001ns、WHS0.000ns（报告精度），setup/hold/pulse失败端点0；200476条连线全部布通，布线错误0；总线偏斜余量2.782ns，脉宽余量0.071ns；DRC Error/Critical Warning0，原平台Warning663保留。6输入/2输出外部delay缺口沿用并明确记录，不称外部电气合格。

独立重新打开最终DCP，确认K26、E10/LVCMOS33/DRIVE8/SLOW、FDRE输出初值0、100MHz控制时钟、MMCM及DPU/VCU结构。生成HWH、DCP内hwdef和XSA内HWH逐字节配对。正式资源为66969 LUT、124189寄存器、93.5 BRAM、56 URAM、710 DSP，不把静态资源率当动态忙时或加速倍数。

XSA的include_bit会重新生成位流，头部时间06:09:46与06:12:25不同；设计、器件及7797692字节配置数据完全一致，payload SHA `e5d136c45e88b2dfbea50bba1a35b9c0de3c8f35bcaede1212835f8de613dcb6`。新增6项配对格式/错误器件/配置变更/截断/尾部等检查通过。保留两份原件，采用XSA内确切位流为canonical，经bootgen成包；不是删校验或只换哈希。候选manifest记录原始/采用的位流、XSA、路由DCP、独立报告及复核输入SHA。

共享交付新增`firmware/`和`aura-vsrv2-joint-778d2512-offline.zip`，9055885B，SHA `395b499385d0539c16be32e1e76213467ed70a502461467f0b8033d7f97f15ee`；复制、CRC、逐文件SHA检查通过。既有51软件、3RTL/9场景、真实GTK6、HWH连接13、报告门槛8、新工具14及配对6项分别保留，不混成实板通过。

较新的统筹文件说明另一个终端已暂缓HDMI并只读查明pan为Boot mismatch，仍以单终端管理板卡；本任务已提供完整包和独立回执，不并发接板。当前候选`OFFLINE_VSRV2_BUNDLE_PENDING_BOARD`、deployable=false、board_accessed=false、动作0。当前FDT/成套恢复、固件ID/STOP、原生r4真实共存、有限实体观察/机械参考均待板端窗口；不复用旧GUI/相机回退，不清持久故障记录。Windows接收未确认。

最终共享交付104个内容文件逐项长度/SHA封存，31份Python AST、24份JSON解析及5条Markdown文件链接核对通过，记录`final-verification.json`；未把这些离线检查当作板级动作。构建服务已退出，没有留下本轮后台负载。
