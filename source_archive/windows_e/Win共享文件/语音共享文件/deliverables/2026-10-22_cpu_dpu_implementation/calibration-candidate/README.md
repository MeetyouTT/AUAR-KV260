# SFace INT8 现场标定候选

本包实现 `CALIBRATION_ONLY`：在既有相机的 SFace shadow worker 内观察合格 INT8 输出，RAM 中保存操作员指定的匿名分组，输出标定/验证的数值统计。没有创建第二个 DPU owner、runner 或相机进程；没有开启 INT8 身份库、登记、发布身份、写照片/向量或自动填写正式识别阈值。

状态：**仅软件候选**。软件合约测试使用合成像素/向量与临时合成数据库，不接触真实人脸或板卡。本包没有连接 UART、部署或修改任何现有服务、共享入口、冻结候选及原身份库。主任务正在单独处理原链路的音频/负载异常，本候选不介入该排查。先前 SFace 真人短测属于原 shadow 候选的证据，不能当本标定接线的板验。

## 范围和最小接线

`candidate/aura/` 是 9 个文件的 overlay，依赖已恢复的实际板端源码和已验证的 YuNet/runtime overlay。基线与 SHA 在 `patch-manifest.json` 中逐项记录。

| 文件 | 内容 |
| --- | --- |
| `board/identity/sface_calibration.py` | 只用标准库的 RAM 会话、源票据、标定统计、候选冻结、独立验证；没有设备/存储入口 |
| `board/identity/calibration_http.py` | 默认关闭的新 loopback 控制路由，Bearer capability、严格 JSON、容量/重放检查 |
| `board/identity/sface_shadow.py` | 原 shadow 中新增可选观察器；offer 时绑定会话票据，输出通过原 target/TTL 复核后才观察 |
| `board/identity/camera_faces.py` | 显式配置创建观察器；health 只返回汇总；原 Windows 正式身份路径不变 |
| `board/vision/ui_camera_service.py` | 唯一新增位置是 `handler_for` 最后一处 `return wrap_handler(Handler,state)`；未改采集/推理/音频/显示 |
| 其余 4 个文件 | 直接复用已冻结 shadow 的 `deferred.py`、`live.py`、`model_store.py`、`dpu_sface.py` |

这里的“无身份发布/无 DB 写入”限定于新增标定路径。原 Windows 身份服务按原行为继续工作，标定不会把 INT8 特征交给它、替代其结果或调用登记/删除接口。不要把原服务同时产生的正式身份当本标定结果。本模式不启用新的照片归档；现有业务的登记按钮仍属于原身份业务，现场标定期间应只操作新增标定入口。

与主任务 T2 埋点合并时，对 `ui_camera_service.py` 只合并 handler 末尾的两行导入/包装，不用本包整文件覆盖较新的 run/callback/health 修改。`sface_shadow.py`/`camera_faces.py` 必须以本包 manifest 的冻结 shadow 基线为准，不能覆盖板端其他未确认变更。

## 会话协议与有界输入

默认没有配置或 `{ "dpu_sface_calibration": { "enabled": false } }` 时不创建标定控制器。只有显式启用独立 `compare_cosine=false` 的原 shadow 后，才能追加：

```json
{
  "dpu_sface_calibration": {
    "enabled": true,
    "mode": "CALIBRATION_ONLY",
    "control_token": "<PRIVATE_RANDOM_64_HEX>"
  }
}
```

示例中的占位符故意不能通过校验。操作员在板端私有候选配置生成随机 256 bit capability，配置权限设为 0600；不要放进共享目录、manifest、日志或命令行。原 Windows 配置、模型 ID、阈值、库路径全部保留；没有用随意的 INT8 阈值绕过现有 `null` 拒启保护。

新入口仅 `POST /v1/ui/sface-calibration`，同时要求 loopback 地址、单个正确的 `Authorization: Bearer <capability>`、`application/json`、单个 Content-Length 与不超过 4096 字节的请求。拒绝 Transfer-Encoding、重复 JSON 字段及 NaN/Infinity，不接受图片、向量、照片路径或远程 URL。原有 HTTP 路由按原行为委托。

请求格式为 `{ "action": "...", "params": {...} }`。

| action | params | 行为 |
| --- | --- | --- |
| `health` | 空对象 | 返回容量、状态、计数，不含 capability、session token、姓名、目标或向量 |
| `start` | `request_id,purpose,person,capture_session,target` | 原子复核当前目标后，显式开始一个匿名采集场次，返回私有 session token |
| `end` / `discard` | `request_id,session_token` | 结束并保留 RAM 样本 / 丢弃本场次；在途票据立即失效 |
| `report` / `suggest` | 空对象 | 仅使用标定集，返回数值统计 / 阈值建议 |
| `freeze` | `request_id,threshold,ambiguity_margin` | 覆盖合格且无活动场次时，显式冻结 RAM 候选；不写正式配置 |
| `validation_report` | 空对象 | 用冻结 gallery/阈值对新验证场次作独立统计 |
| `reset` | `request_id` | 丢弃 RAM 特征和候选；保留防重放台账，不允许旧请求重用 |

