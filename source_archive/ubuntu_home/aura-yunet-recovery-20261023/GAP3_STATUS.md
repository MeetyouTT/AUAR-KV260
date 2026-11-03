# light3 间隙取证候选

复用原业务时间戳，每次发布保存前一份计数的6个数字；只有观察到跨TTL间隙才追加详细记录，最多32条，超过容量显式累计dropped。记录包括前后source stamp、前一发布观察时刻、间隔、TTL缺口上下界，以及这段时间内新帧供给/尝试/时隙拒绝/busy/deadline/expired取消的差值。既有混合事件环保持。原light2父目录未改。

完整85项软件测试通过，覆盖15项light、20项service、39项retry、11项combined；评估器19项通过。KV260无设备合成检查35项通过：正常路径新增CPU平均0.285647ms/墙钟0.298359ms；拒绝路径新增CPU0.151022ms；满16混合事件及32条gap记录的health在外层共享RLock下新增CPU0.287403ms/墙钟0.317456ms，均低于原0.5ms门槛。满容量观察器JSON约15,649字节。测试未创建额外DPU任务，原相机112143及GUI/Xserver未被修改或重启。

此为合成开销证据。当前120秒实时诊断使用helper `54bbfd6469d02252…`，原30ms/5ms、1ms GIL、同版有界重试与回退finalizer保持。结果记录在主任务目录`/home/ghmd/aura-post-power-20261022`；未在本文预报实时通过、根因已解决或生产启用。schema故障占位也已同步light3。
