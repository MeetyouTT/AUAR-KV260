# 2026-10-17 ASR同步依赖与Ubuntu文件核对

用户在微力同步四文件补丁后追问还需哪些文件、Ubuntu上有哪些缺失。阅读ZIP README、当前导航、既有语音交付清单、ASR真实导入和启动脚本，按当前录音转文字路径核对。未取得Windows目录，未声称两机全量差异已检查。

## 当前确认

本次ASR完整必需清单为8份源码/说明、3份模型数据：原4文件外，还需既有board/runtime/audio/asr.py、audio/runtime/common三个包初始化文件；模型需model.int8.onnx、tokens.txt、test_wavs/0.wav。0.wav用于真实启动探针，不是可省略的测试附件。

Ubuntu11项均存在且SHA匹配，3份模型合计243626686字节。当前隔离环境Python3.8.10、numpy1.24.4、sherpa-onnx/core1.13.8，包元数据检查通过。未安装torch/omnivoice/transformers于该ASR环境；PATH未找到ollama/nvidia-smi，不把这当作全盘未安装或硬件缺失的证据。

重新按已接受的model_files.json、baseline_files.json对31项交付文件逐项长度/SHA校验，31/31通过。包括OmniVoice、Qwen3 4B和ASR模型、参考与冻结资料；本轮不等同于完整LLM/TTS运行通过。

## 交付与验证

在原共享交接目录新增 `asr-host-complete-code-b9ac9d83fe24f179.zip`，12549字节，SHA256 `1d07cc2b30848a07f9c454e8d149c48a5647a71167ef93c57bfef1c7a4268255`。8份源码加必需文件清单，不含模型权重，原四文件ZIP保留。CRC、逐字节回读通过。

将新包解压到临时隔离目录，用-I -B实际实例化包内Paraformer服务，确认ASR/wire从隔离包加载，外部真实模型样例识别成功；模型身份paraformer-f36a0433bcf096bd6d6f11b8。没有联网监听或新板端操作。Windows运行未验收。

同步目录增加 `ASR_REQUIRED_FILES.json`、`check_asr_files.py`、`ubuntu_inventory.json`、`isolated_code_validation.json` 和 [完整清单](/home/ghmd/Win共享文件/共享文件夹/deliverables/2026-10-17_board_asr_host_files/FULL_ASR_CHECKLIST.md)。校验器使用标准库，支持Windows侧按实际aura目录输出MISSING/DIFFERENT/MATCH，不覆盖文件。本机11/11及依赖元数据通过。

工作证据 `/home/ghmd/aura-sync-inventory-20261017/inventory.json`、`isolated_validation.json`；模型与语音完整交付SHA重验的逐项结果也已复制进微力共享交接目录。

## 共享之外与限制

Ubuntu的AMD_Smart计划/日志、下载/项目.zip、aura-asr-integration-20261016报告/串口证据均在共享根之外，不会仅因同步共享根就自动覆盖。已在清单中注明，未擅自复制整个环境或全部历史证据。

本轮只生成依赖清单、检查脚本和源码补充包。没有改业务运行源码、密码/密钥、板卡网络、GUI/相机/运动服务或Windows环境；板端跨机实时转写仍待服务联调。
