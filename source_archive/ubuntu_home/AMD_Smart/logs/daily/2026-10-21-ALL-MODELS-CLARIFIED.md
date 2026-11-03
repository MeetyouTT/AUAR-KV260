# 全部模型职责与计数纠正

2026-10-21洛杉矶，UTC22日03:21后。用户表示全部模型仍不清晰，要求仔细分析。重读ZIP README、旧总清单/manifest/模型卡、语音源码/权重、共享入口与最新日志，三次UART只读查询当前audio-frontend实际源码、配置/状态及无音频健康接口。

发现此前六项清单不完整：遗漏当前已配置GTCRN gtcrn_simple.onnx与Silero VAD v5。实际board_avatar_gtk.json audio_frontend.enabled=true、192.168.50.1:8795；自动对话/打断相关开关为true。主机源码固定两份SHA、CPU/sherpa-onnx，GTCRN降噪仅供Silero判speech，协议仅回布尔/样本时间线，原始录音仍交Paraformer，不能称ASR已吃降噪音频。界面IDLE/current前端状态为空，8795健康超时，未发音频或证明主机在线，权重在本地镜像未找到，大小留未知。

当前按功能统计8项：YOLOX、YuNet、SFace、GTCRN、Silero、Paraformer、27B文本对话、OmniVoice。独立列OmniVoice音频tokenizer组件；Light-ASD与VLM是待接能力；历史/研究候选和运行时/算法不混算。SFace ONNX/xmodel是同任务部署版本，16步是生成参数。27B本地标签qwen3.8与元数据family qwen35不同，只按本地标签标识，不宣称已核验官方型号或视觉能力；原始GGUF旧记录14.40GB与Ollama记录13.89GB来源不同，本轮未Windows文件比对。

新增[完整概览](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_model_inventory/全模型概览_当前.md)与过滤证据，纠正本日原清单与DPU表的漏项，给10-18历史清单加当前入口，保留历史原表/实测。三次响应SHA/长度及回显恢复通过，本轮未改生产源码/配置、部署模型、重启、录音/采脸或新推理；Windows同步/在线驻留与完整真人业务验收仍未确认。
