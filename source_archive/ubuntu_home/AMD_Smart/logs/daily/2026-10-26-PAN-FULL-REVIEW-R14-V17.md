# 转轴完整复核与三层修复

承接用户30秒真人试转反馈“依然有问题”、离开约两小时并要求继续全面解决，主端独占UART/板卡，另一路仅本地审查/回归。最新又单独指定一路解决音频USB告警，保持root板端串行，音频另一路不接板。

实测r12/v16：90ACK、59目标变化均−1µs、31保持，1458→1402；事件去重28ARM（12区内预备无PWM）、20horizon/6lease/1submit过期/1人工窗口结束。真实两段首COMMIT6/11ms后width仍旧、target未生效；不能把ACK等同PWM更新/实体角度。输入315独立READY/259接纳，图龄中位77/p95129、锚龄331/p95439，新图间隔79/p95123/max798ms；没有RIGHT有效触发。用户实体仍反馈有问题，本轮不能追认平顺通过。

r14已实际部署：首次PWM最少23ms硬件lease＋既有20ms提交余量/3ms预检；不足无PWM且不累计未执行pva，最终COMMIT前再查实际lease。退出先STOP验证再reader关闭，reader异常不掩盖控制/STOP错误。115主机回归、4paired合成PWM回放过；KV260使用实际ARM轨迹库、Fake PWM完成同4pair＋8shutdown检查，真实运动指令0、完整STOP读回1402不变。manifest d7bdb9576311df8a6e77fbfe1833532e05cd9e286ada30756e5fbf668db0c3dd，23pins；Q09最后native写竞态仍非硬件绝对截止保证。

source-v17已实际部署：直接uint8 BGR resize→LUT/NHWCint8，消除floatblob往返，原模型/guard/owner/输出解码/阈值/fallback不变。69主机回归过；KV26020帧完整Fake native检测对照byte相同，wall中位66.568→26.377ms/线程CPU34.260→15.882，实际DPU0/电机0。23→24NoFace live轮direct_encode wall2.383/CPU1.944、整个process39.884/18.863，为非paired现场窗口，非机械延迟。正常fresh精确owner checkpoint迁移camera673020→720342，GUI未在该阶段重启，故障历史保留。source manifest84d7359f18a5a98aa5dabba967c4ededf5e35d0c43153166fc6998729a30219c、11pins，算法14/协议11保持。

当前joint RTL/HWH/bundle/同boot加载链确认硬限位1400..1600/build0x778d2512。用户机械中位1420只给减脉宽侧20us，最后1402已近限位；不能仅调PS扩大，不能无人回中。稀源220ms时4us/source硬截已合成复现，本轮真实轨迹未触发，不当实体根因。左右边界leftbox≤10%、rightcenter>80.647%、方向+1/手动−1、区内冻结保持。

GUI生命周期v2已部署：读回现役SHA9374b8d3…复现communicate非Timeout异常会遗失活child，纯helper确认子进程退出前不重建manual；不确认保留STOP。审查又复现异常收尾和重复STOP的双reaper窗口，Event先失败后修复。22主机＋KV260实际安装类22隔离过，正常停止GUI647839exit0后751680恢复、camera720342保持、259pins。新controls3ebb1b32…/helperffae5bc2…，布局/视频AST保持。初20s还activating记录STARTING，后READY，不重复kill。两次部署前因瞬间THINKING/WAITING_PCM拒绝，未动服务；等待稳定IDLE后正常执行。

MCP01 xhci slot4ep3告警13:21～13:25复发；前轮一次正常重连不是根治。此次GUI正常重启后末8秒内核0、PCM RUNNING/IDLE_READY/STOP1402恢复，不能提前称长期稳定。原native primary累计27→v17启动28→后续29，optional0/0保持，未清历史。启动7200s只读观察，只记PID/健康/STOP/有界内核，owner变则退出，不具备运动或自动恢复行为；实际时长以采样为准。

音频独立候选现已复现blockFalse/maxbytes仅信号时nativequeue可无界（2s96000B>7680）；原7＋新10共17测试，非USB根因证明。主端正做真实Gst无ALSA隔离，候选未因此直接变正式；不默认禁语音/USBreset/内核配置。完整代码、证据、风险与后续见[共享回执](/home/ghmd/Win共享文件/协作任务/2026-10-26_转轴完整复核与首帧修复/README.md)。未代填Windows接收/运行与实体验收。

