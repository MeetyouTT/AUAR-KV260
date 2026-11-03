# 双模型CPU亲和性120秒helper独立审查

2026-10-22，本终端只读代码与已有冻结证据，没有访问UART、执行helper或修改主任务文件/生产/共享入口。

审查对象：`/home/ghmd/aura-affinity-board-20261022/build_trial.py`及生成的`/home/ghmd/aura-identity-dpu-check-20261018/board_cpu_affinity_live_20261022.py`。本次helper SHA为`bed25237601e36ea6afde2bdc854aae14756bebe89005efbb146a3cc061361ba`；后续修改需重新审查差异，本结论不能自动套用新SHA。

结论：未发现阻塞此次受控双模型短测的代码问题。原5ms GIL、30ms保护/5ms guard、独立回退与原服务恢复边界保持；本结论是本地审查，不是板测通过。

追加r2 helper复审：`board_cpu_affinity_live_r2_20261022.py`的SHA为`c98cdd3015a366369671b9cfa018d845dccf2a02de6bda794b7d3bb21500d009`。与上版完整diff仅为下述建议1/2/3：snapshot前保存候选PID、getmask后复查线程与进程启动计数、freshness补负值拒绝。AST通过，未执行helper，未发现新的阻塞项；上述结论扩展到这一准确SHA。主任务报告预检原425227在新候选未启时又31.97132ms回CPU，按原unit恢复后再试；这属于主任务外部证据，本终端没有接板核验，不能把预检故障归到CPU亲和性候选。

## 关键依据

- 四角色启动没有三模型依赖环。`FaceTargetService.start()`与`IdentityService.start()`持`state.lock`创建线程，但`Thread.start()`只等待bootstrap先置位的`_started`，不等待`Thread.run`目标或本候选屏障；主线程随后释锁、返回`create_service`，可继续创建HTTP/GStreamer并start detection和preview。原业务`factory`在四角色commit后才运行。本机CPython实现也核对了`_started.set()`先于`self.run()`；目标板使用Python3.9.9。需注意8秒启动期限仍可能因GStreamer初始化慢而明确拒启，不能称绝不会启动失败。
- helper先等实际candidate runtime和健康状态，再检查commit。没有用另一个外部条件阻止主线程创建余下角色。健康检查虽依赖face ready，但在独立helper中轮询，不占相机进程业务锁。
- copy生产后才应用固定14源，随后逐一核对全部6份角色源。AST抽取并解码了3份内嵌payload：均与r2冻结内容及自身SHA一致；全部角色SHA另对照此前独立板审计/14源manifest，face准确为`d03e2aee…`。仅双模型四角色策略`[2,3]`/`[0,1]`；没有设置GIL的调用。
- 启动和结束均核对记录PID/进程启动计数/当前TID及线程启动计数，再只读mask；要求4个APPLIED、唯一commit、old mask完整及actual mask与策略一致。未知任务只记录comm/TID/mask，不按名称猜职责；未知后代继承mask边界明确。
- 稳态窗口每次要求当前PID等于first PID，YOLO/YuNet完成数用同一候选PID的计数作差；恢复后的计数没有混入吞吐。主要计数窗口以稀疏health返回为端点，elapsed含随后检查成本，不能称精确逐帧分布。
- 原单元字节及原config/偏好保护、单相机/DPU锁owner、GUI与Xserver PID核对保留。进入服务切换前已武装独立360秒回退；helper RuntimeMax300秒。业务检查失败走finally恢复，恢复脚本拒绝覆盖无关后续unit。原服务恢复与候选线程RESTORED/CLOSED分别记录；候选缺干净退出事件会令总体passed为false，没有伪装为原服务恢复失败。
- TTL独立汇总；主检测≥9Hz、YuNet≥2Hz、native完成≥100、0新USB/0真超限和完整线程清理各有门槛。不得只看“无超限”推断全部业务时效或根因修复。

## 已告知主任务的改进建议（非本次安全阻塞）

1. 在第一次`affinity_snapshot`前记录`candidate_camera_pid`，让启动核验失败也能读取正确日志；当前异常仍会保存`latest_camera_seen`并恢复原服务。
2. 读取mask后再核对一次process/thread启动计数，可进一步缩小只读核验中的线程退出/复用窗口。当前先核对`/proc/<PID>/task/<TID>`且4个角色设计为长驻线程，风险较小。
3. freshness从`age<1000`补为`0<=age<1000`，与既有单调时间新鲜度约定一致；正常当前数据不会为负。
4. 原SIGKILL或`os._exit`路径不保证RESTORED/CLOSED齐全，必须保留这个失败/未确认事实；确认原进程已终止、原服务及owner恢复是另一项证据，二者不可混淆。

没有执行任何板卡命令，新增DPU调用0；不把本地AST/解码审查计成新的板测。
