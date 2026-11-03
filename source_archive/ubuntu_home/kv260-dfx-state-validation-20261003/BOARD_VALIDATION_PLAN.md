# 通过本机验证后的板端验收步骤

本机 8 项普通回归、8 项 ASan/UBSan（含泄漏检测）和原系统镜像加载器枚举检查已经通过。实际 FPGA 加载/卸载仍未验证；本机相关调用是明确的测试替身。本轮未发现 USB 串口设备，未切换板端服务。

## 接入和 staging

1. 接回 KV260 USB UART 或提供可达板卡 IP。先只读采集板卡身份、boot ID、活动应用、`dfx-mgr.service` 的实际 ExecStart/DropInPaths/Requires/After、ZOCL srcversion/参数/占用、配置、运行时/固件/模型哈希与当前日志。
2. 核对当前状态与历史已验证备用卡记录；实际变化必须先解释。历史恢复目标为 `/usr/local/lib/kv260-runtime-repair/dfx-mgrd`，SHA-256 `db9c25f09f1178177884b1114c57f32c076f1e7f9cdd0d12b7a896039038a46c`。接入时若不同，以重新核验的实际恢复点为准。
3. 传输 `release/dfx-state-20261004-host-verified.tar.gz` 到独立 staging，核对归档和全部成员 SHA-256。候选 daemon 的 SHA-256 为 `369c7fb0ddd023a7cf7af14896a7fda6036219a36f4980c73640889720c95dfd`。
4. 保存当前 unit/drop-in、daemon.conf、VART 配置和运行时文件原件/哈希。只将候选 daemon 放到 `/usr/local/lib/kv260-dfx-state-repair-20261003/dfx-mgrd`，沿用当前客户端和已验证 ZOCL。创建 `/home/root/kv260-dfx-state-validation-20261003/` 保存全过程证据。

## 临时切换

1. 用当前正常 manager 执行 `xmutil unloadapp`，确认活动应用已经正常卸载，再停止 `dfx-mgr.service`。两个 manager 不能同时使用 `/tmp/dfx-mgrd.socket` 或操作同一 PL。
2. 审阅本目录 `board/90-kv260-dfx-state-validation.conf` 与板上实际 unit 合并的结果。只在 `/run/systemd/system/dfx-mgr.service.d/` 创建同名临时 drop-in；保留已验证 ZOCL 的 Requires/After 依赖。
3. `systemctl daemon-reload` 后读取实际解析配置，确认 ExecStart/依赖/日志位置与准备的文件一致，再启动候选。任何未预期错误先保存现场，按实际硬件/服务状态恢复，避免盲目重跑卸载。

## 板端验收

- 默认官方 benchmark 正常加载，`xdputil query` 与原 ResNet18/原图片分类逐项对照已验证结果。
- 列包查询与一个未加载、明确命名的测试包的创建/移动/删除并发执行。测试包至少包含三个子包和孙目录。逐阶段记录包列表、内核监听项、daemon 完整日志、内核日志及退出码；父目录删除后全部回收，复用槽位无残留。
- 通过专用测试包检查活动目录消失策略：从可加载列表退出、运行槽位保留、显式卸载成功后回收，失败时不谎报已卸载。官方固件不得用作删除用例。
- 正常加载/卸载循环后复跑同图推理，核对原输入/固件/运行库哈希，评估持续查询延迟、崩溃、死锁、监听增长和新增内核错误。

## 回滚和完成条件

manager 可用时先正常卸载应用并停止候选。仅移除本轮创建、内容已核对的 `/run` drop-in，`daemon-reload` 后确认恢复接入时保存的已验证 manager，重新启动官方应用并复跑 query/原图推理。若候选退出而硬件仍加载，先保存现场并按实际状态恢复已验证 manager，再正常处理硬件。

临时板测合格后再完成持久化与冷启动验收，才可记录为板端修复完成。没有本轮板端日志、身份和推理结果前，不能将本机通过记为板级通过。
