# 整个项目模型总盘点

用户纠正范围为“这个项目全部的模型”。本轮重读ZIP现行方案第13/25章、既有模型盘点，核对两工作根配置、语音最新记录/健康证据、当前权重文件列表、ASR与对话请求源码、历史KWS模型卡。

已固定名称六项：YOLOX-Nano、YuNet、SFace、Paraformer、当前27B本地标签、OmniVoice。只有YOLO明确在现有DPU业务中集成；YuNet/SFace为CPU参考及未上板身份候选，SFace DPU仍仅初检；语音三个模型已有Windows实际链路记录。Light-ASD仍待集成；看图VLM型号/后端未验收，当前文本调用没有images，不能把27B文本回答当作视觉问答。

另列历史Zipformer KWS、旧4B/14B/3B、Qwen3-TTS/VITS/Kokoro、SenseVoice、未采用身份候选和ResNet18基准。特别注明ByteTrack、EnergyVad及Streaming ASD/LoCoNet/Neural Simplex思路不计为已部署独立模型。

新增[共享模型总清单](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-18_identity_dpu/整个项目_模型总清单_20261018.md)。本轮未改生产源码/配置/模型，未推理、编译、部署或重新读取板卡/Windows；只核对本地资料与保存证据，校验文档本地链接，不运行产品测试。
