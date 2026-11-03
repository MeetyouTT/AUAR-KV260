# AURA 当前模型清单核对

日期：2026-10-11。依据 ZIP README、最新板端日志、共享模型清单、语音源码及同日 Windows 语音交接记录。此次为只读盘点；未连接 Windows/板卡查询当前进程，未复跑推理或全部权重哈希。

## 关键更新

10 月 11 日新增共享资料明确：已接受的 TTS 是 **k2-fsa/OmniVoice 16 步**。10 月 8 日日志中 Qwen3-TTS 1.7B Base 作为最新语音方案的描述已被此记录更新；Qwen3-TTS 保留为历史声线/性能对照。

用户说当前 Windows 部署千问 14B。共享验收包则固定 Qwen3 4B 快速配置，同时保存 14B 对比记录和切换方式。应区分用户当前运行配置与交接默认配置，不据离线文件断言用户已经换为 4B。14B 历史精确标签已从 fast14b_benchmark.json 定位到 `huihui_ai/qwen3-abliterated:14b`；用户当前服务是否仍为该标签待运行时核验。

## 主线与参考模型

| 模型 | 用途 | 位置与证据状态 |
| --- | --- | --- |
| YOLOX-Nano / yolox_nano_pt | 人体框、置信度、人数 | KV260 B4096 DPU，已真实相机验证；当前仅 person 类，不做身份判定 |
| YuNet 2022mar | 人脸检测、五点关键点 | KV260 ARM CPU 已有实时历史验证；保留参考/身份前处理链，不能称当前与 YOLO 同时常驻运行 |
| SFace 2021dec | 128 维人脸身份特征 | KV260 ARM CPU 板端图片参考链通过；实时登记/识别完整业务未验收，未在 DPU 上加速 |
| Qwen 14B；历史标签 huihui_ai/qwen3-abliterated:14b | 文本理解、多轮回复 | Windows；用户报告当前部署 14B，共享目录有对应历史测试，不声称本轮读取在线模型 |
| qwen3:4b-instruct-2507-q4_K_M | 较小文本对话模型 | Windows 10 月 11 日语音交接包默认配置；不是与 14B 必须同时运行 |
| sherpa-onnx-paraformer-zh-2023-09-14，model.int8.onnx | 中文语音转文字 | 最新 Windows 链为 CPU、2 线程；本地共享可见 ONNX 与适配代码，sherpa-onnx 是运行框架 |
| k2-fsa/OmniVoice | 文字转汐蓝固定声线语音 | 最新 Windows GPU TTS 基线；16 步、float16、SDPA，用户声音效果接受记录；板端部署未验收 |

14B/4B 记录是文本对话链，尚未据此确认视觉语言模型；不能假定可直接接相机图像。语音合成的不同步数或声音参考不另计独立模型。

## 历史、测试与规划

- Qwen/Qwen3-TTS-12Hz-1.7B-Base：历史 Windows TTS 与 OmniVoice 对照，已有生成记录。
- VITS AISHELL3、Kokoro INT8：早期 TTS 候选，共享目录可见权重/试听文件，不是最新选择。
- goonsai/qwen2.5-3B-goonsai-nsfw-100k:latest：历史本地 3B 对比；README 记载专名记忆错误，未采用。
- ResNet18：历史 DPU 平台分类测试，不是当前人物交互主模型。
- MobileFaceNet：计划中的轻量 DPU 身份候选，未固定与验收；ArcFace 为身份训练方法，不单独计作已部署推理网络。
- Light-ASD：主动说话人模型，规划 Windows 运行；现有清单仍为接口已定义、模型未集成。
- ByteTrack：跟踪算法，有适配基础、未接入当前 YOLO 实际服务；不计作已部署的第二个 DPU 神经网络。当前 YOLO 服务使用 IoU 基础关联。
- 当前语音交接入口是按键结束录音，不能把其他模块中的 KWS/VAD 接口计为此链已部署神经网络。

## 证据入口

- [YOLO 接入](/home/ghmd/aura-board-yolo-20261011/YOLO_INTEGRATION_REPORT.md)
- [模型旧清单](/home/ghmd/Win共享文件/共享文件夹/aura/config/model_manifest.json)：其 project-person-dpu pending 状态被独立 YOLO 接入证据更新，统一框架仍待整合。
- [语音接受记录](/home/ghmd/Win共享文件/共享文件夹/deliverables/2026-10-11_voice_accepted/acceptance.json)
- [语音交接](/home/ghmd/Win共享文件/共享文件夹/deliverables/2026-10-11_voice_accepted/HANDOVER.md)
- [对话配置及历史比较](/home/ghmd/Win共享文件/共享文件夹/deliverables/2026-10-11_omnivoice_dialogue/README.md)
- [ASR 源码](/home/ghmd/Win共享文件/共享文件夹/aura/board/runtime/audio/asr.py)

共享源机器称完整权重保存并校验通过，不等于本 Ubuntu 副本已同步全部大文件。此次新增本盘点日志，未改变默认模型、配置、旧日志或运行服务。
