# 已验证案例与适用限制

原始证据在本提交附件的 evidence/；运行时与硬件基线固定值在 config/source_lock.json、config/baseline_inputs.json。以下均为此前有限验证，不能称本技能已完成新的板测。

## 重复 watch 登记

dfx-mgr commit bc06691eb35d7f0acb7c2508b6d050d77b0264a0：
listAccelerators → firmware_dir_walk → acell_dir_add → add_to_watch。
内核重复 inotify_add_watch 可返回已有 wd，原内部表却重复占用空项；base 去重发生过晚。

主机真实 helper 测试：

| 实验 | 原版 | 修复版 |
|---|---|---|
| 重复扫描 | 130 次后内部 500、内核 5 | 10,000 次后内部 5、内核 5 |
| 生命周期 | 未按本项声称原版通过 | 1,000 轮，最终 5 |
| 8 线程登记 | 未按本项声称原版通过 | 80,000 次调用，最终 1 |

修复保持容量 500；按 wd/path 去重、表洞复用、参数检查、登记/删除互斥和删除清空。没有证明所有 daemon 共享状态线程安全，现有 SDK 缺 libasan，未执行 sanitizer。

板测：1,000 次专用 list 循环、50 轮真实目录增删、3 轮官方重载、一次 M3 装载及四阶段同图推理通过；不是 30 分钟持续试验。原 manager 和原 ZOCL 已恢复。

## 就绪误判及修正

原 06-start-candidate 返回 1，完整失败日志已保留。服务实际已运行；测试脚本误用 SOCK_STREAM，而上游 example/sys/linux/dfx-mgrd.c 和 src/dfxmgr_client.c 使用 SOCK_SEQPACKET。

先读服务状态、PID、socket 与源码。独立 20-ready-check 使用正确协议通过，候选二进制没有为此改动，也没有重放启动过程。新增 socket_probe.py 复用这个判断，仅连接一次，不发送协议载荷；它证明 IPC 可达，功能仍由原客户端和模型对照确认。

## ZOCL 引用释放

固定 XRT commit 43926231f7183688add2dccfd391b36a1f000bea。
成功 bus_find_device 持有引用；zocl_get_zdev 返回借用 drvdata，需释放临时查询引用。cu.c 的查询成功路径、错误和提前返回均需平衡。

已有修复只改三文件，SPDX 保持 GPL-2.0 OR Apache-2.0。有限切换中修复驱动没有新增目标 /axi/zyxclmm_drm 引用错误；原驱动第一次卸载出现一次已知错误，112 条去重 overlay 属性警告仍保留。不能据此推断所有内存泄漏或并发热卸载问题已解决。
