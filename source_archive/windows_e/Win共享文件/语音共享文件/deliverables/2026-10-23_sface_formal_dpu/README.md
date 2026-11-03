# SFace正式DPU迁移

**最终已接受并保留三模型DPU业务版本：** unit `a29082ba…`，camera333557/GUI监督333586/Xserver1077，正式身份后端`DPU_SFACE_INT8`，新INT8库保留原有1个登记身份。原Windows身份库及照片完整保留，原库SHA前后相同。新版本不是影子模式，界面使用本地DPU识别结果。

| 本次独立60.345秒窗口 | 实测 |
|---|---:|
| YOLO人体检测 | 9.959Hz |
| YuNet人脸发布 | 3.563Hz，215次新DPU native完成 |
| SFace正式身份特征 | 1.740Hz，105次新DPU native完成 |
| 已知本人匹配 | KNOWN95／UNKNOWN10／AMBIGUOUS0，接受率90.48% |
| 稀疏状态快照 | 13点中11点识别为确认本人 |
| 新增DPU超限／人脸更新gap／USB告警 | 0／0／0 |
| 整板CPU | 66.50% |

另一15.197秒动态点测CPU64.69%、DPU任务busy6.276%、完成231条DPU命令，其中SFace新完成31次。此窗口不是与旧版完全相同帧流的受控加速比较；busy不是MAC阵列效率或PL静态资源率。XRT统计最后关闭，发布controller和独立restore timer inactive，回退入口--check实板通过。

实际release为`/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-sface-int8-9025bd49fe52-333217`，匹配源880文件包、关键16文件与GIL1ms启动记录已从板端回读；当前配置启用YuNet/SFace各100ms outside-slot通知等待，30ms/5ms及独立取消和帧TTL保护继续适用。

本轮用户明确要求开始解决未完成项，并确认镜头前为此前已登记的本人。基线为unit048ee59c…的YOLO＋YuNet DPU、Windows SFace；新目标是在同一DPU owner下运行三模型，并为既有身份重算独立INT8模板。

迁移来源是当前原库唯一登记身份与恰好匹配当前库revision15的committed照片归档。先验证26个图像文件哈希、selected图片原CPU embedding与旧模板余弦至少0.99999，再在暂停相机owner期间独占项目DPU锁重新提取selected及5个原登记留出验证帧。新库严格绑定sface-int8-12b2ff5c7de15713，保留旧身份ID与称呼、只写新域向量；原库、旧照片和配置哈希保持。复用既有登记与本人迁移确认，不自动创建新的用户身份。

首次离线迁移在完成新特征提取后，store.match拒绝numpy.float32输入，事务未接受并协调恢复原相机/GUI。修正CameraFaceExtractor本地DPU分支将特征转换为普通float tuple，以及迁移验证入口做normalized标准浮点转换；增加真实extractor→store合成集成检查。源不将INT8/Windows向量混写，也不逐向量回CPU。

本轮SFace加入与YuNet相同的最多100ms通知等待，等待时无DPU slot；醒来仍重新检查新鲜源stamp与正常primary deadline准入，30ms硬cap/5ms guard保持。候选默认不开启新等待；此release显式sface_slot_wait_ms=100。未扩大帧TTL/改变YOLO优先。

验证状态：最终83项隔离软件检查和36项发布/回退事务检查通过。原模型SHA、编译fingerprint、tensor接口必须匹配。开始正式服务前设置独立restore timer，服务故障或gate失败协调返回原unit048ee59c和原Windows配置。正式接受记录见ACTIVE_RELEASE.json和accepted-release-evidence.json，早期failed reports及恢复证据保留。

真实调试中先遇到NumPy输出类型被store拒绝并修正；随后某一轮三模型性能通过但已知本人快照仅2/13，另一轮没有稳定正面目标，均未接受。私有预览检查的是姿态/可见性，不作人工身份辨认；之后将“操作员已宣布开始”作为计时信号，等待连续KNOWN再采一分钟。当前正式窗口是本人确认＋正面已就绪后的独立采样，不将等待阶段的UNKNOWN清零或算成全生命周期90.48%。同一正式进程在窗口之前的UNKNOWN仍保留在累计诊断中。

前置还遇旧相机`Camera stopped producing frames`后的systemd自动重启，以及免按键enabled但mic closed/WAITING_SERVICE被旧条件误拦；对应尝试在改service之前停止。只读3次连续新帧就绪等待和实际mic/录音/播放检查已加入，保留用户enabled偏好；没有放行活跃录音/播放。一次工具访问UART被原有独占锁拒绝，未发命令，等传输完成后串行进行。

实验阈值0.50/margin0.10在独立INT8域重新检查旧登记留出正样本，并在本轮活人已知身份场景检查。陌生人/多用户的现场误接收率未验收；公开1000对仿真98.8%使用的是另一公开训练阈值，不能写成当前0.50现场准确率。本轮不会据5个正样本重拟合阈值或宣称未知人的准确率。

模型与旧登记图像/embedding/人名/IDs/数据库均不进入共享交付；报告只保留文件哈希、库绑定、计数、相似度和是否匹配已确认本人。语音仍在Windows，运动与位流未改。实际新库在板端私有目录，旧库完整保留；手动回退指引见OPERATIONS.md。
接受后的只读续查：同一camera333557仍活动，SFace累计1091次完成、YuNet3131次准入，两个optional overrun0、face freshness gap0，SFace slot wait511次全部ready；此时face_count0，因此界面UNKNOWN是无当前人脸的正常结果，不计入已知本人窗口。
