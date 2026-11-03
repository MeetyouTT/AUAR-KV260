# 当前分工：SFace状态与界面CPU / YuNet另行审查

用户已明确把YuNet偶发超限交给另一个AI审查。本Ubuntu任务继续SFace可用性状态、相关身份操作与界面CPU定位，不开展YuNet长尾根因实验，不改YuNet、共享DPU调度器、30ms/5ms保护、位流或运动。没有启动新的agent。

本地独立工作目录 `/home/ghmd/aura-sface-availability-20261023`。已改相机`board/vision/dpu_sface.py`、`board/identity/camera_faces.py`、`board/identity/live.py`，另修实际GUI消费侧`board/identity/spoken_query.py`的ERROR误判。4源候选92软件/16板隔离通过，尚未替换生产程序，见[修复交付](../../语音共享文件/deliverables/2026-10-23_sface_availability_candidate/README.md)。没有覆盖双方活动源码或旧封存交付。

为了保留YuNet的现有故障现场，本轮不重启相机或修改正式unit；SFace先做同源软件反例与板端隔离验证，不打开第二个DPU owner、不发新的真实DPU任务、不读取身份原库/照片。正式部署与当前候选完成分开记录。

YuNet审查优先读[第三次故障补充](YuNet审查交接_第三次超限与保护锁定_20261023.md)和 `evidence/ubuntu/yunet_review_latest_20261023.json`：同camera333557、unit a29082ba，第三次82.927ms/guard越界已LATCHED退CPU；包含前两次完整数值环。较早project_remaining_20261023.json的恢复2/2仍保留，但不能当目前仍DPU。第一例主要停顿在API外围，第二例主要在execute墙钟；不能直接归因纯硬件或仅调整cap。共享JSON无真实图像/录音/身份向量或库。

后续回传至少列出审查源hash、改动文件、是否需要切换相机/共享调度器及证据时点；其他AI需要共享调度改动时，应基于当前正式源合并，不覆盖已完成的SFace身份域或较新UI/语音成果。此约定不代表Windows已确认接收。
