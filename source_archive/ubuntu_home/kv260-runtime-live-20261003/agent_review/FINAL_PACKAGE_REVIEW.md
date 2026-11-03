# 新联合运行包的最后审阅

审阅对象为 `reviewed_payload/board_worker.py`、`live_common.py`、
`agent_helpers.py`、`actions/*.py`、`config.json` 与固定 `package_manifest.json`。
本审阅未修改这些包成员，未打开 UART、未执行板端命令。

## 结论

正常受控流程未发现必然阻断执行的错误。主实验异常被 worker 捕获后进入
`finally` 并尝试 `60_restore.py`。恢复阶段仍严格核对身份、哈希、实际应用、
模块引用和 DRM 占用；不 force 卸载、不覆盖原程序或模块文件。

可以开始原定有限板测，但“发生异常必尝试受控恢复”不等于“任意异常一定恢复”。
若候选 daemon 已停止而活动 overlay 仍在，恢复脚本会因实际状态无法通过严格
无应用证明而停止；worker 将明确记录 `state=failed`、`baseline_restored=false`。
该情形需要重新审阅已知应用状态后恢复可信管理器的 IPC，不能放宽检查或强制卸载。

## 状态解释

- 主实验全部完成、恢复完成且没有最终日志或恢复诊断问题：`state=complete`。
- 主实验或诊断失败，但原基线完整恢复：`state=failed`、`baseline_restored=true`。
- 恢复本身失败：`state=failed`、`baseline_restored=false`，查看 `failures` 原始 traceback。
- `completed_phases` 包括正常返回的恢复阶段；该列表自身不能代替整体 `state`。
- 候选日志在 SIGINT 刷新后审阅；发现 `ERROR:` 继续尝试恢复，但将实验记为失败。
- 恢复阶段内核错误/日志连续性丢失原样保存，不阻止剩余受保护的恢复；未知应用、
  占用、改变的身份/哈希和正常命令失败仍立即停止。

## 检查结果

16 项主机离线验证全部通过，证据为
`offline-fixtures-20261003T084507649628Z/fixture-review.json`。

1. 旧官方、重载后官方、M3、恢复官方 4 份完整 Top-5：强制把旧原始文本作为 stderr，
   当前 helper 均解析成功。
2. 上述 4 份 DPU query：stdout 保持 JSON、stderr 加入非 JSON 文本，均正确解析并核对。
3. 内核环形日志保留末尾重叠时连续性成立；新增引用错误和没有重叠时均停止主实验。
4. 相同 wd 出现在不同 FD 时分开计数，同一 FD 内去重；同一 PID 换 starttime 被拒绝。
5. 13 个固定包成员哈希与归档哈希匹配；包内 Python 语法全部通过。

主机 fixture 使用模拟 subprocess 和 proc/sys 文件，不构成新的板测。
旧分类输出和 query 原文及哈希在 fixture 结果中逐份记录。

## 执行与证据边界

当前包 `10_start.py` 的实际顺序是原应用正常 remove、rmmod/insmod、再 stop 原服务，
然后创建本次临时 drop-in 并启动候选；与早先讨论的 stop 原服务在先顺序不同。
在该实际顺序中，模块暂时缺失时原管理器仍能提供活动应用查询；恢复脚本也覆盖
模块缺失与服务停止状态。

30 轮重载和至少 1800 秒推理阶段保存各命令 stdout/stderr、元数据、完整内核日志及
内存/watch 样本到新的板端 `WORK/agent_logs`。后台 worker 的 status/progress 用于
实时观察；阶段摘要不能代替这些完整文件，执行后必须回收核对。

watch 样本绑定本次 manager PID/starttime，无法读取或进程更替不按零计数。
内核检查依赖原日志末尾重叠；覆盖全部重叠会标明无法确认，不将空的新错误集合当通过。
未改变的 daemon stdio 缓冲可能延后 ERROR 观察，以最终 SIGINT 刷新后的完整日志补充核验。
有限观察不证明所有内存泄漏或并发热卸载情形均不存在，也不是新的 FPS 成绩。
