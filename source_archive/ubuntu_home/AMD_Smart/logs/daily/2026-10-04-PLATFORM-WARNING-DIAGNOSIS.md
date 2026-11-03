# 2026-10-04：KV260 遗留告警诊断与修复方案

用户询问 NFS、TPM、overlay 等剩余问题如何解决。本轮读取项目书入口、平台重建方案和最新板测/冷启动记录，再通过同一 UART 只读查看实际内核配置、NFS 服务和开机入口、TPM 状态与能力、显示时钟和 DisplayPort 连接。

## 实测结论

- NFS 根因确认：CONFIG_NFSD 未启用、nfsd 模块不存在，但 server/mountd 和 sysinit 中的 nfsd 挂载被启用。当前导出和 NFS 挂载均为 0。建议停用无用途的服务端启动并取消 nfsd 挂载启动，保留客户端；配置尚未更改。
- TPM 启动 256 = 0x100，对应 TPM2_RC_INITIALIZE。日志随后由内核执行初始化，本轮 `tpm2_getcap -T device:/dev/tpmrm0 properties-fixed` 返回 0。补充纠正先前报告的笼统“TPM 旧问题”：已证实当前能力查询正常，这条日志不是持续自检失败的证据。
- overlay 告警来自内核对存量 DT 节点属性的动态更新/释放边界。前轮用户态 manager 的 fd/watch 验收不覆盖内核属性；实际内核泄漏量未测量，修复需在最终配套 DT/内核中实施与回归。
- 显示时钟 -13 对应固件访问拒绝；当前 DP-1 为 connected，不能按无显示用途裁掉链路。需继续核对固件资源许可和设备树时钟请求，唯一根因仍待证。
- IRQ 8 枚举边界与 xclbin 可选 section 提示已定位到对应源码，需按具体设计处理，不能将所有日志文本一概视为 DPU 失败。

新 manager 仍为 PID 999、active/running，boot ID 保持 `01ca88c1-93b6-414f-9646-774482d4b2f0`。本轮只读查询，没有改变板卡配置、清空 TPM、更新 QSPI、加载新 bit 或重复推理/压力测试；没有新增物理断电验收。

完整 [诊断与修复方案](/home/ghmd/kv260-platform-warnings-20261004/WARNING_REPAIR_PLAN.md) 及 [结构化状态](/home/ghmd/kv260-platform-warnings-20261004/DIAGNOSIS_STATUS.json) 包含证据链接、源码与官方资料依据、逐项验收要求。UART 超长命令的首次未执行记录保留，拆分后采集通过，echo 已恢复。
