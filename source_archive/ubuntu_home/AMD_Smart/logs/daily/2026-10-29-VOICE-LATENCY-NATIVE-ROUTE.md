# 语音延迟：运行加载已生效，同输入对照待补

## 用户要求进一步提速：Windows第二轮执行单已准备

基于现有两轮，首句累计约1.89/2.02秒，TTS请求1.58/1.22秒，板端总差0.397/0.354秒。两轮模型加载仅毫秒，不把再加预热列为解决暖态秒级等待的已证实措施。复核既有FirstSentenceBuffer12字符完整句、已上线首句合成、持久音频80ms缓冲/10ms周期与历史早分段导致停顿的失败；不直接缩句或缓冲，也不切到历史流式TTS替代候选。

已写共享进一步降延迟_Windows执行.md：实际r9源码保护及回收→同输入基线→提示预处理/缓存→现有紧凑通道兼容验证（不绕过身份校验）→原OmniVoice16的重复工作/同GPU竞争→板端逐事件准备。参考官方Ollama API/FAQ，区分实装版本支持和文档新字段。约3秒作为评估目标而非承诺；未部署第二轮候选，未测得额外收益，未改生产代码/模型/音色/业务。Ubuntu无Windows远程命令通道，实际模型A/B与最小部署由Windows侧接续并填写本人回执。

## UTC12:47：运行false已验证，最近两轮暖态起答约3.59–3.87秒

用户询问当前延迟。共享目录仍无Windows本人回执，但新的两次独占UART实读显示Windows已更新为voice-chat-memory-20261029-r9/source5a4fa28e8679ffd24b61e940455e7dd2341c02c8ae70e8997aa5682c157471f3，ready且非busy，compact_grammar=false，其余开关/27B/Paraformer/OmniVoice16保持。boot55152f95、GUI114923、camera21824保持，监听/跟随关闭。原始输出exit0/SHA/回显恢复通过，未执行本次重载或模型请求。

读取板端已有最近完整turn generation20/38：提交到软件起答3.865955/3.588321秒，服务端首PCM3469/3234ms、准备0.00/0.00ms、ASR各78ms，首句累计1891/2016ms、首次TTS生成1559.89/1185.38ms，模型加载2.21/1.55ms，均非TTS缓存、无质量重试且音频完成。上下文0/2条，不能形成严格同输入前后对照；它不包含句尾端点全部等待，也不是声学计时。服务当前版本较新，不能直接归因全部变化到单一开关。

当前可确认运行开关已生效、两轮已无旧准备开销，仍需Windows回执、同输入A/B和持续体验。最新过滤JSON与任务状态已更新，旧true的health原件保留。不共享对话正文、原始媒体或数据库，不代填Windows回执。下方07:52–07:56“待加载”为早前记录。

用户在明确保持现有整机功能范围后，授权执行关闭失败原生通道、检查预热/保活和同输入延迟对照。已查ZIP项目README、项目及共享规则、最新双机入口、先前脚本与实测依据。

实际新证据：UTC2026-10-29 07:52:10与07:56:05经独占UART读板端及Windows健康。boot55152f95、GUI114923、camera21824/epoch55319b91…保持；UI IDLE/IDLE_READY、无录音或待转写、监听/跟随关闭。Windows8792是较新的voice-timeline-20261028-r2，source_fingerprint=bc9b8aaddea9b9d3e4a588d57c4b52b49bd8a61f59fac06c6f856477baf0baae，ready=true、busy=false，27B/Paraformer/OmniVoice16保持，含timeline_memory等新能力。该源码尚未同步到Ubuntu，不用旧共享源覆盖或历史重启脚本回退。

完成：UTC07:53:40运行已有disable_failed_native_route.py --apply，只将共享语音根aura/config/voice_latency.json中compact_grammar改为false。前SHA bc1202bf9f5c15c2416d94f8948225f08eb129699a31e9aaad8276f9f8c4085b，后SHA 72f3cf4344abdab9b100b94679624c980ce1240e641bf36b6b47468cf6c94111；原字节备份保留。独立比较确认唯一变更键和其他五项保持，再次只读预览不写入。

验证限制：系统Python3.8且无pytest；标准库运行既有13项不同回归，9通过、4因ThreadPoolExecutor.shutdown(cancel_futures=...)需要较新Python而报错。未修改生产语音源码来掩盖环境限制。原错误和通过日志保留，未称全部回归通过。

连接情况：沙箱ip netlink受限，按流程提升权限读接口，仅172.23无线；提升权限直连192.168.50.1:8792仍3秒连接超时。串口外部可见，已有独占transport两次探测exit0/SHA/echo恢复通过。可从板端读Windows健康，但无Windows PowerShell、SSH配置/密钥或远程命令入口；没有擅建远程执行服务。

最后运行health仍compact_grammar=true，所以本次是共享配置已修，Windows同步收件/加载/收益未验证。Windows启动warmup代码本已存在，不能重复宣称新增；30m保活不等于当前真实驻留。新版本是否仍复现旧18轮失败、具体减少多少开销需新鲜同输入对照，不能把旧服务历史数字当本次结果。

共享[任务与回执](/home/ghmd/Win共享文件/协作任务/2026-10-29_语音延迟修复/README.md)已备齐：保护当前新版、指定配置核对、仅8792及其所有工作进程的空闲归属重载、模型/音色/记忆不变、公开样本/合成会话、本机与网线对照及回退。Windows本人填写执行结果；已询问用户Windows接续方式。没有新增推理、开麦、播放、运动、服务切换或数据库操作。

私有探测原始证据保留/home/ghmd/aura-voice-latency-20261029/；共享仅过滤元数据、配置指纹、测试日志和任务，原始UART与用户数据未共享。
