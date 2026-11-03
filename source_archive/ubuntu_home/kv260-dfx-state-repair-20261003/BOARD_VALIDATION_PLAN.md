# 新 DFX manager 候选的板端验证和回滚

本文件是后续执行步骤。本轮没有连接 KV260、替换服务或运行以下测试。

## 进入板端验证前

1. 运行针对新内部加锁约定编写的本机回归：列表扫描与目录事件并发、多子包和孙目录删除、移动进出、监听容量、父槽位复用、活动设计删除后正常卸载、卸载失败保留状态。旧 `watch_regression.c` 的内部函数直接调用方式需要调整，不能将旧候选通过的测试记到本候选上。
2. 本机通过后，用 `python3 scripts/review_runtime.py --loader-check` 补做原镜像加载器检查；该参数本轮未执行。实际 KV260 加载与推理仍需独立验证。
3. 接回 USB UART，重新读取板卡身份、boot ID、服务实际 ExecStart/DropInPaths、活动应用、ZOCL srcversion、占用、配置和输入哈希。最新历史记录来自 `kv260-fs-repair-reboot-20261003/POST_REPAIR_BOOT_REPORT.md`，不代表重新连接时必然相同。

## 具体候选和恢复目标

- 候选归档：本目录 `release/dfx-state-20261003-candidate.tar.gz`；以 `PACKAGE_VERIFICATION.json` 和包内 `SHA256SUMS` 校验字节。
- 在板上单独 staging，并将 daemon 放在 `/usr/local/lib/kv260-dfx-state-repair-20261003/dfx-mgrd`。本次候选范围是 manager；使用当前板上的客户端和当前已验证 ZOCL。
- 历史已验证 manager：`/usr/local/lib/kv260-runtime-repair/dfx-mgrd`，SHA-256 `db9c25f09f1178177884b1114c57f32c076f1e7f9cdd0d12b7a896039038a46c`。
- 保存实际 `/etc/systemd/system/dfx-mgr.service.d/10-kv260-repaired.conf`、vendor unit、daemon.conf、VART 配置、活动固件和当前 manager 的原件与哈希。回滚目标是接入时已验证运行的 manager，不应照抄旧方案恢复到有缺陷的原厂 ZOCL。

## 临时切换和验收

1. 保存现场，在当前 manager 仍正常时，用 `xmutil unloadapp` 正常卸载活动应用；确认状态后停止 `dfx-mgr.service`。两个 manager 不能同时使用 `/tmp/dfx-mgrd.socket` 或操作同一 PL。
2. 只在 `/run/systemd/system/dfx-mgr.service.d/` 新建本轮专用 override，审阅合并后的 unit，保留现有 ZOCL 服务依赖，临时将 `ExecStart` 指向新候选。`daemon-reload` 后检查实际解析结果，再启动服务。全量保存候选诊断和内核日志。
3. 验证默认官方 benchmark、`xdputil query` 和原 ResNet18/原图片分类，逐项对照历史已通过结果。
4. 列表查询与一个专用、未加载的测试包目录的创建/移动/删除并发运行。测试包至少包含三个子包及孙目录；记录每阶段内部可见包列表、内核 inotify 监听项、退出码和完整日志。确认父目录删除后全部子监听回收，复用槽位无残留，其他官方包不变。
5. 只用明确的测试包评估活动目录消失策略：元数据从可加载列表退出，运行中槽位保留，显式卸载成功后才回收；卸载失败时状态保留且不能假报成功。不得直接删除官方固件来制造用例。
6. 完成官方应用正常加载/卸载循环及同图推理。确认没有新增崩溃、死锁、监视增长和异常内核日志。合格后再决定持久化配置与冷启动验收。

## 回滚

候选异常时先保存现场。manager 可用则正常卸载应用；停止候选服务。仅清理本轮创建、已核对内容的 `/run` override，执行 `daemon-reload`，确认 ExecStart 恢复接入时保存的已验证 manager，随后重新启动默认官方应用并复跑 query/原图推理。若候选已退出而硬件仍加载，先按保存的实际状态恢复已验证 manager，再正常处理硬件，避免猜测状态后连续重跑卸载。

持久化和重启属于后续验收步骤；本候选尚未完成这些步骤。
