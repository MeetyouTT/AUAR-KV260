# 实测比较所用参考

`yunet_compiler_manifest.json`、`sface_compiler_manifest.json` 固定历史 DPU 图、指纹和张量接口，原编译时的 board_tested 字段保留原语义。后续真实板端观察分别保存在 board/evidence。

`yunet_synthetic/` 收录原向量档案中两个确定性合成输入及其宿主量化参考。`.bgr` 为320×320×3 uint8 BGR，`.i8` 为manifest声明的INT8输出张量。文件形状、张量名和SHA均可核对。原验证判据为整数最大差不超过1 LSB。

`dpu_crosscheck.public.json` 与 `performance_summary.public.json` 是旧测量统计参考。离线比对脚本从实际数值样本重新计算，并检查逐例误差。
