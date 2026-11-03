# 语音助手启动摄像头身份登记

**最新现场（UTC2026-10-19 03:03后）：** 用户当前在玩偶交流页，实板UI空闲/相机正常，身份仍未启用；电脑8792健康请求本次超时，保留TRANSCRIBING。先按[当前页面下一步](现在在玩偶交流页_下一步.md)恢复语音连接。只读检查未启动录音、播放、登记或重启。

2026-10-18 Ubuntu软件候选；UTC核验在2026-10-19。用户要求“说记住我是谁，然后助手操作启动”。

已在语音共享根实现：语音登记入口→询问称呼→明确确认→同一摄像头五帧采样→事务写库→按真实结果播报；普通对话继续使用原27B和OmniVoice16。**本轮未部署到活动板端，功能开关默认关闭，未采集或登记真人。当前相机身份候选为CPU参考；DPU SFace正式相机后端和真人验收仍待完成。**

## 已实现

- “记住我是谁”或“记住我，我叫小明”进入登记；确认前可修正称呼/取消。只说“我叫小明”不会自动登记。
- 整段登记绑定同一相机/轨迹代次，要求画面内只有一人；确认后可自动选择唯一目标。多人、换人、失联或超时会中止。
- 原相机进程筛选新鲜、清晰、不同且相互一致的五帧特征，归一化聚合后一次提交；不新增摄像头，不在共享目录存人脸图或身份库。
- 接受采样请求不等于登记成功。只有匹配请求的 `COMMITTED` 及库版本才生成“记住了”的播报文本；写库失败、取消和超时返回失败文本。
- ASR后先执行板端控制逻辑，再通过新增文本流接口调用原LLM或固定反馈TTS。每轮一次ASR，保留流式音频、代次校验和播放完成后提交对话记忆。
- 旧电脑服务不支持新接口时会显示需要升级，不静默执行登记。当前仍使用按键录音，不增加常听麦克风。

## 验证

- [框架回归](framework-unittest.log)：271项unittest通过，其中新增27项语音登记测试。
- [补充函数回归](voice-functions.log)：7项已有流式任务/延迟函数测试直接调用通过；未安装pytest，未将其称为pytest全量执行。
- 新增测试包含真实回环HTTP与SQLite、合成ASR/人脸/TTS。四轮测试验证登记三轮后普通问题仍进入LLM，ASR恰好四次；不代表真实模型听音、真人身份准确率或DPU相机混跑通过。
- [最终工件核验](verification.json) 与 [源文件清单](source_manifest.json) 记录长度、SHA256和默认开关；归档仅是源码补丁，不是可直接覆盖活动版本的完整运行包。

## 文件与接手

- [操作与接口说明](../../aura/docs/VOICE_IDENTITY_ENROLLMENT.md)
- 板端：[语音控制器](../../aura/board/identity/voice_enrollment.py)、[多帧事务](../../aura/board/identity/live.py)、[ASR分流任务](../../aura/board/runtime/audio/channel_jobs.py)、[GTK接线](../../aura/tools/board_avatar_gtk.py)。
- Windows：[新增文本流接口](../../aura/tools/board_model_host.py)、[原TTS路径与固定反馈](../../aura/tools/voice_channel_source.py)、[请求校验](../../aura/common/voice_text.py)。
- [测试源码](../../aura/tests/framework/test_voice_identity.py)，[修改前11份源码快照](before/manifest.json)。`source/`为本轮16份源码/配置/文档的冻结副本，归档与哈希以verification.json为准。

Windows先更新相关服务并重启，确认 `/health` 的 `voice_text_channel=true`；板端基于当前流式版本合入源码，在同进程DPU SFace及对应模型模板/阈值就绪后启用 `voice_identity_enrollment=true`。不要直接覆盖新版语音运行目录，也不要用CPU模板冒充DPU模板。实际相机、MCP01出声、登记后重返、UNKNOWN、取消、删除/重启须分项验收。原按钮单帧接口保留，语音入口使用新多帧接口，后续再统一按钮流程。

Ubuntu本地文件/测试通过、微力同步接收、Windows服务重启、板端部署和真人业务验收是不同状态。Windows回执由Windows端填写，本轮未代填。