`person` 只接受 `P_[A-Z0-9]{1,12}`，不是姓名或自动识别结果；`capture_session` 只接受 `C_[A-Z0-9_]{1,24}`，在当前实验中全局不可复用；target 是调用者明确提供的 `camera_epoch/track_id/track_generation`，不自动选人。操作员负责保持每场只有该对象、标签真实并实际隔开采集场次。不同字符串本身不能证明物理独立采集。

最多 8 个匿名 person、32 个场次、每场 12 个 128 维特征，总特征标量上限 49,152；Python 对象还存在固定开销，因此不把“标量字节数”当进程 RAM 总量。原 shadow 仍最多一个在途 crop＋一个最新 pending crop，所有特征/crop 只在 RAM。每场最长 120 秒，样本至少相隔 500 ms，场次至少 3 个样本才计入统计。目标失效、代次/相机换代、源 TTL 过期、重复/倒序帧、重复票据、结束/丢弃/重置/关闭均拒绝相应输出。因目标改变或超时中止的场次不进入标定/验证统计，需要重新开始新场次。

源票据只在进程 RAM，绑定会话 token、代次、目标、源帧/时间、相机质量元数据和单调序号；回放无法重复采样。质量元数据由原 `pose_quality` 的五点几何＋对齐 crop 拉普拉斯方差提供，HTTP 不接收或伪造质量值。仅接受 yaw 提示值绝对值≤.22、roll≤15°、原脸最小边≥72px、眼间距≥18px、blur≥40 的正面样本；它是几何提示，不是已标定的头部姿态角。会话 token 256 bit，检测碰撞并有界重试；每条写命令的 `request_id` 为 128 bit 十六进制，失败的请求也消耗 ID。台账最多 128 个 ID，满后拒绝写入，不淘汰旧 ID 使其可重放。reset 不能清台账。需要新实验容量时走主任务的正常候选服务重启流程，本工具不会自行重启。

采样票据申请不等待 session 锁；锁繁忙直接略过该次标定。worker 的观察发生在原相机保护锁之后，锁顺序为 state.lock → shadow.condition → session.lock，session 不反向申请相机锁。统计先复制有界 RAM 快照，释放 session 与相机锁后计算；HTTP 最多同时执行一个较重的 report/suggest，health 不等待该计算。不要在性能对照窗高频请求统计。

关闭先由原 shadow worker 结束在途调用、关闭自己的 runner，再清除标定 RAM 引用。原 native wait 卡住时仍遵循既有 shadow 边界：不谎报已关闭、不释放仍在使用的 owner；由主任务停止原进程后恢复。这里的清除是释放 Python 引用，不是对解释器/操作系统内存作安全擦除保证。

## 标定与验证流程

1. 每位预定登记者先显式采 `calibration_gallery`，再离开/重返或另起实际场次采 `calibration_probe`，每场 3～12 个合格样本；至少两位。
2. 至少一位没有 gallery 的对象采 `calibration_unknown`。同一 person 不能同时被当 gallery 与 unknown；不能把本轮 probe 当 gallery。
3. `report` 给出跨场次同人/异人余弦 count/mean/min/max。`suggest` 只在标定覆盖合格时搜索预设 21×21 网格（threshold 0..1，步长 .05；margin 0...5，步长 .025），优先零已观察误接受/误识、再提高已观察正确接受。没有有用候选时明确返回不足，**有限小样本上的零错误不等于真实误识率为零**。
4. 操作员查看标定报告并用 `freeze` 明确填写候选数值。冻结后不再接受 calibration 场次，也不允许改阈值或 margin；只有 reset 丢弃当前实验才能重新开始。
5. 在新的独立采集场次采 `validation_known` / `validation_unknown`。原 gallery 与阈值完全冻结；验证样本不进入 gallery、pair 标定、suggest 或阈值选择。
6. `validation_report` 分别给出 known/unknown 实际样本数、正确接受、误拒、歧义、误识、未知拒识、未知歧义及误接受。覆盖不足始终返回 `COVERAGE_INSUFFICIENT`，不返回验收通过。只有一人时允许准备其 gallery/probe，但不能 freeze 或宣称异人验证完成。

gallery 每个匿名 person 只接受一个合格完成的 gallery 场次，从真实观测向量选代表，不使用均值合成新模板：按绝对 yaw、绝对 roll、负 quality 取最正面 5 帧，再按与这 5 帧的相似度总和、quality 选 medoid。quality 是 `min(blur,400)+min(pixels,240)`，选择核心与实际 `EnrollmentSampling._choose_front` 一致，已有 3 帧及 10 帧/前 5 排序两组真实源码对照回归。`gallery_policy=frontal_medoid_v1_observed_top5_operator_labelled_capture`，不同人员按 group 分别选一个模板；probe/unknown 不会变成 gallery。

