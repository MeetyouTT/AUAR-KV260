# 当前操作边界与继续入口

当前生产相机588727、GUI588755；unit/release/GUI运行目录见 `final-audit.json`。YOLO仍DPU，YuNet因event521的guard越界在CPU保护，SFace因event610的39.891329ms硬超限停用、ready=false。现有0新USB、gap0只代表对应快照。

GUI-only回退仍是 `/home/root/aura-video-cpu-20261023/66cde810eb059dce/restore_previous.py`；本轮仅执行了 `--check`，按相同源码/argv/owner验证后把会话camera_pid从499773衔接至588727。**本目录内的旧恢复脚本和固定PID预检是历史执行记录，不能直接当下次恢复命令。** 不应运行旧整包回退来测试GUI。若以后boot/PID/source/偏好变化，先重新只读核对，不篡改保护PIN让检查通过。

`trace_isolated.py` 是无DPU的隔离成本检查，已完成；三轮各自SHA、真实失败和清理结果保留。最新9c8f8702…使用无seek单次append写，保留原fixture/BTI偏移。先前 `Path.open('a')` 的隐式SEEK_END不适合该tracefs节点；不是VART或模型故障。

`trace_vart.py` 是一次60秒、固定实际ELF/boot/相机PID/TID生存代次的阶段采样控制器；没有新建runner或调用推理，既有业务自己产生样本。只保留SFace TID记录；同一库其他调用线程仍可能承受断点开销。四个非分支位点：native前0x10a04、后0x10a10，RestoreThread前0x10a1c、后0x10a24。前点分别含三条/一条参数准备指令，时间也含断点与off-CPU；不叫DPU硬件耗时。文本实际精度以报告fraction_digits为准。

每个控制器用私有tracefs instance、唯一group及已保存path/offset所有权清理，不截断全局uprobe_events，不修改全局tracing配置。清理要关闭自身event并移除自身instance/定义；只关tracing_on仍不能消除断点成本。75秒独立cleanup timer与90秒worker上限兜底。报告必须同时检查controller退出、cleanup passed、group/instance不存在、timer inactive、global_state_unchanged、缺失/丢事件情况以及业务fault/gap/主周期增量；measurement passed不能代替业务稳定通过。

本次业务控制器实际在line72的SFace ready门槛被拒绝，早于guard/probe创建，没有60秒观测结果。`cleanup-audit.json` 确认probe/instance0、worker failed且已退出、定时清理inactive。下一轮先补SFace受限恢复的真实probe入口与ready隔离，再做单变量native/GIL归因；不要求用户长时间守镜头、不以反复重启追求零计数。准入余量候选、独立陌生人/多人精度与冷启动/长稳仍单独待办。

共享包不包含精确ELF和全量反汇编；Ubuntu私有本地路径 `exact-runtime/vart.so` 仅作匹配分析。`verify_exact_elf.py` 需要该原件，其他机器只能复算数字证据，不能伪称已重验二进制。Windows仅更新自己的回执，Ubuntu不代填同步接收/本机服务或实板业务验收。
