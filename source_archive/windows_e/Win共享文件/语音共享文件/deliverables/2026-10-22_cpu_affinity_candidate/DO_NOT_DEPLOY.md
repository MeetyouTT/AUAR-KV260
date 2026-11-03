# 审查未通过：本版不可部署

2026-10-22主任务在最终与实板证据交叉核对时发现：本版`camera-face-targets`固定SHA为迁移前的`8d0270f2…`，而实际保留生产及14源候选复制的人脸服务为`d03e2aee…`。它会在启动校验阶段拒绝运行，没有上板或改变生产。

本目录作为审查过程证据保留，原FILES.sha256覆盖的20份内容不改写。新增此拒绝记录不表示原候选通过。修正版将单独发布到`2026-10-22_cpu_affinity_candidate_r2`，以共享任务入口最终链接为准。

独立依据为`../2026-10-22_gil_interval_trial/evidence/final-active-audit.json`中的实板source_hashes，以及原迁移源`../2026-10-21_dpu_vision_start/candidate/aura/board/identity/face_targets.py`。后续打包必须逐一比较实板基线和14源覆盖清单，不仅比较候选内部参考源与固定值。
