# 可复用运行时审阅技能

技能入口：[kv260-runtime-review/SKILL.md](kv260-runtime-review/SKILL.md)。
本目录是比赛要求的 skill/ 材料，尚未安装到全局 Codex 技能目录。可在新对话明确提供此路径并请求使用技能；也可直接阅读入口与引用资料。

## 范围、方法与效果

适用于 Kria Linux 的 DFX manager / ZOCL 运行时诊断、重复 watch 登记排查、Unix socket 就绪检查与受控复验。方法由真实失败→诊断→最小修复→有限板测→恢复案例提炼，来源在 evidence/ 中；不是完整 AURA 应用，也不是 PYNQ Skill。

工具可复用参数，不硬编码单一卡号、PID 或 boot ID：

```bash
python3 -B skill/kv260-runtime-review/scripts/socket_probe.py --path /tmp/dfx-mgrd.socket
python3 -B skill/kv260-runtime-review/scripts/watch_snapshot.py --pid 1234
```

PID 1234 是示例，必须替换为本次实际 daemon PID。脚本不执行应用重载、服务启停或模块装卸；socket 默认 SOCK_SEQPACKET，应先确认目标源码。两类工具输出 JSON；没有连接或无法读 PID 时返回失败，不能作为零 watch 或功能通过。

历史修复的效果：原版 130 次扫描登记表满500/内核5；修复版 10,000 次保持5/5；板上 1,000 次 list、50 轮目录增删、3 轮重载和同图推理有限通过。新技能工具在本机完成 9 项隔离验证，包括正确/错误 socket 类型、缺失 socket、重复 wd 分属两个 FD、缺失 PID、归档路径和相对链接处理。技能结构检查通过。这些不是本技能新的板测或通用效果证明。

## 失效条件和限制

镜像/内核/daemon 协议/应用/权限变化时重新获取证据。proc/sys 无法读取、PID 更替、环形日志不完整或采样不足时报告无法确认；单个 RSS/Slab 样本不能断言泄漏。修复登记互斥不证明全部 daemon 状态线程安全，引用平衡也不证明并发热卸载安全。

导出全部真实可见大模型记录仍待完成；本附件的 collaboration_log.md 是注明范围的摘录。尚未在其它工程独立泛化验证，不能宣称额外比赛分数。
