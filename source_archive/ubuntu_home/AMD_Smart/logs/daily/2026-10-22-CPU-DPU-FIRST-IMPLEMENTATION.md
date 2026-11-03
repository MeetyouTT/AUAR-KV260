# CPU / DPU 第一批实施

2026-10-22。用户授权开始并行Codex。重新查阅ZIP入口、最新统筹计划、共享入口/双方回执/工作约定以及实板源码与冻结候选。主任务独占UART负责T2/T3，另一个sface_calibration agent负责独立RAM标定候选；首次agent请求遇模型容量错误，已重试恢复，不影响板卡操作。

实际只读复核当前YuNet根/6源码/模型/manifest/unitSHA/原库路径，UI131932和Xserver1077保持、相机165277持续推进、影子为空、统计关闭与timerinactive。YuNet新进程累计估计偏差2、最大29.6328ms、0真正超限，独立于原30分钟22.0694ms证据。镜头前1脸、UI IDLE/录音IDLE/输出IDLE_READY。长测使用旧冻结6源码及新隔离部署脚本，30ms保护不放宽；6项覆盖/计数差/门槛/回退语法本地检查通过，helper SHA585f4b521f722c0219c94ecace9dd82aa18052e9967172eef05d19b5a9564c8e暂存启动准备中。30分钟/100完成/恢复结果尚待实板，最终记录后补。

本轮不覆盖Windows源码/回执或旧冻结交付，不改语音模型/显示/运动/位流；人脸/向量只在获准候选RAM，原库保持。新任务交付在共享2026-10-22_cpu_dpu_implementation，计划状态与实际完成分开记录。

## T3实际失败与受保护恢复

v1 helper585f4b…因假定/etc/systemd/system/xserver-nodm.service存在而在保护路径读取时安全失败，未动相机。修正为systemd FragmentPath实际路径，v2 helper SHA cac8329a111abcbf05eb737fe75b3081a3c2718d1b08dd430cb4f756737bedc5启动隔离影子相机187580。计划1800秒，最后12个快照到55.0308秒，下一检查抛Optional task overrun:sface并自动回退。passed=false/complete=true/rollback_verified=true，回退timer停止、UI131932/Xserver1077保持，原YuNet根恢复相机188288。v2在healthy拒绝前未保留该份失败快照，不能推断SFace超限数值；v3补失败快照/基线告警拒启及6项本地检查，未执行。

最后留存11间隔55.0072秒YOLO9.94415Hz/YuNet2.18153Hz、SFace实际完成20/接受20，平均16.6371ms、上一次累计成功调用最大28.1063ms，实际有效0.36359Hz低于拟议0.5Hz；这些不包括失败瞬间，不是全程或现场身份准确率。原Windows身份配置/库未改，影子决策0/模板写0。报告与CSV在交付evidence中。

之后相机188288的YuNet发生33.1471ms真超限、可选禁用/CPU回退。独立故障快照MCP01 slot4/ep3播放RUNNING/录音closed、1000条内核尾记录均匹配告警，journald重启/高CPU；15.4587秒总CPU93.733%，UI33.59%、相机28.06%、journald11.50%、syslog8.98%、音频5.06%，XRT4.32%。该窗口已是双模型原根、YuNet CPU回退/影子无，不是三模型忙时。无法由现有时间线确定DPU与USB故障的先后/因果，未臆断DDR/供电。

空闲状态正常重启原应用一次，helper SHA c739a9f42637dbcb1818f343f427eb3eb4b20b573e0e1da038db463b48624f7f，改用有界journal读取避免高开销/dev/kmsg逐条观察。before8秒窗口达到5000条上限、只是下界；stopped3秒PCM closed时journal仍到达478旧/新未区分消息，不能写成停流期新警告数。after8.116秒0匹配且窗口未截断，配置/偏好SHA保持，完成与guardinactive已确认。UI主191322，音频worker191451，Xserver1077/相机188288在音频重开期间保持；新出声/录音未验收。保留标准启动器同模式xrandr/DPMS原行为，未手工关开显示。

之后仅重启原相机单元以清除disabled状态，192540恢复DPU YuNet；6源/模型/manifest/unitSHA/原库路径、影子无/timerinactive/CU关闭审计通过。恢复15.168秒CPU55.6238%/XRT5.0000%/190命令；另15.033秒健康窗口YOLO9.97805Hz/实采12.4393Hz、无新匹配告警/无YuNet真正超限，最后保留内核告警距窗口末约489.5秒。只是短窗恢复证据，不称新长稳或根因修复。

## T1/T2软件完成与接续

并行agent交付T1九源码，46项回归（原16＋新30）与8项标准库模拟通过。根任务审查发现初始均值gallery与真实登记frontal_medoid_v1不一致，已要求按真实观测/正面top5/相似度总和及quality挑medoid；3帧及10帧top5与实际sampling源码对照、新camera→quality→ticket→np.float32→RAM链回归通过。模型/阈值绑定、匿名分场次、token/代次/TTL/重放/容量、loopback控制与独立验证均有合约，仍defaultoff/deployment_threshold_validated=false/正式身份未迁。核心SHA23a5c619…，本板纯标准库8项检查实际通过，没有runner/DB或真人特征。

