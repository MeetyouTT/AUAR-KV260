# YuNet输入编码候选与音频有限复核（子任务）

用户要求两个终端，主端独占板卡操作。本子任务仅读取本机源码/运行host合成输入与Fake native scheduler；未接UART、板端HTTP、MMIO、服务或模型，不改冻结v15。

依据主端同fid profile已测得layout/normalize与encode成本占比（此处不代验板端），完成独立yunet_input_fast_20261026候选。仅native_critical且fix7/NHWC[1,320,320,3]更换实例net；原YuNetCompat resize/blob/decode/NMS、guard、_native_scheduled、owner/预算均保留。严格验证float32 NCHW[1,3,320,320]、有限、0..255且为整数，再uint16提升后原位加一/右移/clip127，形成连续NHWC int8；失败清缓存。

6项host回归通过，覆盖全256灰阶、随机BGR/resize/非连续/饱和输入逐byte等价、原guard对象及期限不变、None/原异常/错误输出名/无guard、native/legacy准入与CPU fallback对象不变。独立20帧无DPU微基准含完整resize/blob/setInput/forward以及Fast验证，real reference YuNetNetwork/encode；两边native fake及output transform identity。微基准内部12秒预算（最大14），host通过不代表KV260性能。生产优化未在子任务启用，主端将决定板端测量与接入。

fast_yunet_input.py SHA4cadbd723c74041405fa97e34f917656200302bf330d24528b92a570ea3aa7d0，board_benchmark.py SHA62867afe9c8c32f2a1930898ede33774bb752afa73a6c6ecefd9d23e249cbff7。v16 profiler派生decode统计需加入fast_input_encode/fast_network_forward两个非重叠子阶段，不改冻结v15。

音频有限审查按主端确认的worker5f7f5684/enginef257cf2d现役版本，对比r4旧版区别。原7项+3项Fake-clock有界检查通过；持续空闲保活/20ms时基/最多8块补推/有界Python队列未见直接导致HC_DATA_BUFFER_ERROR的证明。IDLE_READY不是实际USB健康证据，普通persistent stop不释放PCM而close才release；不以正常GUI一次重连恢复宣称底层根治，不实现自动恢复/不建议取消语音或默认关设备。

本地源码及报告：/home/ghmd/aura-pan-follow-shadow-20261024/yunet_input_fast_20261026/、v15_local_review_20261026/AUDIO_REVIEW.md；共享小型副本在协作任务/2026-10-26_转轴交接复核与闭环修复/YuNet输入编码候选/及v15本地独立审查/。未修改Windows原回执或共享主入口，无权重、图像、个人身份或venv复制。模型性能、真实音频/长稳/实体跟随均未由本子任务验证。
