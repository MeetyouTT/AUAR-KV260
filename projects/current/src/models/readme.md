# 模型与外部输入

YuNet 2022mar、SFace 2021dec 的两份原始 ONNX 位于 `vision/`，以 `src/config/model_manifest.json` 为校验依据。原项目的固定版本是 OpenCV Zoo `c97242ce7f2a554e288b50eabd9f5df957e78801`，原许可见 `vision/licenses/`。`build/prepare_models.py check` 验证两份输入；框架 doctor 检查模型可定位性。

正式板端三模型为 YOLOX Nano、YuNet 与 SFace，对应 SHA 见 `board/deploy.json` 的 `external_inputs`。YOLOX 取自指定 KV260 镜像中的 `/usr/share/vitis_ai_library/models/yolox_nano_pt/yolox_nano_pt.xmodel`，可在 Ubuntu 上只读导出。文件大小 2,127,303 字节，校验后可作为离线部署输入。

```sh
debugfs -R "dump /usr/share/vitis_ai_library/models/yolox_nano_pt/yolox_nano_pt.xmodel $OUT/yolox_nano_person.xmodel" "$ROOTFS_EXT4"
sha256sum "$OUT/yolox_nano_person.xmodel"
```

`adapt/` 收录原始重建、适配、校准、评估和编译代码。`calibration/arch.json` 固定 DPU 指纹 `0x101000056010407`，其余报告保留各自原始验证口径。准备可合法使用的公共 LFW 基准并将其留在共享工程之外。`fetch-lfw` 会校验归档和两份划分文件的 SHA。校准需要锁定 ID 的 Vitis AI CPU 镜像，容器环境若缺 ONNX，可将与其 Python 3.7 环境匹配的 `onnx==1.12.0` 放入单独目录，通过 `--python-deps` 只读挂载。镜像标识在 `build/env.json`。

```sh
python3 -B build/prepare_models.py fetch-lfw --out "$PRIVATE_DATA/lfw"
python3 -B build/prepare_models.py quantize --lfw "$PRIVATE_DATA/lfw" \
  --python-deps "$ONNX_DEPENDENCIES" --kind both --out "$OUT/models"
```

原 `hardware_vectors.py` 会把真实基准图像和模型输出写进 NPZ，并明确要求留在本地。`calibration/vectors/references.json` 只记录两个原文件的 SHA 和大小，持有相应输入时可用该脚本在同一容器生成。本次生成的量化与编译结果应与历史结果分别记录，精度与现场表现还需板端测量。

`inputs/host_llm.json` 锁定 27B GGUF 的仓库、revision、文件名、字节数和 SHA。`host_tts.json` 与 `host_tts_files.json` 固定 OmniVoice 的 revision 和 11 个文件，`board_audio_dependencies.json` 固定独立板端语音附件的 15 项。主机工作树生成后在其根目录运行 `python prepare_weights.py --gguf <文件> --tts-cache <目录>`，只使用已有模型。GGUF 和 Ollama 模型库放在源码共享目录以外。

本轮已经在锁定的 Vitis AI 镜像中重新执行两模型的校准、公共划分评估、batch-one 导出与目标编译，实际回执见 `report/evidence/model_build.json`。两份新候选图的 SHA 与 9a4f 的既有部署输入分别记录，正式业务清单切换前需要独立做板端验证。
