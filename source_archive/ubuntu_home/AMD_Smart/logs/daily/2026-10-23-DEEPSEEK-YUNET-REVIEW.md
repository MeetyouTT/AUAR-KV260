# YuNet偶发超限：DeepSeek独立审查提示词与资料

用户要求解释YuNet偶发超限，并准备提示词交DeepSeek做全面审查。先重读ZIP README、项目/共享规则、最新入口和日志，发现最新状态已变为a29082ba…三模型正式DPU，不能沿用旧SFace Windows/2478次零故障结论。

按已有UTC08:12～08:19只读证据：YuNet10678次native完成、2次hardcap、native失败0，分别scheduler30.692017/31.162401ms，均status0/completed1、guard0/waiting_primary0，恢复2次后RUNNING。第一条execute前22.709727ms、execute4.099281ms；第二条execute30.220712ms/调用线程CPU1.122652ms，必须分别解释。当前gap0/主周期超限累计仍1，SFace1528次/超限0。最新两条故障未采集对应USB内核窗口；仅历史独立故障有USB0证据，不能混用。

已在共享语音deliverables/2026-10-23_deepseek_yunet_review创建完整中文提示词、来源分级、过滤故障和发布证据、带行号合并TXT和ZIP。提示词要求独立审查计时边界、测量开销、锁序与并发、YOLO期限、时隙饥饿、VART绑定/GIL证据、保护恢复、SFace disabled健康可见性、CPU剖析和单变量最小实验。明确不预设GIL/硬件/USB为根因，不以阈值放宽或计时边界迁移伪造修复。

实际验证：16份现役导出源与ACTIVE_RELEASE逐字节SHA匹配；7份额外发布PIN源匹配；6份参考源明确没有本轮实板PIN；7份既有测试仅供审查。36份Python AST解析通过，两条故障分段求和吻合原trace，所有证据JSON可解析，ZIP CRC/包内SHA通过。未运行附件中的业务测试，未连接板卡、部署、提交推理或向DeepSeek/其他外部服务上传。资料不含现场图像/声音/特征/身份库、模型权重、密钥或原始UART；入口和Ubuntu回执只记录本次资料准备，Windows回执未改。

交付：[完整提示词](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_deepseek_yunet_review/给DeepSeek的完整提示词.md)、[合并TXT](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_deepseek_yunet_review/DeepSeek_YuNet审查资料.txt)、[ZIP](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_deepseek_yunet_review/DeepSeek_YuNet审查包.zip)。实际因果定位仍待独立代码审查及必要实测。
