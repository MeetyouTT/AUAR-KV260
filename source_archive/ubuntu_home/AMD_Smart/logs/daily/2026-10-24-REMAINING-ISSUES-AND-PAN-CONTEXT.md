# 当前剩余问题与转轴上下文核对

**后续验收标准更新：** 用户提出YuNet能自动恢复即可，当前阶段据此将有界自动恢复后持续输出、主任务时效保持、故障及恢复可观测作为验收标准。旧4fault/4recovery保留，不声称根因消除；恢复失败/锁定或影响业务仍是需修问题。长尾唯一根因不再作为当前交付阻塞，不单独延长等待故障的观察；优先转轴和严格CPU/DPU收益，恢复可用性并入整机运行检查。

用户要求暂缓HDMI问题（物理拔插可临时恢复），继续其他问题。root保持单终端，无新代理。只读访问既有健康接口和文件，不打开运动传输/MMIO、不发运动、不更换PL或重启模型。

实板新快照：boot `c5f247b9-76b9-40a3-85ca-96578055eb5c`，相机1309/GUI1310均active、NRestarts0，YOLO约9.92Hz，原生路径启用、owner未fence、worker存活，YuNet/SFace本boot超限0。旧4次YuNet故障/4次恢复已另档，不用新零值宣称根治。

转轴API明确为 `FAULT`，`error="Boot mismatch"`，脉宽和目标为null、动作history空、automatic_following=false、机械参考未标定。实际活动manual_vsrv.py SHA `cea8413e2076045376f3cd402f877cb97cffae84cb5df6f2e4d1e4fd857257b2`，其平台验证先核对boot，再进入传输和寄存器接口。故当前是旧启动绑定被保护拒绝，不能据此认定电机损坏，也不应仅改boot_id绕过上下文核验。

联合VSRV/2候选仍在本机离线构建：`aura-pan-offline-resume-20261024.service` active/running，单线程/Nice15；route_design已完成并打印Router Completed Successfully，正在后路由phys_opt_design。路由阶段估计WNS/WHS各0.001ns是中间值，完整report_timing_summary/DRC、位流/XSA、独立审计及封包尚未全部完成；当前joint_implementation_passed=false/deployable=false保持，不修改构建任务自己的STATUS或PROGRESS。候选模板disabled，正式放行和有限台架观察要分别记录，缺外部测量不伪造QUALIFIED。

后续顺序：

1. 收尾联合固件最终时序/DRC/配套驱动检查；用当次实际boot、FDT、固件和业务源重建交接上下文。条件满足后，先ID/STOP及有限台架，再机械标定/随动；当前未上板候选。
2. YuNet按上述自动恢复标准随整机验收，唯一根因研究留作后续优化；两小时未新增不等于根因消除，30ms/5ms保护不放宽。
3. 完成相同输入/负载的新旧路径性能对照：延迟、有效帧率、CPU核秒/帧与DPU任务忙时。既有15秒busy5%点测、页面A-B-A负载差异不可作为优化倍数。
4. 补三模型有人持续负载、身份转头/多人场景及实际旧码回退。前次7200秒窗口SFace新完成0，不属于三模型满负载验收；已有正脸和陌生人样本保持原范围。

证据为 `aura-model-inventory-20261021/pan_current_readonly_20261024.response.json` 与对应exit_code=0/输出SHA串口回执；原始UART不共享。Windows回执未修改。
