# SFace DPU shadow 候选

状态：独立候选，尚未上板或启用。Windows FP32 和原身份库仍是唯一身份判定来源。本目录未连接板卡/UART，未改变生产服务、共享入口或冻结的 `/home/ghmd/aura-sface-live-candidate-20261021`。

## 行为与改动

`CameraFaceExtractor` 原样返回原 Windows FP32 向量；只向额外 shadow worker 投递 RAM 快照。`compare_cosine=false` 时，合格 crop/质量通过后、远端请求之前投递一次，reference=None，本地计算不依赖 Windows 在线；`true` 时只在原 Windows 同图特征成功后投递一次，供余弦比较。远端失败仍按原错误路径返回，不自动替代身份判定。shadow 不查写身份库，不登记，不发布身份，也不保存 crop/embedding。原模型 ID、数据库、识别阈值、登记与照片策略全部沿用原配置。

新增 `board/identity/sface_shadow.py`：单独线程、一个最新 pending 槽，另有最多一个在途任务；每张 crop 仅 112×112×3=37,632 字节，副本不可修改。投递不会等待 shadow 锁或模型推理，锁竞争允许丢弃。队列替换旧包，不积压。默认至少 500ms 间隔，最多约 2Hz；模型处理慢时更低。source TTL 与 target key 在计算前后均检查，后验统计发布在父相机锁内复核。

复用上一冻结候选的 `dpu_sface.py`、`deferred.py`、`model_store.py`，三份源码保持原 SHA。shadow 只调用 DpuSFace 适配器，不调用 open_dpu_store、INT8 配置迁移或登记接口，因此无需新身份库、登记阈值或复制原模板。共享原 camera owner/schedule，CPU 预后处理仍在 DPU 锁外。

`camera_faces.py` 加默认关闭的显式配置、异步投递、隔离 health/错误及关闭接线。`live.py` 保留先前候选的 extractor health/lifecycle，并补未停 shadow 的父级关闭保护。未修改 GUI、相机采集、公共 DPU scheduler/runtime、FPGA、显示、音频或运动。

## 显式配置

从原 Windows 身份配置创建独立候选文件，保留所有原字段，只追加：

```json
{
  "dpu_sface_shadow": {
    "enabled": true,
    "model": "/已校验/sface_public_int8.xmodel",
    "manifest": "/已校验/compiler-manifest.json",
    "model_sha256": "12b2ff5c7de157133ebd5aa71665fc5ddcd1f65d9e30e2d6e965e0752e467f25",
    "manifest_sha256": "d52e4343910f7d3c775405c161e3fdf16db27396891dc617b0e5defdb878841b",
    "max_source_age_ms": 1000,
    "interval_ms": 500,
    "compare_cosine": false
  }
}
```

以上是追加片段，需要改成真实已校验绝对路径。它只允许原 `feature_backend.kind=windows_sface` 与 `model_id=sface-2021dec-0ba9fbfa01b5`。`max_source_age_ms` 为 100..1500 且不超过原 result_ttl_ms；`interval_ms` 为 500..5000。缺省不创建 shadow；显式关闭写 `"dpu_sface_shadow":{"enabled":false}`。本目录没有生成或改写任何生产配置。

shared owner/schedule/current_target 与相机锁由 create_service 注入。runner 的模型哈希、manifest 哈希、目标 fingerprint、精确 INT8 I/O 均由冻结的适配器校验。冷启动或 artifact/推理异常只出现在 shadow health，Windows 主身份继续工作。

## 统计

`identity.feature_inference.shadow` 提供有界队列、运行、丢弃、失败、stop_requested/stopped 状态；累计 `accepted_latency_ms` 和可选 `same_crop_cosine` 仅含 count/mean/min/max，不含逐帧、姓名、目标、图片或向量。

目标变化或超时的任务不进入 accepted 时延/余弦汇总；`stale` 计数增加。`execution.completed` 仍准确表示实际 DPU 完成，即使该输出后来过期。两者须分别展示。公共 scheduler.calls 是准入区间，不能代替实际 completed。`templates_written` 与 `identity_decisions_from_shadow` 恒为 0。

同图 FP32/INT8 余弦只衡量该图特征一致性，不能宣称识别准确率、误识率或现场阈值已通过。

## 关闭边界

只停止 shadow 时，Windows 主身份继续工作。shadow worker 自己等待在途调用并关闭自己的 runner，不触碰 owner。`close(timeout)` 只在真正停止后返回 true；health.closed/stopped 也仅在 runner 关闭流程结束时为 true，stop_requested 单独表示已请求停止。

CameraFaceExtractor.close 最多等 2 秒并返回明确 bool。若未停，IdentityService 记录 shutdown_incomplete；父级 close 会抛 `Shadow inference has not stopped; keep the shared DPU owner open`，不能把它当关闭成功后释放/复用共享 owner。worker 真正停止后可重试 close。若原生 VART wait 卡死，Python 线程不能安全取消；需停止原服务进程并等待其完全退出后，再启动新 owner，禁止第二个 owner 绕过保护。本轮未遇到或实测硬件卡死，这是代码的已知恢复边界。

## 验证与未验证事项

运行 `python3 -B run_tests.py`，使用本机既有 Vitis AI CPU 容器，无网络、只读源码挂载，无板卡/真实图像/身份数据。实际结果见 `test-results.txt`。

16 项必要回归覆盖：Windows 返回不等待慢 shadow、失败/busy/关闭不改变主向量和 KNOWN、原 FP32 库 SHA/revision 不变、不新建任何 INT8 库、默认不创建线程、单在途+单 pending 与替换、输入不可变副本、限频、锁竞争立即丢弃、源过期/换目标不发布时延或余弦、runner 初始化/运行错误隔离、正常关自身 runner 不关 owner、关闭超时明确未停、父级禁止未停后释放 owner。新增验证无余弦时远端异常仍运行 shadow 且原异常对象不变、有余弦时远端失败不投递、不论模式成功每包只投递一次。

首轮测试有 3 项失败：测试未确认 nonblocking 投递成功即等待执行，恰逢初始化锁竞争导致包被合法丢弃。已修正测试同步为确认投递成功再等待；不改变生产的非阻塞丢弃规则。最终结果以本目录最新实际日志为准。

尚未验证：本候选上板导入/配置、与 YOLO+YuNet 真实实时协同、模型冷启动对主业务的影响、Windows 8792 当前连通性、实板长期稳定与净 CPU/DPU 收益。需要主负责人按备份/回退流程集成，再记录真实 completed 和主身份业务一致性。
