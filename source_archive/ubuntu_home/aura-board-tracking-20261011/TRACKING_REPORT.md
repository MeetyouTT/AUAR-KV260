# KV260 ByteTrack 接入实测（2026-10-11）

后续现场验收（UTC 2026-10-12）见 [真人跟踪与目标选择报告](REAL_TRACKING_ACCEPTANCE_REPORT.md)：真实点选 #97、新受理回执及40/40选中保持通过；后续新轨迹不继承已丢失的手动绑定。近距离仰拍仍有失跟，多人/受控遮挡待验。下文保留首次接入时的无人状态和原始软件验证记录。

已在当前 YOLOX-Nano / B4096 真实相机链运行作者版本 ByteTrack 的 NumPy 适配，继续独立预览。单人连续确认后可自动成为目标，多人手动选择；手动目标失跟清除选择，重入不继承旧生命周期。**真人选目标本轮未验收**，最终截图中镜头朝向天花板、人数为 0。

依据 ZIP README、视觉手册 B05/B12、10 月 8 日框架和最新 YOLO 日志；当前仍由 A 负责视觉/FPGA，旧 B 编号仅追溯。

改动文件：

- [person_bytetrack.py](/home/ghmd/Win共享文件/共享文件夹/aura/board/vision/person_bytetrack.py)：真实时间/帧号、500ms 失效、代次、测量框、容量及目标策略。
- [bytetrack 目录](/home/ghmd/Win共享文件/共享文件夹/aura/board/vision/bytetrack)：固定作者 commit `d1bf0191adff59bc8fcfeaa0b33d3d1642552a99`，保留 MIT 和原 SHA；NumPy/Kalman、精确 Hungarian 适配。来源见 [原始清单](upstream_manifest.json)。
- [相机服务](/home/ghmd/Win共享文件/共享文件夹/aura/board/vision/ui_camera_service.py)、[DPU 适配器](/home/ghmd/Win共享文件/共享文件夹/aura/board/vision/yolo_dpu.py)：后端、自检、实际状态及低分候选。
- [配置](/home/ghmd/Win共享文件/共享文件夹/aura/config/board_camera_ui.json)、[旧配置](/home/ghmd/Win共享文件/共享文件夹/aura/config/board_camera_ui.yolo_iou.json)、[prototxt](/home/ghmd/Win共享文件/共享文件夹/aura/models/dpu/yolox_nano_person.prototxt)：固定来源与阈值，保留回退。
- [12 项跟踪测试](/home/ghmd/Win共享文件/共享文件夹/aura/tests/framework/test_person_bytetrack.py)、[包收集器](/home/ghmd/Win共享文件/共享文件夹/aura/tools/package_board_avatar.py)、[启动目录](/home/ghmd/Win共享文件/共享文件夹/aura/scripts/board_ui_startup)、[操作说明](/home/ghmd/Win共享文件/共享文件夹/aura/docs/BOARD_TRACKING.md)及入口文档。

板端 NumPy 1.21.2 可用，SciPy/lap/cython_bbox/Torch 不可用，故保留作者高/低分关联等路径，替换线性求解/匹配依赖；48 组小矩阵与独立穷举最优解对照通过。时间步为实际采集时间差 × 10Hz、过程噪声按步长缩放，仍需真实数据标定。对外发布当前测量框，预测只参与关联。最多 16 当前检测、32 暂失轨迹，旧暂失超容量时结束。不是未修改原版，也未接 ReID。

原 xmodel 相同字节复制到 `/home/root/aura-bytetrack-20261011/models/yolox_nano_person.xmodel`，SHA `def64abdeeccbd020cb651913ba907464c1a1786e30ba7d4aa077b601388950a`、实时指纹 `0x101000056010407` 不变；独立 prototxt 下限 0.1，SHA `e3359212356578053b71a844ab10d82617d80c33274bb926875c3f422b6de611`。原预置文件未改，未训练/量化/编译新模型。新轨迹阈值 0.6、关联高分 0.5，低分只救回既有目标。

