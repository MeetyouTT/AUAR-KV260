# VART精确绑定、等待观测与新保护事件

用户授权两路继续；主任务独占UART，第二路仅本地精确ELF/控制器审查，当前均结束。证据/自有代码交付：[native_wait_diagnosis](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_native_wait_diagnosis/README.md)。本机原件目录 `/home/ghmd/aura-native-wait-20261023`。

## 实测结果

- 原生缓存FD schedstat：7项ARM语义通过，但完整适配器平均线程CPU183.193µs/P99墙钟6.856ms，未过100µs/1ms成本门槛，未生产接入。外部100Hz/60秒实际91.84Hz、4.9789%单核CPU，超过2%，已退出。
- 外部窗捕获camera499773的SFace event5788：execute标记30.167721ms/线程CPU0.580727ms，完整包围窗39.587666ms、runqueue两端均4060123226ns、差0；status0。削弱本事件的CPU排队解释，仍不能证明GIL或原生阻塞，更不把剩余墙钟称DPU硬件时间。外部采样有额外负载，不作无扰动故障率。
- 已从板端取回匹配vart.so，194720B、SHA dc6bff9be31b8dc349a72489e06237f8503175805d042025558694823f61de34、BuildID e359176b9761d3035b0301d4ec6c48de9a0af577。方法名→pybind callback→SaveThread→native虚调用→RestoreThread路径及24指令字匹配验证通过。可确认实际绑定释放GIL，重获GIL等待仍在Python execute墙钟内；源码提交仍未匹配。ELF/反汇编只留本机。
- 保存旧camera499773的YuNet2/SFace1/gap1后，只做一次相同unit/source的camera+GUI恢复，初期YuNet427/SFace13次0新故障。新camera588727/GUI588755/X1077，GUI回退session经argv/runtime/owner核对后仅衔接新相机PID，--check通过。恢复不等于根治。
- 后续同新进程YuNet event521：21.037480ms、hardcap0/guard1、native完成status0；准入到guard20.909669ms，20ms估计之外仅0.909669ms余量，锁定退CPU。又SFace event610：39.891329ms、hardcap1/guard0，execute39.040631ms/CPU0.558185ms、wait0.093581ms，status0；SFace停用、ready正确为false，没有此次runqueue数据。未再次纯重启绕过故障计数。
- 四点UProbe无DPU fixture隔离：前两次tracefs初始化EINVAL留证；Python FileIO append隐式SEEK_END机制经本机strace核实。改用os.open(O_APPEND)/单次os.write、不seek后，同fixture SHA/BTI偏移500轮/2000事件完整，无loss；额外平均CPU20.272040µs，P99完整CPU34.69µs/墙钟56.12µs，成本/清理通过，实际文本量化1µs。不是生产开销或根因修复。
- 真实VART60秒控制器9项本地检查通过，但实际因SFace ready=false在创建guard/probe前拒绝，**未执行60秒业务观测**。所有own probe/instance实板只读检查为0，三个隔离guard与业务guard inactive，预检worker failed/已退出。common_pid过滤记录仍不能免除其他VART线程trap成本。

## 当前实板与保留项

同boot7924ac9f…、camera588727/GUI588755/X1077、unit29786434…；YOLO约9.92Hz仍DPU，YuNet CPU保护，SFace102次完成后保护停用（83deferred）。新进程1YuNet/1SFace fault、gap0、worker/诊断错误0、主周期累计仍1；USB/音频告警新增0。GUI175份Python、身份配置与新旧库SHA保持，GUI-only回退--check通过，监听false/麦关闭保持。原恢复前2+1故障与更旧450495历史均未删除；各PID计数独立。

原生工具本机10项C/7适配器检查、8项tracefs fake、9项phase控制器检查及确定性ELF复算通过；只对变更相关范围验证。69工件SHA、70总文件、Python AST/JSON和无ELF/生物数据/UART校验见本机delivery-verification.json。Windows接收、同步及本机服务验收未代填。

## 待办（计划，未实施）

优先SFace独立受限恢复：业务ready与probe许可分离、slot内status0完成标记、hardcap-only冷却、3次合格/600秒最多2轮；guard或未知完成仍锁定，现有YuNet LATCHED/旧计数保持。然后再用已核定四位点短采样定位native与GIL重获；准入余量候选单独评估，30ms/5ms/TTL/YOLO优先不变。当前未部署恢复补丁或余量修改；长期/冷启、陌生人/多人和严格同输入整板收益未完成。
