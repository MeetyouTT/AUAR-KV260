# 转轴延迟接续：两路执行、MCP01日志风暴恢复与输入快路径

用户先要求继续开三个终端，随后改一个，最终改两个。按最新指令主端独占UART/所有板端变更，另一路只做本地审查和输入快适配；未再并发接板。中断前控制r13仅增加PWM帧边界FakeDevice与探针，未改冻结r12、未部署r13。现役控制仍r12、方向+1和左脸框10%/右中心80.647%边界保持。

读本机最新状态、Win共享入口、项目ZIP入口/AGENTS，先取无运动基线。线程CPU和schedstat证明有明显runnable等待；3秒全进程CPU点测GUI141.77%、camera117.81%、journald44.59%、syslogd33.28%、audio24.96%单核，四核接近满载、load10.37。日志末600条集中0.582秒，内核xhci slot4ep3数据缓冲告警与journald漏消息提示占主导。debugfs slot04 name1-1.2、Addr4/RS2确认是MCP01的USB playback端点0x02OUT，并非camera1-1.3。上游Linux5.15相同文本位于COMP_DATA_BUFFER_ERROR/-ENOSR，不能据此认定带宽不足/供电/损坏；主端只以原件和板端定位，不套用网上其他USB设备故障。

确认产品IDLE/notplaying/IDLE_READY、micPCM关闭、manualREADY/autoFalse/flags0lease0及258pins后，正常GUI-only停止/启动使PCM释放/重建；camera604389未在该阶段重启，未改音频设置。第一次额外假设SendSIGKILL=no不成立，前置检查拒绝，未执行STOP；按实际unit普通停止exit0成功，无强杀。GUI137253→647839，初18秒尚在STARTING保留等候，后READY；PCM RUNNING/IDLE_READY恢复，完整运动readback1458未变，恢复vision页和前台。后续数个末8秒日志为0，journaldNRestarts停16，热进程不再包含syslog/journald；同视觉页点测GUI140.86/camera126.87/audio15.32%，load4.41为滞后短窗，不当严格收益。只计一次恢复，USB底层根因及复发未根治；音频现役worker5f7f…/enginef257…已核对，不误用r4旧版。原7＋追加3Fake时钟音频有限测试过，无明确Python根因，不禁用语音/不加自动USB重置、不屏蔽历史日志。

新sourcev15只加入按fid/真实source对齐的wall/threadCPU分段包装；54源回归＋独立6项审查过，长数字观测包4009B<8192。保留v14跟踪/质量/250ms图/500ms锚/唯一owner/原生预算/SFace频率。fresh exact CP正常迁移camera604389→654064，GUI647839不再重启。23个实际NoFace对齐轮：layout/normalize CPU中位9.351ms、encode12.653ms；totalCPU41.902ms/wall86.479ms，identitycallback0.088ms。原生lease约2～3ms，证明输入准备是明确CPU热点；嵌套阶段不能简单相加，wall-CPU不直接认作GIL或DPU。

另一路实现最小FastYuNetNetwork（独立新目录），仅native/fix7/NHWC[1,320,320,3]启用。uint8→blob整数→/256→encode合并为uint16提升后(pixel+1)//2/clip127/NHWCint8，严格验证有限/范围/整数/shape，避免255+1的uint8溢出。原guard对象、_native_scheduled、decode/NMS、模型、CPU/legacy/fallback保持。6项本地bit/guard/异常过；与跟踪/profile组合60源回归过。

KV260独立无DPU微基准20帧（交替顺序，含resize/blob/whole setInput/forward和验证，双方同fake执行/identity输出）：20帧与256灰阶逐byte相等，5非法域拒绝、sameguard/legacy通过；total中位53.739→43.763ms、adapter35.504→24.457ms。无相机/模型/DPU/MMIO，不能当机械延迟。正常fresh exact CP迁移sourcev16 camera673020，GUI647839保持；快阶段实流可见，backendDPU_YUNET_INT8、workerfault0、owner未fence/可选未disabled。新23NoFace轮fast_encode CPU中位14.805/wall28.583ms，总CPU35.055/wall80.737ms，为非严格配对短窗，不宣传整机比例收益或真人平顺通过。

native primary历史7→本轮baseline15→高负载点测22→GUI关闭前25→v15启动26→v16启动27全部保留，不按时序强行归因；可选仍0/0，不能借重启清保护。期间一次下一步UART调用早于上一步完成被独占锁拒绝，未在板端执行；完成后串行重试通过。无新ARM/COMMIT/回中，最后命令1458/flags0/lease0/手动READY/autoFalse。本轮主要无人输入，真人起转/连续跟随/换向/平顺仍未验收。控制r12/Q09最后MMIO竞态的限制不变。

完整代码/源指纹、输入位等价与板端/live证据、MCP恢复范围与下一步真人流程：[/home/ghmd/Win共享文件/协作任务/2026-10-26_转轴输入延迟与USB恢复/README.md](/home/ghmd/Win共享文件/协作任务/2026-10-26_转轴输入延迟与USB恢复/README.md)。未改原Windows交接、未代回Windows同步/运行/验收；未共享个人原图、身份库、录音、模型权重/venv或UART原文。
