# SFace DPU 实时身份接入候选

本目录是独立候选补丁，未改变板卡、UART、生产服务、现有身份库或共享入口。源码基线是 2026-10-21 从实板回收的身份实现，以及 `2026-10-21_dpu_vision_start` 已验证的 YuNet/runtime overlay。它保留独立人脸跟踪、多人歧义处理、同帧五点对齐、多帧登记及照片策略；没有复制任何身份库、图片或向量。

当前交付状态：CPU 上的软件合约测试通过；新 SFace 模型本身的固定输入实板验证属于上一阶段证据。本补丁的实时身份业务、现场阈值、登记准确率及长稳尚未板上验收。

主负责人另于 UTC 2026-10-22 06:47 在 KV260 运行纯 checker，状态 `CONFIG_VALIDATED_NOT_RUNTIME_TESTED`，runner/database_opened/database_created 均 false，阈值未配置/未验收，原配置 SHA 未变。它只证明文件、配置与该板 Python 兼容；没有验证本补丁的实时 runner 或身份业务。该次板验对应 model_store SHA `5d6cd6fe6ddbff9b236b8d09791d7f013f3d02815c8bde99ae913cc7bc2180f0`；随后只补“任何 DB 文件 symlink 均拒绝”的写入边界，本地新增回归通过，后续板验需核对最终 manifest。

## 改动

`candidate/aura/` 包含 7 个补丁文件：

- `board/vision/dpu_sface.py`：共享相机原有 DPU owner 与 `schedule.optional('sface')`。只执行固定 SHA 的 NHWC `[1,112,112,3]` / fix7 → `[1,128]` / fix5 模型。颜色转换、量化、输出分配、反量化均在 DPU 调度区间外；区间内只有提交和等待。
- `board/identity/camera_faces.py`：显式 `feature_backend.kind=dpu_sface` 时才选择本地 DPU；保持 Windows/ARM 原分支。主相机已将同一个 owner/schedule 传入 create_service，不再申请第二 owner。
- `board/identity/deferred.py` 与 `live.py`：busy、optional 禁用或输入过期是本次计算未完成；丢弃此包，保留原结果的原始 TTL，不重新计时、不发布 UNKNOWN、不推进登记采样。目标、库 revision、结果 TTL 仍在发布前复核。正常停机关闭 worker 持有的 runner。
- `board/identity/model_store.py`：固定 `model_id=sface-int8-12b2ff5c7de15713`，要求独立版本命名的设备本地数据库；打开前拒绝重命名旧库、未绑定库、异模型模板及旧库 symlink/hardlink。显式启动候选服务时才创建 0600 新库及单模型绑定。配置检查不创建任何数据库或目录。
- `tools/check_dpu_identity_config.py` 与 `prepare_dpu_identity_config.py`：只用标准库作纯配置/文件校验与新模板派生，完全不导入 `board`、NumPy、OpenCV、XIR、VART，不创建 runner/数据库，不操作设备或服务。

准确文件与基线 SHA 见 `patch-manifest.json`。公共 `dpu_vision_schedule.py` / `dpu_vision_runtime.py` 未修改，避免干扰并行的 YuNet 长稳。

## 显式选择和回退

新模型 SHA：`12b2ff5c7de157133ebd5aa71665fc5ddcd1f65d9e30e2d6e965e0752e467f25`。
编译 manifest SHA：`d52e4343910f7d3c775405c161e3fdf16db27396891dc617b0e5defdb878841b`。
目标 fingerprint：`0x101000056010407`。

示例只说明候选的生成和检查，不会切换生产：

```sh
python3 -B /候选根/tools/prepare_dpu_identity_config.py \
  --fallback-config /原运行目录/config/board_identity.json \
  --model /已校验/sface_public_int8.xmodel \
  --manifest /已校验/compiler-manifest.json \
  --database /设备私有目录/sface-int8-12b2ff5c7de15713.sqlite3 \
  --enrollment-archive /设备私有目录/photos-sface-int8-12b2ff5c7de15713 \
  --output /独立候选配置/board_identity.dpu_sface.TEST_ONLY.json

python3 -B /候选根/tools/check_dpu_identity_config.py \
  --config /独立候选配置/board_identity.dpu_sface.TEST_ONLY.json
```

候选根仅需保持 `tools/` 与 `board/identity/model_store.py` 的相对目录关系即可独立检查，不依赖完整 aura 安装。所有 CLI 路径必须显式为绝对路径。模板生成用 O_EXCL，只允许创建新的配置文件，重复调用拒绝覆盖；它不创建数据库、照片目录或父目录，原 Windows 配置文件保持不变。

