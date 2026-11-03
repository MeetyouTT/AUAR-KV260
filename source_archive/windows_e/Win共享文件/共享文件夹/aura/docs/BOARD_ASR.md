# 录音结束后自动显示文字

GTK 本地录音在手动停止或达到20秒上限后，自动把16kHz、单声道、PCM16音频送入识别电脑的 Paraformer。文字显示在玩偶交流页“你说”区域，长文本可滚动。识别在后台执行，界面继续响应触摸和视觉预览。此步骤只做语音转文字，问答与语音回答仍待原服务接入。

## 启动识别电脑

Windows在 `aura` 目录可直接执行：

```powershell
.\scripts\start_board_asr.ps1
```

脚本从已验收语音的 `machine_config.json` / `stage_config.json` 查找实际存在的语音Python。换机器时显式指定 `-VoicePython 'C:\实际语音环境\Scripts\python.exe'`。看到 `READY` 后保持窗口打开；本轮无法远程运行Windows，入口只做了静态检查。

在 `aura` 目录使用已验收语音环境（Python3.10、sherpa-onnx1.13.8、现有numpy）执行：

```powershell
python -B tools/asr_server.py --listen 0.0.0.0 --port 8791
```

默认使用 `models/asr/sherpa-onnx-paraformer-zh-2023-09-14/model.int8.onnx`、CPU两线程。服务启动先识别模型附带的真实样例，成功后输出 `READY` 并监听。缺库、缺模型或探针无文字会启动失败。`GET /health` 返回模型身份和探针文字。

板卡和识别电脑需在同一局域网，识别电脑私有网络允许端口8791。Linux也可运行同一入口；本轮Linux隔离环境实际使用Python3.8、numpy1.24.4、sherpa-onnx1.13.8，未修改Windows语音环境。

## 配置板卡

在板卡运行时 `aura` 目录执行，替换示例地址为识别电脑的实际IPv4：

```bash
python3 -B tools/configure_board_asr.py --host 192.168.1.10
```

命令通过板端本机GUI控制接口保存配置，并等待后台确认；无需重启界面。配置保存在运行时根目录 `avatar_transcription_settings.json`。默认未配置，地址未知时不发送录音。若当前仍保留一段已完成录音，配置成功后会自动尝试转写该段。

暂停自动转写：

```bash
python3 -B tools/configure_board_asr.py --host 192.168.1.10 --disable
```

## 使用与失败行为

点击“开始录音”，说话后再次点击“停止录音”。界面依次显示正在录音、正在转写和识别文字。无文字时提示重新录音，网络、模型或协议失败时显示失败提示，详细原因保留在状态和文字提示中。

取消本轮或开始新录音会清除上一段文字，并使旧请求失效。板端最多一个网络请求、一条最新待发录音，单段0.2–20秒，默认总时限30秒。远端已开始的CPU推理会继续完成，旧结果不更新界面；服务忙时返回503。

## 协议与验证

独立协议 `aura-asr-1` 使用 `POST /v1/asr/transcribe`，body为原始PCM，`X-Aura-Asr`携带有界元数据。返回必须匹配boot/session/request/generation/capture身份、样本数与PCM SHA256，且为实际识别来源；不使用两机绝对时钟比较期限。请求最多640000字节，返回最多32768字节，文本最多4096字符。

`tests/framework/test_transcription.py` 覆盖停止/自然结束、取消/重录/最新队列、空结果、错归属、过期、断连、配置持久化和HTTP边界。单元测试引擎为fixture；真实模型与已采板卡WAV的主机测试另外留存，不代表实时板端识别或识别准确率验收。当前实际验证范围及硬件限制见 [本轮报告](/home/ghmd/aura-asr-integration-20261016/REPORT.md)。
