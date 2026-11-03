# 主机模型服务接口

此目录复用已有 `aura_fpga/host/model_service` 的 `protocol.py`、`pipeline.py`、`backends.py`，只统一 LF 换行。导入前后 SHA 见 `config/source_import_manifest.json`。框架新增 `client.py` 有界异步工作线程，并将媒体合同接入板端统一运行时。

## 可运行入口

```bash
python3 -s tools/aura_host.py
```

此入口执行 `FixtureAsr`、`FixtureVlm`、`FixtureTts` 三阶段和板端交付检查，`is_fixture=true`，输出 PCM 为测试信号。它没有执行真实识别、视觉问答或语音合成，也没有录音、播放或启动网络服务。

文字模式另用 `python3 -s tools/aura_project.py dialogue --text '你好'`。文字 `1.0` WebSocket 与 `aura-runtime-1` 媒体是不同合同，现有文字服务不能直接接收二进制媒体请求。

## 后端怎样接入

真实 ASR、VLM、TTS 分别实现 `backends.py` 中的 `AsrBackend`、`VlmBackend`、`TtsBackend`。每个后端需报告模型/实现 ID，`load()` 加载，`probe()` 使用实际功能探针；仅可导入或模型路径存在不能报告 READY。

```python
pipeline = ModelServicePipeline(actual_asr, actual_vlm, actual_tts)
health = pipeline.startup()
app.attach_media_backend(pipeline.handle)
token = app.ask_media(audio_ref, pcm_bytes, image_ref, image_bytes)
```

这里的 `actual_*` 需要团队提供，示例不是可直接运行的模型安装器。当前同进程 callback 已通过模拟联调；跨机器媒体传输、重连、MCP01 输入/输出和真实模型仍待实现。跨机器时，应在传输适配中解码为已有类型并保留字节、格式、哈希与归属，随后仍经过板端 `media_session.py`。

管线提供阶段耗时、准备状态、取消世代和有界成功结果缓存。新板端交付门进一步要求准确的当前代次、请求期限原值回显及 PCM 段完整性，不能用主机当前时间与板端绝对时间直接比较。启动归属目前使用运行时时钟实例 ID，运行时重建即换代。

真实回复仅在当前 token 有效时交付给 UI；PCM 仍需播放适配读取。取消、目标换代、相机失联和到期会使旧结果失效。当前 callback 取消并不保证底层正在执行的真实模型立即停止，只保证旧结果不能交付。

主仓已选定的汐蓝声线继续沿用。复用 `backends.py` 的 `CANDIDATES` 是历史候选说明，不能代替最新声线或 Windows 侧实测记录。