## 音频终端收尾与最终版本

上述候选态已更新：KV260实际Gst1.18.5 appsrc→fakesink/BLOCK_DOWNSTREAM成对隔离通过（8.17s，原最大106560B、新最大7680B且有限报错释放），不打开ALSA/USB，业务owner保持；不是USB/声学验收。首轮3.6s自有child超时失败保留，r2阶段计时导入初始化约0.85s、baseline打印前3.26s、移probe/NULL约毫秒，仅说明重试正常，不精确追认首次超时原因。

空闲正常停止GUI751680exit0，备份`before-audio-queue-bound-v1`后只改engine/pin，最终GUI772087、audio772163、camera720342保持，259pins。engine f5d987904aec0dc679936da27018f404f9cc77f42d300e0579a3b52a95f0655c；startup SHA3ce0248ba168955d84876bb0b3561567edd3df4dead99d01705d4d74fba29565。verify初见unit activating被检查拒绝，保留STARTING，之后READY，不重复start/kill。最终phase R14_V17_GUI2_AUDIO_QUEUE1_READY_STOPPED，STOP1402/flags0/lease0/epoch1119，primary29/optional0、0不变，无新ARM/COMMIT。

新只读观察774182最多7200s，13:52主机UTC取回185s/38样本、4个kernel窗口0告警/0读错/0跟随。13:59再读其已运行620.682秒、125样本，primary29、optional0/0、STOP保持。旧观察753305在正常GUI维护期间因连续3次HTTP连接拒绝，记录THREE_CONSECUTIVE_READ_ERRORS后自行退出（935.809秒/188样本）；没有自动恢复动作，不能把维护窗口当新版本长稳样本。未声称两小时完成。板墙钟仍2021，时间交接用主机UART UTC/单调span，未改系统时钟。

重新核对ZIP器件规格：商家DS3230资料死区3us，500..2500/180°只是标称，10月20日有用户DS3230/独立供电共地/摄像头随轴确认；当前硬限1400..1600与用户机械中位1420导致小脉宽侧仅20us。实体最小步长/死区与行程仍待返场测，不能在无人时按标称值扫宽或自动回中。完整回执/代码/数字及下一步已写入共享入口与[USB专项](/home/ghmd/Win共享文件/协作任务/2026-10-26_音频USB告警与队列保护/README.md)。

## 14:05接续

只读观察已完成985.826秒、198样本、17个内核窗口0告警/0读错/0自动跟随，primary29及可选0/0不变；这是约16分钟结果，不提前称两小时通过。8.042秒只读人脸诊断246个UNCONFIRMED包、79独立检测轮，最大readerqueue等待12.738ms、处理轮1.091ms、无fatal、未加载运动模块/未打开MMIO，完整STOP1402不变。无有效人脸因此不能测真人首动或平顺性。音频另一路正增加有界只读复发证据采样器，业务不变。

## 14:17接续收尾

只读事件采样器c7f42323…完成15项离线回归及KV260真实路径检查：3秒明确BASELINE快照hw/appl各+144000、MCP01 identity/slot正确、runtime_status active/control on，未捕获或注入故障。20.009s实运行两轮，历史99同文本＋21其他记录正确过滤，0新告警/0incident；不是完整告警率。启动PID808617最多7200s/最多3incident/间隔60s/总1MiB，固定10s读，只收PCM/IRQ/CPU/USB数字，任何owner/设备变化或读错停，不重置USB、不改服务。源码、测试、SHA及baseline/20秒/启动回执已写音频共享目录。

稳定性观察774182累计1711.434秒/343样本，29个每分钟内核窗口0warning/0readerror/0following，primary29/optional0、0保持。此为约28.5分钟，尚短于之前约1h55复发时长，USB根治/两小时验收未声明。r14/v17/GUI2/音频队列1与STOP1402保持。另仅准备未执行的有人30秒脚本及共享返场短测：先解决接近硬下限和用户机械中位不对称，再真人左右越线/回区/换向，不无人回中或扩行程。
