# 120秒诊断的性能优先级审查

结论：该窗YOLO接近10Hz目标，正常调度等待很小；YuNet可选任务的有效吞吐受准入和采样节奏影响。CPU首先调查采集复制与预览整段，SFace后续实验首先解决影子供给与同步Windows请求的耦合。**尚无证据把某个CPU stage或USB/DPU确定为此前偶发超限的根因。** 更新：600秒延长诊断被原基线的新USB告警预检拦截，尚未切换候选；主任务正核对恢复。先恢复/验证基线，再决定后续诊断与候选实测。

这里只读既有证据、实际源码和冻结候选，未改4源码、服务、板卡、UART、共享入口或阈值。数字可运行 `python3 -B summarize.py` 从既有过滤报告重建，见 `summary.json`、`stages.csv`。输入SHA随summary记录。原根目录的冻结manifest和FILES不作改动，本子目录单独核验。

## 实测范围

120秒诊断295次实际成功wait，YOLO9.924Hz、YuNet2.442Hz、板CPU55.26%（四核合计100%），相机进程21.21%板CPU、约0.848个CPU核；0次新USB告警、0个诊断fault，自动回退通过。只有短窗未重现，不能推翻既有33/35ms超限，不能称长稳通过。报告没有新XRT忙时采集。

最终stage统计覆盖候选进程从启动开始的生命周期，包含观测前约2.6秒；quantile只覆盖最近最多256次。相邻stage计数可能在health取样的瞬间相差1，因为采样未暂停worker。

| stage | 生命周期均值ms | 最近最多256次P95 ms | 应如何读 |
| --- | ---: | ---: | --- |
| capture.callback_prepare | 5.805 | 11.794 | pull-sample、复制、镜像及调度/GIL等wall |
| preview.render_encode_publish | 18.017 | 26.351 | 整段复制、绘制、raw发布、JPEG、发布wall，未拆开 |
| yolo.schedule_wait | .085 | .104 | 正常窗等待DPU调度很小 |
| yolo.native_and_decode | 12.184 | 17.135 | native预处理＋网络API/执行＋解码等，非纯DPU |
| yolo.track | 5.958 | 11.785 | 包含state.lock等待、跟踪和请求处理等wall |
| yolo.path | 18.625 | 29.990 | 包含上述YOLO等待/native/track等，不能再与它们相加 |
| yunet.execute_wait | 3.323 | 6.272 | VART API调用wall，不是硬件周期或调用线程CPU |
| yunet.dequantize | 1.828 | 4.527 | CPU反量化范围的wall，不能当CPU核秒 |

这些stage跨线程重叠，父子stage嵌套；**不能相加解释整板CPU，也不能按wall均值给CPU用量排名。** 只有 `/proc` 差分提供本窗CPU用量。表格是下一轮拆分观察的优先级依据，尚非CPU热点归因。

YOLO源帧开始时平均年龄43.01ms、发布62.11ms。采集约12.5Hz（约80ms/帧）与检测10Hz（约100ms/次）独立采样，本身可造成0..80ms的相位年龄；这属于解释假设，不是额外积压已获证明。新时间戳位于copy之后，不是传感器曝光时间；上游YUYV→BGR转换/USB/驱动时间也未由callback指标完整拆开。

## 调度与YuNet

候选进程共486次可选请求、295准入并真实成功wait（60.70%），191拒绝，其中54已有任务、137期限不足；无等待primary导致的拒绝。拒绝由首个原因分类，多个条件同时不满足时不是完整原因向量。对应源码：

- `candidate/aura/board/vision/dpu_vision_schedule.py:50`：estimate至少20ms，准入还需5ms guard和空闲gate。
- 同文件`:78`：估计偏差后上调估计，仍保留30ms硬上限。正常窗最大24.532ms引发一次estimate miss，未是真正cap/guard失败。
- 已验收overlay `.../2026-10-21_dpu_vision_start/candidate/aura/board/identity/face_targets.py:63`、`:145`：拒绝保存原目标TTL，但也在本次process结束后再等200ms，最新帧覆盖pending；不是“每200ms必执行一次”。
- `.../candidate/aura/board/vision/dpu_yunet.py:27` 与实际 `live-source/board/vision/reference_faces.py:55`：resize、blob、布局/量化、输出分配发生于准入判断之前；被拒绝的请求已发生部分CPU准备。

这证明有减少无效准备、改善到达相位的空间；**没有证明应缩短20ms估计或放宽30ms**。20ms相对正常3.323ms均值保守，但既有尾部已见35ms，不能只按均值缩小预算。可选任务在当前设置下即使gate无争用也受“处理时长＋200ms”节奏限制，实际4Hz左右请求不等于5Hz承诺。

未来可评估一次有界、等primary释放后的新鲜帧重试，保持相同cap/guard和最新一项队列；不能busy loop或对同一旧帧不断重跑。先用相同到达序列做固定策略对照，验证实际完成/消费是否增加，以及多出来的准备CPU与主检测帧龄。简单在CPU准备前加“现在busy就跳过”也可能错过稍后已空闲的窗口，不应未经对照直接部署。

## SFace的0.364Hz从哪里来

旧三模型长测最后保留的健康区间约55.01秒，42次offered＝42次enqueued＝42次DpuSFace请求，20次实际完成、22次slot_denials；replaced/producer_dropped/stale均为0。算术上：

```text
供给约0.763 crop/s × 成功准入20/42（47.62%）＝ 实际完成约0.364/s
```

