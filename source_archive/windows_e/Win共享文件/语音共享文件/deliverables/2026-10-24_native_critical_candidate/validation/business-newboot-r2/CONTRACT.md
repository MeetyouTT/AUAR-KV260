# r2 新 kernel boot 启用合同

这是独立候选，父级冻结 r1 完全不修改；只本机实现/测试，不连接板卡、不重启、不部署。

- `native_execution.allow_new_kernel_boot` 是显式布尔 opt-in，缺省 `false`；为 true 时还需 `new_boot_marker_directory`，绝对非重定向、当前有效 UID 所有、mode0700。目录和归档文件持久化均 fsync。
- preflight 读取实际 `/proc/sys/kernel/random/boot_id`，传入 boot 与真实值不符直接拒绝。source boot 同真实 boot 时严格走 r1 同 boot exact 逻辑，不能用 opt-in 清故障。
- source boot 真正不同，且 opt-in 为 true，才读取 hash 固定、完整、已 seal 的 v2 final checkpoint。legacy health/prefix/maintenance/unsealed/fenced/非法来源/错误字段拒绝；旧单调时间只在旧捕获域自洽校验，不拿旧较大 uptime 当作当前未来，也不将其重放入新预算。
- 为当前真实 boot 生成 `validated_new_kernel_boot`、kind0、全零新 counter/policy 域；新 captured 必须来自当前 `monotonic_ns`，大于当前或不合法都拒绝。所有旧故障/恢复/SFace累计与 source SHA/boot/来源信息归档，界面健康明确为历史域，不能说故障消失。
- attach 前先持久保存完整旧 checkpoint/archive，再创建**仅按当前 boot 命名、无 seedhash**的一次 marker（O_EXCL、文件 fsync、目录 fsync），然后才创建 Context/恢复/adopt。已消费、半写、其它 seed 或启动失败后重试均 fail closed；不移除 marker 重开预算。
- 不同 boot 下旧 PID 可复用，不用 PID 相同误判旧 owner 活着。同 boot 仍必须按 r1 拒绝活前任和重复消费。
- 原旧进程没有精确 seal/export 的首次 legacy→native 迁移仍未解决；不能把当前同 boot 的 5/3 fault、healthprefix 或人为假 boot 当 cold start。