判定顺序与正式 IdentityStore.match 相同：top1 低于阈值→UNKNOWN；否则 top1-top2 小于 margin→AMBIGUOUS；否则接受。但是本工具仅 3～12 帧/场次且只采正面，没有执行正式登记至少 15 秒采集、后验连续验证、姓名确认、独立库落盘和重启持久化；因此**不能声称等同正式登记或阈值可部署**。跨场次 pair 统计与使用 group 模板的识别统计分开呈现。report/health/冻结候选明确包含 `deployment_threshold_validated=false`，正式登记模板和完整业务流程仍须重新核对、标定与独立验证。

validation_unknown 可以是同一未知 person 的**新场次**，便于至少 2 位登记者＋1 位未知对象的初步现场检查；报告明确给出其曾参与标定的人数，不宣称人物完全留出或广泛精度。更有代表性的未见人物、光照/姿态/距离验证还需额外安排。所有标签由操作员断言，程序无法从匿名代码证明人与标签一致。

候选中的 `field_threshold_validated=false`、`deployment_threshold_validated=false` 与 `general_accuracy_proven=false` 不会被本工具自动改成 true。正式登记库、正确姓名、业务 TTL/多人歧义/删除/重启闭环仍由后续独立阶段验收。本包不修改正式 `threshold=null` 模板；正式启用仍要主任务审查数值来源和验证证据。

## 操作工具与不申请硬件的检查入口

`tools/calibration_operator.py` 是板端本机客户端，固定访问 `127.0.0.1`、显式禁用代理/重定向；从私有配置读取 capability，不把它放 argv/env 或报错日志。action 参数从 stdin 读取，写操作自动生成新的 request_id。示例：

```sh
python3 -B tools/calibration_operator.py \
  --private-config /设备私有目录/board_identity.CALIBRATION_ONLY.json \
  --port "$CAMERA_PORT" --action health
```

start/end/freeze 的 params 以 JSON 从 stdin 输入；target 必须由操作员核对当前新鲜目标。start 返回的 session token 仅供本机操作，不放入共享证据。client 不选择目标、不读库、不启服务。未部署本 overlay 前，原服务的新增路由应为 404，不能据此认定已有标定能力。

`tools/calibration_contract_check.py` 是可单独暂存的**标准库合成检查入口**，只读取指定源码并核对 SHA，随后阻断 board/numpy/cv2/xir/vart/sqlite3/socket/urllib/subprocess/serial 导入和文件 open。它用 RAM 合成轴向量检查 8 项协议，不读取配置/模型/身份数据，不连 DPU、相机或服务，不开/建 DB。示例中的 SHA 需从本包 manifest 取值：

```sh
python3 -B tools/calibration_contract_check.py \
  --module /独立暂存/sface_calibration.py \
  --expected-sha256 "$CALIBRATION_SOURCE_SHA256"
```

成功输出 `STANDARD_LIBRARY_SIMULATION_ONLY`、`runtime_verified=false`、`database_created=false`、`field_threshold_validated=false`。即使在板端执行也只证明该 Python 的标准库协议兼容，不能当实时 DPU 或现场阈值验收。本包附本机实际输出 `standard-library-check.json`。

## 实际验证

运行 `python3 -B run_tests.py`，使用本机已有 Vitis AI CPU 容器、只读挂载、无网络，无板卡/真实图片。结果见 `test-results.txt`。基线 16 项 shadow 合约与新增协议/统计/HTTP/工具测试一并执行。

测试包括默认关闭、严格匿名参数、容量上限、token 碰撞与回放、换代/TTL/在途取消、繁忙锁不阻塞生产者、真实 numpy.float32 输出类型、标定/验证分离、冻结不可改、实际观测 medoid 与真实 EnrollmentSampling 选择一致、质量元数据和正面门、group 判定与真实合成 IdentityStore.match 一致、无文件 I/O、RAM 关闭清理、loopback/Bearer/严格 JSON、无 HTTP 向量输入输出、CLI 禁代理/重定向、标准库独立子进程检查。真实 store 一致性测试只在临时目录创建合成库，标定实现本身没有 store/SQLite 依赖。

第一轮 37 项中有 1 项测试把 health 的 `max_embedding_scalar_values` 数值容量字段误当向量泄漏；已改为精确字段检查，未移除容量披露。工具测试初轮又有 1 项把 urllib 允许的 handler 类参数误当实例；已修正测试，保留标准库合法构造。后续发现的真实 numpy.float32 类型接线风险已修复并加入回归。最终结果以最新实际日志与 manifest 为准。

未验证：本接线在实际板卡上的导入/HTTP/runner、现场匿名标签、阈值与误识、整机负载/音频稳定性、正式身份登记与持久化。完整硬件验收必须等原链路恢复稳定后，由主任务独占板卡执行。
