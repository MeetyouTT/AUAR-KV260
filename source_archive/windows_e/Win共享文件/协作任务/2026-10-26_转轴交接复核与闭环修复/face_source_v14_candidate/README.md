# v14 候选：固定实锚光流特征懒提取

本目录继承v13离线候选，只改变特征准备时机；v13已冻结的运行源和manifest未修改。本分支未访问板卡、UART、相机/DPU/MMIO或运动服务，未部署。主agent独占所有实板操作。

主agent实际KV260隔离bench发现v13锚seed约37.044ms；旋转缩放fallback中位49.324ms/最大80.180ms。该数据由主agent保存，本子agent未直接接板，不能将x86微基准代替它。为避免每约100ms检测锚更新都强制付出特征提取成本，v14的seed仅保存原检测锚灰图、固定crop和box；普通full NCC及边缘双块成功时完全不调用goodFeaturesToTrack。

只有首次需要LK回退，才从原anchor_gray提取最多40个固定ROI特征；在同一锚状态中缓存point数组，提取失败的None也缓存。不会从当前图像补点，不会滚动模板或延长原锚；新的真实检测锚才建立新的缓存。v13的前后向、几何、空间支撑、NCC≥0.80及250ms当前图/500ms真检测锚期限保持。

51项主机回归通过（v13的48项＋3项懒提取检查）：seed/普通平移零特征提取、首次回退仅从原图提取一次并复用、失败None不反复计算/不从当前图重建。无相机/DPU/执行器。`validation.json`明确候选及未部署范围。

独立`board_synthetic_benchmark.py --baseline-root BASE --candidate-root CAND --iterations 5`与v13相同，可单进程隔离运行。Host单线程OpenCV样本：candidate seed0.052ms、平移中位0.292ms；旋转缩放中位1.500/max2.695ms，11项正反例全部通过。这些只供核对逻辑与API，KV260代价须主agent重测。首次fallback仍需支付提特征和LK成本，不宣称所有路径都更快或实时跟随已通过。

运行源为entry/face_flow/face_observation/face_lock/face_timing/raw_capture，共8个manifest pins（包含既有operator和face扩展）；`face_tracking.version=11`测量协议兼容、`algorithm_version=14`。detector_timing继承v13的有界逐source包装：native_lease不是纯DPU核耗时，不改变调度、SFace频率、故障预算。其完整审查背景见兄弟目录v13 README，当前候选只增加懒提取。
