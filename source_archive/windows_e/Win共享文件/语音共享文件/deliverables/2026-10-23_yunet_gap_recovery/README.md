# YuNet更新间隙取证与失败轮次恢复候选

本轮已确认一段更新间隙中的实际活动：13次新帧供给、7次尝试，其中5次DPU时隙拒绝、1次共享锁busy取消，随后成功。发布观察间隔1038ms，前一次源帧TTL之后缺口下/上界175/175ms。该段不是输入停止，固定200ms失败轮次等待可能放大连续拒绝。不能据这一段证明所有历史YuNet长尾的唯一原因。

light3将gap单独保留最多32条数字记录，复用已有时间戳，附间隙内offers/attempts/denials/取消计数差。满容量health JSON约15649字节，KV260观察器新增平均CPU正常路径0.286ms、满记录health0.287ms，均低于原0.5ms门槛。原16事件环保留。

独立恢复候选`retry_recovery_ms=None`默认关闭。仅显式设置50ms时，未发布轮次后的等待由200ms缩短到50ms；成功发布（包括真实无脸）仍200ms，等待释放锁且需要新帧。重试次数、25ms退让、200ms提交截止、1000ms TTL、30ms硬上限、5ms guard和YOLO优先保持。源见[face_targets.py](source/candidate/aura/board/identity/face_targets.py)、[间隙观察器](source/candidate/aura/board/identity/face_freshness_metrics.py)、[新增恢复测试](source/tests/test_recovery.py)。

|验证|结果及范围|
|---|---|
|完整软件测试|89项通过，含原85项与4项恢复节拍测试；fake native/虚拟时钟|
|评估器|light3 19项通过，拒绝不完整或成本超限结果|
|KV260无设备合成|同源35项通过，无额外DPU任务；恢复版观察器正常新增CPU0.2805ms，满history health0.2876ms|
|light3实时120秒诊断|有效120.932秒，YOLO9.890Hz/YuNet3.109Hz、CPU56.99%、USB0/硬超限0；捕获1段gap，严格时效未通过，回退verified|
|50ms恢复策略两次实测尝试|都在观测开头因USB告警中止，recovery_waits均0；回退verified，不能报告策略收益|
|最终原服务恢复|原音频与原相机已恢复，8秒完整窗USB0/CPU52.18%，主服务active，guard timer inactive；仍是短窗证据|

USB异常期间约5秒after-cursor查询达到5000条上限（计数仅下界），CPU90.29%。原服务曾26.91ms越过调度guard后回CPU，未达到30ms硬cap；加大30ms不会解决这种guard超限。空闲恢复后短窗告警消退，但再次切换候选仍复发，具体驱动/硬件根因未确定。

当前生产未启用50ms、light3、1ms或新重试参数；YOLO＋YuNet DPU及Windows SFace/旧库按原配置恢复。下一步见[相机与音频切换顺序](NEXT_STEPS.md)。代码与过滤证据在本目录，原始UART、真实图像/音频/特征/身份库与模型权重未共享。Windows接收和实板业务验收仍需分别记录。