生成的新配置保留原质量阈值、登记策略等业务配置，但识别 `threshold` 和 `ambiguity_margin` 明确设为 `null`，`threshold_origin=INT8_FIELD_CALIBRATION_PENDING_DO_NOT_ENABLE`。纯 checker 会返回 `threshold_configured:false`、`field_threshold_validated:false`；真实 `config_for` 拒绝这种模板，防止未定阈值被直接启用。公开人脸对测试阈值没有自动写入现场配置。

未来现场验证通过后，需要显式填写 INT8 专属识别阈值与歧义间隔，选择独立候选配置、准备新登记库，再通过有回退的相机服务集成流程启用。SFace 没有逐向量 FP32 自动回退：INT8 与 FP32 向量不能写入同一模型空间。回退是恢复完整原 Windows 配置和原库，8792 服务及原模板均保持可用；具体可用性仍需当时检查。

若启用照片策略，新照片目录同样必须版本命名并与旧目录分离，避免初始化归档时改变旧 session 状态。本补丁未执行采样、登记或照片写入。

## 计数与检查边界

公共 scheduler 的 `optional.sface.calls` 统计成功准入区间。若准入瞬间输入刚过期，runner 不执行，但该区间仍会被记入 calls，因此展示不能把它当实际推理次数。

候选 health 的 `identity.feature_inference.completed` 只在实际 execute_async/wait 成功并取得输出后递增，`execution_attempts` 明确只代表尝试执行；`features_returned` 表示未过期特征返回上层，并不等于身份发布。另有 `requests`、`deferred`、`slot_denials`、`expired_after_admission` 及 `last_dpu_wait_ms`。IdentityService 还会因目标/库版本变化拒绝该特征。

纯 CLI 成功仅表示模型文件、manifest、精确 I/O、版本隔离配置正确，状态名为 `CONFIG_VALIDATED_NOT_RUNTIME_TESTED`。即使填写了数字阈值，它仍返回 `field_threshold_validated:false`，不能代替现场准确率或实时 runner 验收。

原 `ui_camera_service.py --check` 会先创建/关闭 YOLO owner，再无 owner/schedule 构造身份 extractor；它既会申请硬件，也不支持当前 DPU 身份检查。本补丁没有改变该分支，活动相机期间禁止用它作“只读检查”。本目录新 CLI 独立于该路径。

## 验证

运行 `python3 -B run_tests.py`，使用本机已有 Vitis AI 3.0 CPU 容器、只读挂载与无网络，不连接板卡。`test-results.txt` 保存实际结果。测试只用合成人脸像素、合成向量、临时数据库和上一阶段公开模型产物。

测试覆盖：BGR→RGB/归一化/fix7、fix5 输出、实际模型/manifest 哈希和接口、CPU 工作锁外、busy/禁用/提交前后过期、准入过期真实 completed=0、旧结果 TTL、目标和 revision 变化、runner 生命周期、独立库权限与持久化、拒绝旧库混用/链接、无 owner 不开库、null 阈值不能启动。隔离子进程强制阻止 `board/numpy/cv2/xir/vart` 导入后，纯 checker 仍可通过，并确认无数据库产生、原配置 SHA 不变、重试拒绝覆盖。

## 下一阶段建议：先做 shadow

主负责人提出先保持 Windows FP32 作为唯一身份判定，同时让同一合格 crop 在 DPU 上计算。这个方案能验证真实业务流上的三模型调度与时延，不必提前迁移模板或采用未经现场验证的 INT8 阈值。

最小接点是 CameraFaceExtractor 在 Windows 分支拿到原向量后、返回原向量前，向独立 shadow worker 提交 `(crop, fid, stamp, target, fp32_vector)`。worker 使用最新一项队列、显式限频、原 source TTL 和同一 owner/schedule；CPU 编码和余弦比较放在锁外。主身份分支仍原样返回 Windows 向量，不等待 shadow，不因其超时/失败改变身份结果。不能在 HTTP 调用期间持有 DPU 调度锁。

shadow 不打开 INT8 身份库，不写任何模板，不自动登记，不保存 crop/embedding；仅保留完成数、丢弃数、耗时和可选的同图余弦汇总。需要新增一个 bounded worker 及生命周期/health 接线，少量 CameraFaceExtractor/create_service 配置分支，并测试 shadow 故障不影响 FP32 身份与关闭过程。DpuSFace 适配器本身不打开数据库，可以复用；其固定模型版本与过期规则仍有效。此建议本轮尚未实现或板验，不能计入当前成果。