实际运行更新 `33fd4bc855871500`、启动器 `abd3df01b6d50a3b`；[部署记录](evidence/20261011T141332.867663Z-deploy/deploy.json)。备份 `/home/root/aura-bytetrack-20261011/update-33fd4bc855871500/backup`。只重启自身相机/GUI，80 项板端软件、资源/启动预检通过；固定图分数 ≥0.3 人体 4 个、黑图 0。

首次界面验收因辅助模块同名无法导入 `click`，实时服务正常。修正助手后暂存验收包 `ea926df36eb116cd`，其 37 运行文件 SHA 与实际安装版本一致、启动 ID 相同，没有重新安装业务代码。验收元数据保留原实际安装 ID，并另记验收包 ID。失败记录保留。

[修正版配套包](/home/ghmd/Win共享文件/共享文件夹/aura/artifacts/releases/aura-bytetrack-update-ea926df36eb116cd.zip) 150601 字节，SHA `e5f3269cbeb19b2c28792f589b4f13b5b81471311e6fc54e55685c93be042074`；46 载荷和 manifest，37 运行文件。[清单](manifest.json)、[包记录](package_validation.json)。依赖既有素材、库和模型；旧 217MB 素材包未重建。收集器 917 文件通过，直接验证已有缓存，不依赖变更后的 VoiceWorker，也不启动合成；[记录](collector_validation.json)。

主机 Python 3.8.10 / NumPy 1.24.4 独立环境，12 新增跟踪测试通过；[131 项相关测试](host-tracking-and-unaffected-tests.log)通过。初始全量 137 项有 7 项 `VoiceWorker(cached_only=True)` 接口错误，[原始失败](host-full-framework-known-failures.log)保留，本轮未改语音源码，**不是全量回归通过**。初次独立环境缺 Pillow 的失败保留，随后沿用系统依赖完成相关测试。

同一 boot 前后各 120 次短采样：

| 指标 | 原 YOLO/IoU | ByteTrack |
| --- | ---: | ---: |
| 实际预览 | 18.93fps | 19.46fps |
| 实际检测 | 10.00Hz | 9.91Hz |
| 实际采集 | 26.95Hz | 25.23Hz |
| API 帧龄中位 / P95 | 216 / 309ms | 188 / 277ms |
| 原生入口帧龄中位 / P95 | 89.92 / 125.10ms | 81.01 / 120.88ms |
| 相机 CPU，单核满载=100% | 120.5% | 114.0% |
| 空画面样本 | 0 / 120 | 0 / 120 |

[接入前采样](evidence/20261011T135724.742699Z-probe/probe.json)、[最终状态/界面/采样](evidence/20261011T142122.912057Z-final/final.json)。仅短窗口，帧龄不是物理面板端到端延迟，不推断长期性能。

原生放大 960×550/返回、五次诊断无 GUI 重启、设置保留通过。[主界面](evidence/20261011T142122.912057Z-final/main_screenshot.jpg)已查看，镜头向天花板、人数 0；[放大图](evidence/20261011T142122.912057Z-final/screenshot.jpg)。20 秒没有确认目标，真人选择分支未执行；已请求用户入镜，尚未得到回复。

相机唯一拥有者 PID 451135，GUI 451151、监督 451138；两个服务 active/running/enabled、NRestarts=0，source_kind=actual、DPU READY、BYTETRACK_PINNED_NUMPY。音量 58%、非静音/全屏/非省电保持。boot `9223af18-5113-4486-822f-29ec94d03d3e`、显示/DFX 与保护文件保持；未重启整板、未加载 PL、未发运动命令。

[独立核验](validation_final.json)：68 份 UART 响应长度/SHA，其中 1 份为已解决助手错误；2 工件、46 包载荷、37 源码/运行 SHA 一致。

下一步现场把镜头朝向人，验证移动、遮挡、出入画和设备页选择；多人精度、长稳、身份、统一主服务、新版本冷启动、物理面板延迟与机构仍单列。