这是保留区间的精确计数分解，**不是DPU只能跑0.364Hz**，也不是20次认人正确。失败检查那一帧缺失，不能把本分解冒充失败执行的精确情况；face_count每5秒一次，不能当作连续有人脸时长。

源码定位：

1. 原shadow `camera_faces.py:131-150` 在合格crop后、Windows请求前投递一次（compare_cosine=false），但**下一张crop仍由同一个IdentityService线程准备**。
2. 原shadow `live.py:273-274` 同步执行process后，再设置 `next_at=now+interval`。实测保留配置 `models.response.json:80` 为500ms，`board_shadow_long.py:124` 验证其余原配置完整保留。
3. 实际 `live-source/board/identity/remote_features.py:20-24` 同步HTTP request/getresponse/read，socket timeout配置650ms。它是socket操作timeout，**不是整个HTTP链路严格650ms deadline**；多个阶段/分段接收可能更长。
4. 原shadow `sface_shadow.py:205-209` 在每次_process返回后再等1000ms，成功、busy/deferred也一样。它限制的是尝试频率；拒绝后不会立即等下一slot补算。

如果每次原身份process主要等一次约650ms网络超时，再等500ms，则下一次crop约1.15秒以后，约0.87/s，另有crop质量/目标缺失等。这与实际0.763/s相容，是有源码依据的候选解释。报告没有HTTP逐次耗时/失败原因计数，**不能断言所有请求都耗满650ms，或定量归因其占比**。

当前区间没有队列替换且所有offered最终进入DpuSFace请求，所以单把worker的1000ms改500ms，不会自动创造更多crop供给，也不会自动补偿22次被拒绝。缩Windows timeout或改变原IdentityService周期会同时改变正式Windows业务负载/错误行为，不能作为影子提频的便捷开关。

改善有效DPU吞吐的建议是：后续独立候选把shadow的合格crop供给从同步Windows调用线程中分离，在FaceTargetService选出显式新鲜人脸后，以一项latest-only准备队列限频，复用同owner/scheduler、目标/代次/TTL复核；主Windows路径按原行为运行。先验证供给、实际准入、完成/消费、CPU准备重复开销与主检测一致性，再决定1Hz和拒绝后的有界重试。正式SFace迁移通过后也会消除这条Windows依赖，但不能用尚未验收的迁移假设当前问题已解决。

## 下一步最小改动排序

| 优先级 | 建议 | 依据和验收边界 |
| --- | --- | --- |
| P0，当前 | 先核对/恢复新USB告警的原基线，再按预检重开延长诊断；不改冻结源码 | 当前600秒尚未部署；120秒未重现不足以确定尾延迟原因，避免把优化与根因混在一起 |
| P1，最小CPU候选 | 独立分支仅删capture中间那一次`.copy()` | `ui_camera_service.py:417-421`已extract_dup成独立bytes，frombuffer后又copy，cv2.flip再产独立输出；可减少每帧921,600B确定存在的复制。先验证镜像字节、只读输入、输出ownership/生命周期，随后同业务CPU/帧龄对照；收益尚未实测 |
| P1，DPU有效容量候选 | 分离shadow crop供给，再评估一次有界重试 | 42供给/20完成计数支持先解耦供给和准入；不改变原Windows正式身份、不放宽cap，不承诺达到某Hz |
| P2，先补拆分观察 | preview拆成copy/overlay/raw.publish/JPEG/publish；YuNet拆准备/输出映射/CPU decode；identity拆align/quality/PNG/HTTP | 当前整段wall较大，但缺少线程CPU及分段；先定位，避免删掉仍需使用的功能 |
| P3 | 确认当前所有消费者后才考虑按需JPEG/批量转换/减少重复缩放 | raw transport存在不等于JPEG无用，显示/运动保护保持 |
| P4 | 相机上游有效帧率定位后再探索YOLO提频 | 目前实际采集约12.5Hz；不能用重复旧帧提高“有效吞吐” |

为什么不直接删JPEG：当前 `ui_camera_service.py:504-507` 每帧同时raw.publish和JPEG；`publish_preview:71-76`把frame写入frames，snapshot用其构造preview。已有GUI `tools/board_camera_preview.py:127` 即便走raw也先要求snapshot.preview，`ui_services.py:237-244`仍有JPEG fallback。简单移除编码/发布会改变预览READY与兼容路径，可能破坏显示。共享GUI源码只证明存在此路径，当前生产GUI实际transport/版本仍需主任务读证据核对。

## 现有诊断缺口（只提出，未改4源码）

- 正常完成的thread CPU标记被丢弃，只保留fault的CPU拆分；本窗fault=0，所以无法给出正常VART wall与threadCPU分布。这是设计的有限保留，不应根据“没有事件”推算CPU占比。后续如需baseline，可单独候选增加数值sum/min/max或每32次最多1条有界正常样本，再对照观测开销。
- native异常/cap/guard事件包含阶段边界，但不能区分驱动/硬件/OS抢占/GIL根因；不是硬件任务开始/完成硬时间戳。
- native永不返回、进程SIGKILL或整个Python健康接口因GIL停住时，finally没有机会写终结事件。只有已有active phase与外部进程证据可能保留，不能宣称能抢占或总能读到挂起状态。
- 缺采集上游/传感器时间、preview子段、FaceTarget总CPU准备、HTTP耗时/超时阶段、crop供给间隔及独立worker消费/拒绝重试序列。下一版本应默认关闭、只聚合数值、不保留生物数据；不能为补证据临时改动冻结诊断源码。后续若重开600秒，先通过原基线预检。