根任务T2三源码计时候选15项检查（统计5/集成5/原runtime5）通过，默认关闭；最近256样本P50/P95与累计均值明确分开，不把YOLO native整体当DPU-only，已说明量化/身份消费等缺口。纯标准库统计在板端模拟通过，不是埋点上线。与T1按handler两行最小合并成11源码，合并46＋10项回归通过；新软件未部署生产。Docker原runtime回归初次缺onnx依赖，复用现有只读python-deps后通过，无网络安装。

用户随后回复“继续”。已转向低开销故障时事件观测：主任务准备有回退短诊断接入，独立agent只改新诊断目录，设计单调wall/thread CPU及VART区间数字事件，原保护保持。原T1包已冻结，不在其上修改。Windows回执/health与微力接收仍未确认。

UTC08:22第一批共享工件校验PASS：标定冻结22项/合并源码11项SHA，52份Python AST、20份JSON、16个本地引用、8行任务、87个父清单工件通过。新增接续诊断说明独立标记待执行，下一轮120秒诊断不等价30分钟验收。原模型/旧实测包未重写。

## 接续完成：120秒分段诊断、延长拒启与恢复顺序

后续215707之前的原相机192540在SFace关闭/近期无USB告警时又YuNet35.923419ms硬上限超限转CPU，guard尚余40.483935ms/waiting0。核验读取mono20444.1秒时，最后保留USB告警mono19146.909935秒，约1297秒之前，journald active/重启24未新增。这说明不能将所有overrun都绑到第三模型或新USB告警；根因仍未知。

新四源码诊断29回归通过、过滤6检查，原30ms/guard保持，双env默认关、同owner/thread-local计时、最多8条纯数字fault。受保护控制器4检查，包684f232b…17919B完整UART暂存，helper161ba854…实板启动相机208402。120.06秒295真实成功wait、YOLO9.92438/YuNet2.44165Hz、CPU55.2604%/相机0.848核，0fault/新增USB告警，自动回退通过相机209792、UI/Xserver当时保持。VART调用wall均值3.3232/最大24.3731ms、调度占用最大24.532/估计偏差1，未真超限；正常trace的threadCPU未保留，不能给其分布或纯硬件结论。最近256分位/累计stage含启动/父子与跨线程重叠均已说明。

600秒helper1c22a77b…仅延长控制器，原四源码不变；因原配置15秒基线新USB告警拒绝启动。没有600秒实测，未装候选单元/未武装回退timer；相机209792依然原根。实时slot4/ep3、journald重启增26等复核证实新警告，原始日志计数受尾窗口限制，非可靠全量频率。当前关联不足以认定相机切换/DDR/OS具体根因。

空闲顺序恢复helpera0572918…：关闭原音频、相机209792→215707（同单元原源）、再重建原音频UI191322→215734/Xserver1077保持。after8.094秒0告警、配置/偏好SHA保持，但旧脚本跨PID累计帧数比较误报最终AssertionError/complete=false。原报告留存；未来f4c6c574…改同PID比较，未执行。独立无生产修改验收按新进程5秒计数差/后端/配置/偏好/告警通过，YOLO9.97Hz，6源/模型/manifest/unitSHA/原库路径保护通过，影子/埋点关闭，timerinactive/CU关闭。未为了修验收再重启应用，不称根因或长期防复发通过。

只读补查Windows8791/8792/8795 TCP均约0.7秒timeout，未发推理数据/改远端；V4L2只读参数30/1/当前可见控制，不改格式、不第二采集，不能从参数推断约12.5Hz原因。现场人员/标签异步询问未收到本轮确认，未采正式标定/登记。

agent只读分析准确分解SFace最后42供给/20完成/22slot拒绝、无替换/producer drop/stale；约0.763/s×47.62%=0.364/s，并非DPU性能上限。同步Windows调用后IdentityService等500ms、worker每次尝试后1000ms有供给/准入节奏约束；650ms是socket timeout非HTTP总deadline，缺逐次时长不可定量归因。未来独立解耦供给、有界重试保持原语义/TTL/保护。

单copy CPU候选仅删capture中间.copy，8项真实callback合约/两版patch临时应用通过，像素/镜像/readonly/内存独立/生命周期/layout/error/metadata/EOS/诊断计数保持，每帧少921600B数组复制为源码事实，CPU/DDR收益未测、未部署。

最新共享2026-10-22_dpu_audio_diagnosis：四源码/29＋6检查/控制器4检查、120秒完整数值、600秒预检拒绝、恢复原始验收错误与独立证明、只读分析、CPU候选。63工件/28份Python AST/18份JSON/8个本地引用校验通过。真实媒体/向量/库/原始UART不共享。当前215707/215734/1077、YOLO＋YuNet DPU/正式SFace仍Windows配置，新增功能均不常驻；下步恢复后持续观察与独立同条件CPU/供给改造，Windows接收/同步未确认。

UTC08:53最终交接再审计：相机215707仍DPU_YUNET_INT8、YuNet真超限0、原单元字节/源/模型/旧库一致，影子无、XRT统计关闭、相关timerinactive。追加final-handoff-audit.json，release/validation引用后64工件SHA全部通过；旧08:51打包核验数字作为该时点保留。
