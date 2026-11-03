# YuNet通知等待与独立取消检查

**最终当前版本已正式接受：** unit `048ee59c…`，相机298571/GUI监督298601/Xserver1077。100ms通知等待与独立取消信号已部署；旧方案的共享状态锁busy撤回在一分钟实流窗口内为0。当前最终审计确认双视觉DPU、音频IDLE_READY、恢复状态RUNNING，正式SFace仍Windows CPU。当前正式源码、性能数字和回退已封存到[交付目录](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_yunet_event_slot_wait/README.md)。

本轮目标是减少连续DPU准入拒绝造成的人脸更新缺口。候选将已准备好的输入在DPU关键区外等待最多100ms的时隙通知，YOLO释放后仍重新走原准入和提交前TTL/关闭检查；等待不占DPU，不扩大原30ms占用/5ms guard/200ms轮次期限/1000ms源TTL。超限受限自动恢复保持原配置。

实际调试发现：只加通知等待会在YOLO结束后立刻唤醒，而此时共享相机状态锁可能被后处理/UI占用，原nonblocking准入检查会持续busy撤回。该首次实时候选已拒绝并恢复上一版，保留完整过滤证据；不能将“通知可用”直接当业务成功。修正版将关闭状态改为独立的一次性取消Event，准入只读取该信号、不可变源时刻和轮次deadline，避免无关的状态锁竞争；图像/跟踪/发布仍使用原锁。close先设置Event，即使共享锁暂被其他线程持有，也阻止尚未提交的native任务。默认配置未启用时保留原路径。

软件验证：原117项加通知/期限/原子准入/实际Condition释放17项、运行包装层5项及独立取消3项，共142项通过；部署协议、PIN、已恢复历史故障检查、真实临时文件事务和回退共33项通过。KV260 Python3.9.9/aarch64同源17项无设备检查通过，无新DPU任务；空合成槽每次额外CPU约-0.0041ms，仅测量波动，不作板端降耗收益。

最初两次预检分别因父版存在已恢复历史超限、父相机正因`Camera stopped producing frames`自动重启而退出，均在任何服务切换前。已补父版已恢复状态核验，保留真实历史计数；新候选仍要求0新增超限。旧相机watchdog重启与通知候选无关。首次通知版上板后busy增多、TTL gap增多已明确拒绝；独立恢复报告passed，原unit e893930d…与音频恢复，相关controller/timer均inactive。另一次本机stage命令boot参数漏写一段UUID被校验拒绝，更正完整boot后17项前置通过；无绕过boot保护。

当前短窗口结果和实际活动版本以ACTIVE_RELEASE.json、accepted-release-evidence.json和final-audit.json为准。受控启动、真实观察、已接受和长期稳定性分别记录；两分钟窗口已实板接受，长期/冷启动仍未验收。正式SFace保持Windows CPU/旧身份配置，语音、运动、位流无改动。

新候选的模块变化是face_targets.py、camera_faces.py、dpu_vision_schedule.py、dpu_yunet.py和ui_camera_service.py；模型及量化runtime保持原SHA。camera_faces仅在显式启用yunet_slot_wait_ms的调度器下开启独立取消检查；相机config完整复制父版，只新增yunet_slot_wait_ms=100，原yunet_dpu_recovery=true保留。正常entry不包含延迟注入。

短窗对照：旧版read-only 60.063秒窗口 YOLO9.940Hz、人脸发布2.714Hz、CPU65.83%；新版本60.327秒窗口 YOLO9.962Hz、人脸发布3.763Hz、CPU57.28%。旧窗口累计gap为6→6（窗口内无新增），新窗口为0→0。采集帧不是配对输入，数字只描述实测窗口，不能称为严格加速比或CPU降幅。

另做15.152秒XRT/整板CPU点测：CPU55.331%、DPU task busy4.934%、207条DPU命令；统计随后关闭。busy是CU任务忙碌时间占比，不等于MAC/PL静态资源利用率。最终审计的slot-wait累计474次，全部ready、timeout0；这包括一分钟窗口外的业务调用。KV260空slot微基准每调用线程CPU变化约-0.0041ms，为测量噪声，不作为CPU节省证明。

本轮`python3 run_regressions.py`得到142项软件回归；`python3 -B -m unittest test_handoff test_live_checks test_control -v`得到33项事务/部署反例；KV260 Python3.9.9/aarch64另有17项隔离检查，没有提交新的真实DPU任务。真实业务窗口由受保护release controller完成，最终只读审计确认PID/单owner/源/config/GUI和模型保护，controller及restore timer inactive，CU统计disabled；`restore_previous.py --check`已实板通过。

本轮保留源码、测试、旧版一分钟只读观察、纯通知失败候选及恢复、token修正版实流、最终源码回读和SHA。交付不含原始UART、真人图像/声音/特征、数据库、偏好原件或权重。Windows回执未改，跨机接收未代确认。
之后只读实时检查再次确认camera298571、YOLO9.92Hz、YuNet后端DPU；跨进程累计YuNet calls2478/超限0/max26.418ms，slot wait1330次全部ready/timeout0，retry busy与撤回0、freshness gap0，当前人脸源帧age243ms。恢复仍RUNNING，CPU/DPU采样和controller均关闭。
