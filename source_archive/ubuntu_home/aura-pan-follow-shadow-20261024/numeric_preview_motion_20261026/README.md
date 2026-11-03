# 缓存预览背景位移观测器

`preview_motion.py`是独立只读模块：不导入/调用执行器，只GET本机缓存状态、带camera_epoch/frame_id的JPEG及现有缓存人脸框。校验JPEG三个X-Aura响应头匹配状态引用，保留原`captured_mono_ms`与观测进程`sample_mono_s`，不把下载时间当采集时间；不保存照片、姓名或身份库。

用法：`observer = PreviewMotionObserver(duration_s=8, interval_s=.25).start()`；主终端可在ARM之前 `observer.wait_baseline(timeout_s=2.)`。ready_event仅表示首帧建立了基准，纹理不足也可能ready，须看baseline.state。既有控制器确认真实STOP后调用 `observer.close_after_stop(readback, timeout_s=1.)`。采样线程独立daemon，主控制不等网络/图像处理；join超时会如实报告observer_alive，不能当作已完成清理。

640×480缓存预览在内存灰度降至320×240；首帧固定角点，之后始终回第一帧做LK前后向检查、RANSAC及内点位移中值。屏蔽中央前景、边缘覆盖区域与当前有效脸框；背景点数、空间覆盖、内点比例、FB误差或变换质量不足，一律`UNMEASURABLE`且dx/dy为null，不用0冒充没动。输出位移换算回640×480像素坐标，不转换为舵机角度。

8项本地检查通过：已知8/−4、16/6像素移动和回原位均保持第一帧基准；移动中央前景不改变背景估计；脸区独有特征/无纹理不产生运动结论；错帧头/重复帧/换代拒绝；只输出可JSON化数字；关闭必须在STOP后且等待有界。验证使用本机OpenCV4.6.0/NumPy1.23.5，未接板，本模块还未用于实际镜头运动验收。

背景位移是图像证据，可能受场景、灯光、纹理和独立背景物体影响；即使输出接近0，也只能说本观察窗口未观测到明显镜头运动，不能据此认定舵机没电。该模块不更改r2控制器、参考、方向、边界或运动许可。
