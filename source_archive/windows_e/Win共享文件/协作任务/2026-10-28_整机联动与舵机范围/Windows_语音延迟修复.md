# Windows语音延迟：已定位无效原生通道重试

Ubuntu本轮仅读取正在运行的状态与数值耗时，没有读取或共享对话文本/录音，没有修改Windows服务，也没有代填Windows执行回执。

## 已验证现象

- 当前8792为voice-animation-dialogue-20261026-r3，source_fingerprint=5271c3d559b99126d075c927c347f8c3cfef6d112b9bfd1b7baade46e551c88c。
- 本轮18条已有回答全部实际走backend=ollama，而health仍显示compact_grammar=true。
- 首轮原生准备TimeoutError，后17轮均为ValueError: Native model/template/build/context not verified；暖机通道准备约0.80～1.19秒，每次都尝试失败再回退。
- 前13轮实际起答：首轮20.565秒，模型load_duration约8.887秒；后12轮4.172～6.285秒，中位4.810秒。暖机首句成形约2.78～4.27秒，首次TTS生成约0.96～2.57秒。这些不同台词不是严格优化A/B。
- 本机同步源码原本已经keep_alive=30m。不能把“再加30m保活”写成新修复；startup_warmup_complete=true也不代表模型当前仍驻留。

## 最小修复

优先在当前实际语音项目的aura/config/voice_latency.json中仅将compact_grammar改为false，其他五项、27B模型/人设/采样参数、ASR/TTS、记忆库和其他模型保持。因为实际早已回退普通Ollama，此项移除失败的前置探测；预期减少相应准备开销，尚未实测承诺具体端到端降幅。

本目录[disable_failed_native_route.py](disable_failed_native_route.py)默认只读预览；Windows在确认当前实际配置路径和空闲后可用--apply写入一项配置，自动备份且保留其他值。**脚本不会重启服务；需Windows端用现有进程归属校验流程，仅空闲重启8792。** 不向其他端口发停止，不清库，不关闭模型身份校验，不改变VERIFIED_BUILD来强行接受未验证runner。

重启后核对health.compact_grammar=false、ready及原模型/配置，使用实际新回答确认backend=ollama、无compact_grammar_fallback、request_preparation_ms降低，并分别记录首句、首PCM和板端起答。冷态/暖态分别保留，回答内容不同不得直接报严格提速率。

后续再核对实际runner build/template/context与已验证版本的差异，做同输入输出/取消/上下文回归后决定是否重新启用原生通道。冷首句另考虑明确的人脸进入事件触发有界预热；保持其他模型运行，不无条件将大模型永久占满GPU。

执行结果由Windows端补充新回执。本轮没有运行--apply或重启Windows。
