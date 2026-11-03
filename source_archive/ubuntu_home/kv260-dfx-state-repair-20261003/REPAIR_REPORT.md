# DFX manager 共享状态与父设计清理修复

## 结果

两处已确认缺陷已在独立源码副本中修复，KV260 AArch64 daemon/client 编译通过，原系统镜像的静态 ABI 核对通过。当前交付为可审阅候选；本机运行时回归、加载器执行检查和板级验收尚未执行，板端尚未替换。

工作目录：`/home/ghmd/kv260-dfx-state-repair-20261003/`。本地日期为 2026-10-03，证据目录采用 UTC，日期显示 2026-10-04。

## 源码改动

实际改动两个源码文件，源自此前 watch 去重修复版本：

- [daemon_helper.c](/home/ghmd/kv260-dfx-state-repair-20261003/sources/dfx-mgr-patched/src/daemon_helper.c:31)：一个 `state_lock` 覆盖监听表、设计元数据、活动设计和槽位生命周期。公共读取、列表、加载/卸载与目录事件使用同一把锁；内部函数要求调用者持锁。阻塞的 inotify `read()` 在锁外执行。UIO 路径在解锁前复制到线程私有缓冲区，避免外部保留内部槽位指针。
- [dfx-mgrd.c](/home/ghmd/kv260-dfx-state-repair-20261003/sources/dfx-mgr-patched/example/sys/linux/dfx-mgrd.c:149)：初始化失败时退出并报告错误，避免带着未初始化的共享数组继续服务。

父目录删除/移出时，按完整路径边界清理所有子目录及孙目录监听，清空全部子包记录。非活动父设计释放并完整重置；活动设计从可加载列表退出，但保留运行中槽位、类型、槽位数量和身份，直至显式卸载成功后回收。硬件卸载未成功时保留运行时记录。

关联边界处理包括：新目录真正登记自己的监听描述符；未知描述符不会中断整批事件；监听溢出时重新扫描并清理已消失路径；子包容量耗尽不返回越界指针；目录不存在时不调用 `readdir(NULL)`；负槽位/槽位上界和 FD 数量检查；活动 `shell.json` 更新不改写已分配槽位数组的边界；列表拼接受缓冲区容量限制。

加载路径由运行中槽位持有，避免 `pkg->path` 留在函数栈上；包路径长度受到原运行时 `tmp_dir[128]` 容量限制，过长路径会拒绝加载。XRT 固件环境配置直接写入 `/etc/vart.conf`，移除了原函数的路径分配差一字节和固定 shell 命令缓冲区问题。

## 实际验证

### 编译和静态兼容检查

- 使用现有 Vitis 2022.2 AArch64 GCC 11.2 与匹配 sysroot；无需下载依赖。
- 最终构建：[status.json](/home/ghmd/kv260-dfx-state-repair-20261003/evidence/20261004T063058.990912Z-patched/status.json)。daemon/client 均成功；保留项目原有 `-Wall -Wextra -Werror`，使用 `-O2`、stack protector、FORTIFY、branch protection 和 RELRO/NOW。
- 最终静态 ABI 记录：[status.json](/home/ghmd/kv260-dfx-state-repair-20261003/evidence/20261004T063258.673559Z-runtime-review/status.json)。AArch64 与解释器路径正确；候选去除了构建 RPATH；`libdfx.so.1.0`、`libpthread.so.0`、`libc.so.6` 和 `ld-linux-aarch64.so.1` 的依赖与版本化强符号均由原镜像提供，未解析强符号为 0。
- 客户端 `.text` 与上一候选一致，整份 ELF 哈希受构建标识/路径影响而不同；后续部署选择 daemon，沿用板上现有客户端。
- `git diff --no-index --check sources/dfx-mgr sources/dfx-mgr-patched` 返回 0。
- 首次构建因新代码缩进触发 `-Werror=misleading-indentation` 失败，已修正。该失败日志及中间成功构建保留在 `evidence/`，最终候选来自上面标明的最终构建。

### 候选身份与复现

最终 daemon：117856 字节，SHA-256：

`369c7fb0ddd023a7cf7af14896a7fda6036219a36f4980c73640889720c95dfd`

候选包输出为 `release/dfx-state-20261003-candidate.tar.gz`。包中含 daemon/client、完整候选源码、相对上一 watch 修复版本的增量补丁、相对固定 vendor 源码的完整补丁、源码清单及构建/ABI 记录。补丁回放、原副本保持一致和归档逐成员回读的结果统一记录到本目录 `PACKAGE_VERIFICATION.json`；该文件放在归档之外，避免循环哈希。

源码基线的固定 vendor commit 为 `bc06691eb35d7f0acb7c2508b6d050d77b0264a0`。`sources/dfx-mgr` 为保存的上一 watch 修复版本，`sources/dfx-mgr-patched` 为本候选。此前工程、已验证二进制和历史报告均保留在原目录。

同一主机重新构建：

```sh
cd /home/ghmd/kv260-dfx-state-repair-20261003
python3 scripts/build_manager.py patched
python3 scripts/review_runtime.py
```

每次构建和 ABI 检查使用独立目录；`CURRENT_BUILD_PATCHED.json` 指向最新成功构建。生成时间/绝对构建路径可能影响 ELF 构建标识，不能用全文件哈希一致代替源码和实际构建输入的核对。现有候选包已封存，后续修订应使用新版本包名。

## 验证边界与下一步

本轮未执行本机回归、ASan/TSan 或 QEMU 加载器检查，静态符号核对不证明并发行为正确，也不代替真实硬件加载/卸载。当前没有 `/dev/ttyUSB*`、`/dev/ttyACM*` 或 `/dev/serial/by-id` 设备，未取得本轮板端证据。

共用状态锁会让目录事件及查询在加载/卸载期间排队；实际持续负载延迟需要测量。目录已移除的活动设计必须先正常卸载，才能重新接受同路径新包。

下一步先按 [板端验证计划](/home/ghmd/kv260-dfx-state-repair-20261003/BOARD_VALIDATION_PLAN.md) 补本机回归和原镜像加载器检查，再接入 KV260 临时切换、对照官方推理及热更新验收。历史最新板测仍是 [文件系统修复后冷启动记录](/home/ghmd/kv260-fs-repair-reboot-20261003/POST_REPAIR_BOOT_REPORT.md)，当时运行 manager 的 SHA-256 为 `db9c25f09f1178177884b1114c57f32c076f1e7f9cdd0d12b7a896039038a46c`；不能把那个版本的已通过板测记到本候选上。

本次源码修复不意味着相机、音频、三人接口合同或完整运动硬件已经交付。这些事项继续按项目书和架构审查记录推进。
