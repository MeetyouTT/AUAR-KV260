# OpenCV 4.5.2 人脸参考链兼容层

`face_compat.py` 用现有 `cv2.dnn` 和 NumPy 提供 YuNet 检测、五点对齐、SFace 128 维特征及余弦比较。板端缺少两个高层接口，不升级板端系统/全局 OpenCV。每个实例归一个推理线程，图像输入必须为 uint8 BGR。

固定权重来自 OpenCV Zoo commit `c97242ce7f2a554e288b50eabd9f5df957e78801`：YuNet `2022mar` 和 SFace `2021dec` 的 FP32 ONNX。每次加载严格核验 SHA-256，拒绝拿新 YuNet 输出布局套用旧解码逻辑。检测固定 320×320 推理并把坐标还原为原图坐标；这个软件基线的拉伸策略需要在后续精度评测中记录。

API/后处理参考 OpenCV 4.6.0：

- https://github.com/opencv/opencv/blob/4.6.0/modules/objdetect/src/face_detect.cpp
- https://github.com/opencv/opencv/blob/4.6.0/modules/objdetect/src/face_recognize.cpp
- https://github.com/opencv/opencv_zoo/tree/c97242ce7f2a554e288b50eabd9f5df957e78801/models/face_detection_yunet
- https://github.com/opencv/opencv_zoo/tree/c97242ce7f2a554e288b50eabd9f5df957e78801/models/face_recognition_sface

相应来源及许可证保存在 `reference/`；保留了 OpenCV 4.6 的旧模型宽/高解码系数，以官方 API 数值对照为依据。SFace 的 BGR→RGB blob 转换和模型内归一化与官方一致，不能额外重复除以 255。

电脑对照环境独立安装在 `identity/.venv`，版本 OpenCV 4.6.0 / NumPy 1.23.5。在上一级工作目录执行：

```sh
identity/.venv/bin/python identity/verify_reference.py
identity/.venv/bin/python identity/compare_board.py
```

板端检查由上一级 `scripts/board_exec.py scripts/identity_test.py` 调用，使用已校验的独立文件，不打开摄像头、不加载/卸载 PL。固定图片验证只证明软件兼容与数值链路，不证明用户身份精度、生产帧率或 DPU 部署。模型状态仍为 CPU_REFERENCE；最终 DPU 身份网络必须另行量化、编译、板级验证。

2026-10-06 本机实测通过，证据由 `CURRENT_IDENTITY_TEST.json` 指向。板端/电脑坐标最大差 `3.0517578125e-05` 像素、特征余弦 `0.9999999086`。5 次预热测试中位数：检测 91.66 ms、对齐＋特征 304.31 ms、完整链 395.91 ms。这是固定图片、2 个 OpenCV 线程的小样本数据，不是生产 FPS 或尾延迟保证。

板端最小调用（已有 BGR 图像 `frame`，每个实例由单一推理 worker 使用）：

```python
from pathlib import Path
from face_compat import YuNetCompat, SFaceCompat

models = Path('/home/root/aura-adaptation-20261006/identity/models')
detector = YuNetCompat(models / 'yunet_2022mar.onnx')
recognizer = SFaceCompat(models / 'sface_2021dec.onnx')
faces = detector.detect(frame)  # N×15: x,y,w,h, five x/y landmarks, score
if len(faces):
    crop = recognizer.align_crop(frame, faces[0])
    embedding = recognizer.feature(crop)  # 128 float32 values
```

身份 worker 使用最新一帧、有限队列及观测时间戳；识别结束后重新核对轨迹/session/db_version，过时结果丢弃。此工作只提供参考算法后端，worker 调度、身份数据库、多帧阈值和正式运动接口将在后续集成中实现，不能把上面的 `faces[0]` 示例当成多人选人策略。
