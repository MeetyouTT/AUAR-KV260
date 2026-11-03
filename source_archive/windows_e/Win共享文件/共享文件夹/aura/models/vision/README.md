# CPU 参考视觉权重

本目录两份权重从已有本地 KV260 适配/身份参考实验复制，没有重新下载、训练、量化或编译。模型 ID、路径和 SHA256 以 `config/model_manifest.json` 为准，框架测试和 `doctor` 会校验本地副本。

| 文件 | 用途 | 限制 |
|---|---|---|
| `yunet_2022mar.onnx` | CPU 人脸检测和五点关键点 | 不是项目 DPU 人体检测 |
| `sface_2021dec.onnx` | CPU 人脸特征参考 | 不是已完成的共享 DPU 身份模型 |

真实 CPU 后端复用既有 OpenCV 适配。模型文件校验通过不等于本轮执行推理；本轮系统 Python 缺 OpenCV/NumPy，未运行 CPU 图像推理。

项目检测 xmodel、DPU 架构指纹、专用前后处理、项目身份模型和 Light-ASD 权重尚未纳入框架。正式比赛发布前需按原模型来源补齐模型卡、许可和再分发核验，旧总许可记录位于 `docs/LICENSE_MATRIX.md`，不能自动覆盖新模型。
