# 当前运行与回退

当前同boot `7924ac9f-311d-4fcd-98be-57bf023cf1aa`：camera unit SHA `e893930d9f51540223e849c36409fdc225fe7cbb347cdc1cb75166d8271e83f7`，相机252665、GUI监督252691/Xserver1077。代码与新配置在：

`/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-bounded-61abe4391d3a-251478`

活动entry为runtime_entry.py，延迟注入入口不在正式unit中。配置`yunet_dpu_recovery=true`，源包880文件；原30ms/5ms、1ms GIL、50ms失败轮次、1000ms TTL保留。SFace正式仍Windows/原库配置；本轮没有切换语音模型或位流。

在板卡串口/受控终端进行只读核验：

```bash
/usr/bin/python3 -B /home/root/aura-dpu-vision-20261021/postpower-retry-live/release-bounded-61abe4391d3a-251478/restore_previous.py --check
```

明确执行回退时：

```bash
/usr/bin/python3 -B /home/root/aura-dpu-vision-20261021/postpower-retry-live/release-bounded-61abe4391d3a-251478/restore_previous.py --restore
```

该入口先校验boot/代码/config/偏好与空闲条件，再arm独立恢复timer；正常关闭原音频、确认PCM关闭后恢复旧camera unit，重建原音频并复核就绪。本次回退目标为前一版af337bce…与release-recovery50-946d1a0d500f-197870，含原50ms策略，但没有本轮自动恢复；不是最早84116d8f…版本。--check已实板通过，--restore的部署事务回退路径通过软件故障注入，本次正式成功后未为测试而再次撤销正常版本。

同boot前置与文件校验均不可随意绕过；新boot、用户修改config/偏好或录音/运动活动须重新采集当前状态。旧写死af337bce…或84116d8f…的helper不能直接在当前unit上重跑。Windows后续发布GUI/语音时保留当前camera unit/runtime/config，不使用历史整机包覆盖。

受控注入的35.509ms事件属于前一个相机进程的实际测试记录；正式进程为重新启动的普通入口，注入代码未被其导入。正常进程的新超限即使恢复成功也应报告真实次数；冷却/探测期间的CPU fallback与最终恢复分别记录。30ms是完成后的占用检查，不是强制中止VART的保证，禁止任务未完成时释放owner或复用缓冲。
