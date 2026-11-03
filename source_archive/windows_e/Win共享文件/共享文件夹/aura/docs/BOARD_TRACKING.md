# KV260 人体跟踪与目标选择（2026-10-11）

当前 YOLOX-Nano / B4096 人体检测后接入 ByteTrack 作者版本的 NumPy 适配，预览保持独立。显示真实观测框、轨迹编号、置信度和人数；编号不表示身份。实测与改动文件见 [接入报告](/home/ghmd/aura-board-tracking-20261011/TRACKING_REPORT.md)。

后续[真人现场验收](/home/ghmd/aura-board-tracking-20261011/REAL_TRACKING_ACCEPTANCE_REPORT.md)已取得有效选人回执，#97/代次2保持40/40新鲜样本（约6秒）；后续45秒193样本中新的可见轨迹未继承丢失的手动绑定。失跟发生在后续首个采样之前，未连续捕获完整物理出入画。近距离仰拍和移动仍有明显失跟，应先固定相机并让上半身完整入镜；多人交叉/受控遮挡和长稳仍待验收。

在“互动”页点“放大画面”查看框；在“设备”页点“选择目标”，再选当前人体编号。选中框为绿色，其他可见框为黄色。单人连续确认后可自动成为目标，多人需要手动选择。手动目标丢失清除选择，不自动转给另一个人；重入需再次选择。短暂丢失后可能保留编号，但 `track_generation` 递增，旧绑定不能继承；超过 500ms 无真实观测时，关联前结束旧轨迹。

固定 [作者源码](https://github.com/FoundationVision/ByteTrack/tree/d1bf0191adff59bc8fcfeaa0b33d3d1642552a99/yolox/tracker) commit `d1bf0191adff59bc8fcfeaa0b33d3d1642552a99`，保留 [MIT 许可证](../board/vision/bytetrack/LICENSE)、[原始 SHA/URL](../board/vision/bytetrack/upstream_manifest.json)。这是作者源码的板端适配，没有接入 ReID。

- 保留高分关联、低分救回、未确认轨迹、重激活和重复轨迹处理；删除无关 Torch 导入。
- NumPy Cholesky/solve 替换 SciPy；精确 Hungarian 可选匹配替换 LAPJV，未匹配代价为阈值一半；独立小矩阵穷举对照通过。IoU 保留作者包含边缘约定，没有改成贪心匹配。
- 高分阈值 0.5、新轨迹阈值 0.6、匹配成本阈值 0.8；低分阶段使用高于 0.1 的候选。预测只参与关联，对外发布当前检测测量框，不将失跟预测作为新观测。
- 时间步为实际采集时间差 × 标称 10Hz，过程噪声按步长缩放；此适配仍需真实数据标定，长间隔先结束过期轨迹。
- 最多 16 个当前检测、32 个暂失轨迹；超容量结束较旧暂失轨迹，历史随活动/暂失轨迹清理。两次连续输出确认后才开放选目标。

实现：[person_bytetrack.py](../board/vision/person_bytetrack.py)、[作者适配目录](../board/vision/bytetrack)、[相机服务](../board/vision/ui_camera_service.py)。配置固定跟踪源码 SHA，无自动回退 IoU。

[board_camera_ui.json](../config/board_camera_ui.json) 使用低分候选。相同 xmodel 复制到 `/home/root/aura-bytetrack-20261011/models/yolox_nano_person.xmodel`，配套 [prototxt](../models/dpu/yolox_nano_person.prototxt) 置信度下限 0.1、原 NMS 0.65，人体 NMS 仍为 0.45。未修改原预置模型/prototxt，未训练、量化或编译新模型。prototxt SHA256 `e3359212356578053b71a844ab10d82617d80c33274bb926875c3f422b6de611`；xmodel SHA/指纹延续 [YOLO 基线](BOARD_YOLO.md)。参考图自检以分数 ≥0.3 计数，低分候选不作为精度提升证据。[原 YOLO/IoU 配置](../config/board_camera_ui.yolo_iou.json) 保留作明确回退。

实际运行更新 `33fd4bc855871500`、启动器 `abd3df01b6d50a3b`，备份 `/home/root/aura-bytetrack-20261011/update-33fd4bc855871500/backup`。首次验收辅助脚本存在模块命名冲突；修正版配套包 `ea926df36eb116cd` 的 37 个运行文件与已运行版本一致，只修正验收辅助文件，未重复安装业务代码。配套包依赖既有素材、库和预置模型，旧完整素材包未重建。

12 项新增跟踪测试覆盖低分关联、时间步、测量框、失跟/重入、多人选择、重放拒绝、容量和独立最优匹配对照。首次接入131 项主机相关测试、80 项板端软件测试通过，当时全量主机回归另有 7 项 `test_cached_voice.py` 接口错误，原日志保留。2026-10-15 已恢复 `VoiceWorker(cached_only=True)`，当前完整框架 149 项通过，详见[采录与缓存修复报告](/home/ghmd/aura-media-integration-20261015/REPORT.md)；不是本轮重跑旧板端80项。

多人交叉/遮挡、远距离/低照度精度和长稳仍需现场数据验收；软件回放不代替多人实测。身份、统一主服务、正式模型构建、机构及本版本冷启动单列。
