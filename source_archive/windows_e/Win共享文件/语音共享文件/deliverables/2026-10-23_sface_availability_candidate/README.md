# SFace停用状态与身份结果修复候选

状态：**代码修复、92项相关软件回归、KV260上16项隔离合成检查通过；尚未替换生产相机或GUI。** 用户已将YuNet偶发超限交给另一个AI，本轮保留当前相机/GUI进程及故障现场，不改YuNet或共享调度器。自动恢复策略不在本候选内。

修正前使用已读回的正式源，三个反例均失败：SFace保护停用后health仍ready、原TTL内仍显示缓存姓名、语音消费者把ERROR当UNKNOWN。修正版将持续停用与普通时隙繁忙区分：停用后health.ready=false并有数值原因码，界面ERROR且不再展示缓存匹配/脸预览，拒绝登记及启动采样，删除和取消仍可用；“我是谁”明确返回identity_unavailable。正常短时争用、CPU/Windows参考兼容路径及UNKNOWN保留原行为。

## 改动文件与部署归属

| 文件 | 作用 | 归属 |
| --- | --- | --- |
| candidate/aura/board/vision/dpu_sface.py | 增加轻量availability、停用/关闭原因、health持续可用性；不运行推理查询状态 | 相机runtime |
| candidate/aura/board/identity/camera_faces.py | 向上层提供当前特征后端状态 | 相机runtime |
| candidate/aura/board/identity/live.py | health/view/预览/登记/采样消费状态，不把旧匹配当当前可用；状态读取失败时明确不可用 | 相机runtime |
| candidate/aura/board/identity/spoken_query.py | ERROR返回identity_unavailable，UNKNOWN仍返回identity_unknown | **GUI runtime消费侧** |

相机基线unit `a29082ba…`、release `release-sface-int8-9025bd49fe52-333217`。GUI基线 `/home/root/aura-speech-motion-20261021/de989bf024a9/runtime/aura`。前3文件与正式相机读回SHA一致，第4文件从实际GUI读回；不可只把第4文件放进相机目录就声称语音消费者已修复。合并时分别接入最新相机和GUI源码，不覆盖另一AI的YuNet/调度或新的语音/UI成果。

本轮未改变30ms/5ms/源TTL、固定0.50阈值、margin、模型/INT8身份域或库；未加入FP32向量回退。SFace真正停用后的有界恢复/协调重启仍是下一项，不能把可见性修复称作恢复已实现。

## 验证范围

- baseline-failure-demonstration.txt：旧版本3个指定反例按预期失败，不是生产注入。
- software-regressions.txt：92项通过，覆盖新增16项、既有SFace通知/浮点边界、身份事务/协议/人脸目标及采样回归。
- board-isolated-result.json：KV260上16项通过，16个SQLite均为`:memory:`，禁止导入VART/XIR，实际新建DPU runtime0；模拟调度时钟触发保护，不向生产注入延迟。不读取真实身份库/照片。
- 隔离检查前后camera333557/GUI333586保持，4份正式源SHA不变；模型正式路径保持。`candidate_deployed=false`。

首次本机系统Python缺numpy，改用现有离线Vitis-AI镜像；扩大回归遇测试依赖pipeline_metrics缺失，读回实际依赖后完成相机/身份相关92项。额外旧语音测试缺test_simple_enrollment夹具未运行，未计为通过；新声学无关的语音ERROR/UNKNOWN消费集成由本候选专项覆盖。失败日志本机保留，未将缺环境当产品故障。

## 生产状态与CPU后续

隔离检查开始前，YuNet已出现第三次超限，调度占用82.926870ms且越过guard0.358214ms，当前LATCHED/CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN。前两次恢复2/2不能覆盖第三次保护锁定；本轮未重启、解锁或调整保护。最新数值环已另存为YuNet审查交接。YOLO约9.94Hz，SFace仍DPU且未超限，gap累计0。此处是现场状态，不是本候选造成/修复该故障的结论。

GUI只读取现有性能日志和滚动240帧profile：core p50/p95=38.492/76.711ms，整帧41.263/79.476ms，public1.023/2.072ms，compose_resize1.205/2.465ms，jpeg0.118/0.240ms。渲染约8fps；最近12个5秒窗口为IDLE。实际worker源码表明core段覆盖controller.tick，包括控制、音频/状态及动画/合成，不能直接把38.492ms称作纯绘制CPU。下一步应在此段内部细分，再选择优化点；当前快照复制已不是该窗口主要墙钟段。墙钟不等于纯CPU，也不能相加各阶段分位数或以此宣称优化收益；GUI组此前3秒36.35%整板CPU仅为进程级线索。

## 接续与复现

在保留另一AI故障审查现场的阶段，本包仅隔离验证。正式接入需回收双方最新改动，合并3份相机源与1份GUI消费源，使用匹配版本的协调关闭PCM/恢复流程，在短轮确认健康状态、原模型/库及用户偏好后接受；不能直接复用绑定旧unit/boot的历史安装器。本包不提供绕过这些检查的原地覆盖命令。

本机 `python3 run_tests.py test_feature_availability test_formal_scalar_contract test_sface_notification tests.framework.test_camera_identity tests.framework.test_identity_face_targets tests.framework.test_enrollment_sampling -v` 使用已有离线容器和冻结依赖。板端隔离封包入口build_board_check.py及源SHA清单保留。所有候选代码/证据可审核；本轮无正式运行代码/配置、音频监听、身份库、位流或运动输出变更。
