# 当前运行与回退

当前boot `7924ac9f-311d-4fcd-98be-57bf023cf1aa`，camera unit SHA `29786434df9bb9b94a8e640a7a48db47019c224d3876037ce27d3467bb2f5512`。

实际camera release：

`/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136`

GUI runtime为该目录下`gui-runtime`；新增自有12z开头的reliability systemd override。相机450495、GUI监督450525、Xserver1077仅为本次核验时点，后续从服务/health读取实际PID。

身份仍使用父版本`release-sface-int8-9025bd49fe52-333217/board_identity.sface_int8.json`及同一私有INT8库；配置SHA398ece6a…、原INT8库SHAee22b97d…、原Windows库SHAe0d2113e…在本次首尾不变。没有新登记/迁移，不能把此版本的模型ID、向量域或阈值改成旧Windows值。0.50/0.10仍实验固定值，现场异人/多人未验收。

板端默认只读核对：

```bash
/usr/bin/python3 -B /home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136/restore_previous.py --check
```

明确回退：

```bash
/usr/bin/python3 -B /home/root/aura-dpu-vision-20261021/postpower-retry-live/release-reliability-f7624754038f-450136/restore_previous.py --restore
```

回退目标为原unit a29082ba…和原GUI de989bf0…，保留当前INT8库/配置；不退回Windows特征域、不删除身份或记录。入口绑定boot/source/config/原dropin集合和偏好，须自然空闲并无开麦/录放音/运动。手动回退先ARM独立恢复timer，再关GUI/确认PCMclosed、移除自己override、恢复camera与原GUI；全部核验后停止timer。不得删除其他dropin或绕过SHA/boot检查。

该--check已两次实板通过；成功保留的最终版本没有为测试手动命令而撤销。前两轮失败已实际完整恢复两组件，自有override和timer清理通过。新boot、外部GUI/source/偏好改变后可能拒绝，要重新核对后生成匹配流程，不直接复用旧固定PID/boot helper。

检查新健康字段时，scheduler和optional_diagnostics两个子快照明确非原子，不能无条件强求其调用计数同一时点相等。worker_alive由真实线程is_alive表达，故障后fault_latched/ready=false；SFace feature_status.ready=false时不消费缓存身份。owner_fenced=true表示完成未确认、所有新DPU准入被阻止；它不代表在途硬件已经被取消或可安全另开owner。

本版本没有改变30ms/5ms或引入自动放宽。SFace停用可见性已修，SFace有界自动恢复尚未实现；遇真实故障先保存boot/PID/源SHA和完整数值，再协调恢复，不能清计数后宣称根因已消除。
