# 2026-10-03：重新连接 KV260 与运行时扩大复验

用户指出板卡已连接。沙箱中的 /dev 不可见，升级到沙箱外只读主机枚举后发现同一 Xilinx USB 与 ttyUSB1；UART root shell 读取成功。原“没有串口设备”不能代表主机未连接。

实时身份核对为备用卡、mmcblk1p2、PetaLinux 2022.2、kernel 5.15.36-xilinx-v2022.2；boot ID 仍为 64083069-98b7-409b-a455-b7b3b7158745。原 manager/driver/official slot 0 与 26 项哈希一致。

初始宽泛 DRM 检查因 Xorg 使用 card0 停止。sysfs 证据明确 card0 属于 zynqmp-display，DPU 的 card1/renderD128 属于 ZOCL 且无客户端、refcnt 0；按实际相关驱动重新检查通过，没有停止桌面、修改厂商规则或绕过占用。

第一独立目录 /home/ghmd/kv260-runtime-live-20261003：26 项原文件在板端新 baseline 逐份复制并核对，传输13成员包54帧/162841B通过。只使用此前板测的 manager db9c25... 和 zocl 5cef5e...。

首次扩大复验在原应用 remove 后、修复模块加载前停止，原因是自编测试脚本要求全部旧 dmesg 为新日志前缀。完整日志确认前4行被正常环形缓冲滚出，旧末16行唯一连续重叠，新增4行完整，含原ZOCL一次known引用错误。修复模块未加载、candidate log不存在；worker finally恢复通过，原服务无drop-in、原driver、官方slot0、VART/26hash、DPUquery和同图完整Top5一致，boot不变。

28成员完整失败/恢复证据已回收校验，71597B，SHA b89ad1baf4d30309c725f6e93a76a36bd33e59609acc8591b1cb575cd905db85。所有失败原始来源、清单、输出和归档保留。

新独立目录 /home/ghmd/kv260-runtime-live-20261003-retry1：仅修正测试脚本的核日志重叠判定，旧日志尾16行须唯一连续匹配，无匹配/歧义/新错误仍拒绝。真实原始日志fixture及10项边界验证通过。厂商代码、此前板测二进制、板卡原基线不改。

重试完整预检、备份和新包准备正在执行。30轮及至少30分钟复验尚未得到结果；本记录之后会补充实际结论。未永久启用、重启、SD/QSPI烧录或执行PWM/执行器。

## 最终补记：扩大复验通过，原基线已恢复

上述为启动前记录。新独立重试完整预检、26项备份、54帧/163404B传输及13个包成员校验通过。只改自编测试器的日志重叠判定，厂商代码/规则/二进制保持原固定版本。

新boardworker全部6阶段完成，正常退出。30轮官方remove/load及同图功能成功；连续观察1802.124417944秒，872次同图推理和60份长测采样通过；M3 DPU查询和同图复核通过。合计35份DPU query、905份分类，完整Top5逐项一致。M3本轮没有重复寄存器/MMIO/PWM/FPS测试。

长测同一candidate PID/starttime，watches5、managerRSS9524kB恒定，zoclrefcnt0。MemAvailable3634836→3594152kB、Slab75136→79812kB、SUnreclaim37768→37324kB、SReclaimable37368→42488kB；日志/缓存可能贡献，未做独立归因，不能称完全无内存泄漏。有限循环不是FPS基准。

内核165份增量审阅，修复阶段新增不允许错误0；原驱动卸载knownreferror1条；544条不同时间戳的overlay属性警告原样保留。SIGINT刷新完整candidate log 2708388B，SHA135a3f4b58f729fd8065300640f6f3a48d789be56fcd32e1d8c2afd01f2cd7ae，ERROR0。

恢复原manager40318、原driver0991D1B457855C8987936E6、官方slot0、原VART/26hash，drop-in移除，boot不变。同图恢复功能通过；另一次freshfinalguard再次核对原服务active、workerResultsuccess/ExecMainStatus0、无ZOCL占用。修复未永久启用，原版缺陷尚留在恢复的原二进制。

完整板端证据3480成员回收至board_evidence.tar.xz，522748B，SHA3384ec011a254ddb2b6baaf489d23ade09844c385e5363af495625f6ccb3b3b0，逐成员hash校验通过。独立分析overall_pass=true/baseline_restored=true/issues0，92份全流程采样另存CSV；之前源码附件1052封存记录仍全部匹配。

报告：[LIVE_REVIEW_REPORT.md](/home/ghmd/kv260-runtime-live-20261003-retry1/LIVE_REVIEW_REPORT.md)。原失败目录及证据完整保留。没有永久启用、板卡重启、SD/QSPI烧录、执行器/PWM、自研新硬件构建；旧DRC/约束/时序限制与fstab重复项没有被这轮有限运行时验收覆盖。

最终另一个只读审阅独立执行21项核对通过：3480文件及tar.xz内成员逐份size/SHA一致，重新解析35query/905Top5，确认60长测样本、完整管理器日志、内核增量分类及恢复。输出final_review/FINAL_CROSSCHECK.json/md。补充测后完整meminfo与16886958B测试日志体积已记录；该点属于恢复后状态，不等同修复版长测，也不用于宣称内存变化已完全归因。两次独立目录生成EVIDENCE.sha256并回读验证，保留所有成功/失败资料。

## 持久启用方案准备（主机侧）

新建独立目录 `/home/ghmd/kv260-runtime-persistent-plan-20261003`，复制此前板测通过的 manager/ZOCL、补丁及来源、基线和依赖元数据；候选二进制 size/SHA 与板测输入相符。加入只读板端启动顺序采集脚本、待审阅 systemd 草案、安装门槛和哈希限定的回滚步骤。脚本 Python 语法检查通过，目录 14 项摘要回读一致。

关键未决项：在线测试使用临时 override，不证明冷启动顺序。必须先用 UART 新鲜检查 initramfs 实际模块内容、modules-load/udev/systemd 启动先后；当前 loader 遇见已加载的非目标 zocl 会失败关闭，故草案不可直接安装。本机 `systemd-analyze verify` 在沙箱中因 varlink/systemd socket 权限失败且模板扩展名为 `.in`，未算通过；须在目标系统以正式 unit 名复核。本轮没有运行板端探针、写启动配置、切换板端运行时或重启。

## UART 启动顺序只读预检

按用户要求继续自主检查，通过 `/dev/ttyUSB1` 115200 UART 登录 root。备用卡 CID `0353445345333247805558c00401a100`，root `/dev/mmcblk1p2`，boot ID `64083069-98b7-409b-a455-b7b3b7158745`，PetaLinux 2022.2 / kernel `5.15.36-xilinx-v2022.2`。原 `dfx-mgr.service` active/enabled、无 drop-in；官方 benchmark slot0；原 manager SHA、原 zocl srcversion/file SHA 与历史值相同，参数1、refcnt0、DRM节点无打开进程。26项原文件 SHA-256 经两组 `sha256sum` 逐项比对，26/26 一致。

只读检查真实 U-Boot initramfs（流式解包、没有落盘）：归档无 `lib/modules`、zocl 或 modules-load 条目。两个 boot DTB 无 zocl/embedded_sched 字符串。modules-load、modprobe、udev、systemd 配置搜索无 zocl/xocl 命中；内核模块 alias 有 `of:N*T*Cxlnx,zocl*`。已读完整 `xlnx-firmware-detect`，此脚本只验证默认固件标记与目录，不加载 app 或模块。systemd 249.7+ 中 modules-load/udev-trigger 位于 sysinit 前，拟议 oneshot loader 增加 After 两者，并由 dfx-mgr Requires/After 保证 manager 之前加载修复模块。结论是方案有足够运行态证据进入静态审阅/安装前恢复点准备；冷启动仍未验证。

目标板无 `systemd-analyze`；Ubuntu 工具是 systemd 245，离线 `--root` 不支持 verify；沙箱下 verify 还遇 varlink/socket 权限与 host ExecStart 路径错误。因此 unit 语法/依赖检查没有计为通过。整个 UART 轮次只读，没有板端写入、app切换、卸载或重启。详细证据在 `/home/ghmd/kv260-runtime-persistent-plan-20261003/logs/BOARD_READONLY_PREFLIGHT_2026-10-03.md`。

## 修复版持久启用和冷启动验收

目标板 systemd 249 通过 `/run/systemd/system` 临时加载候选 loader 和 manager drop-in；`systemctl show` 确认 `LoadState=loaded`、manager 的 Requires/After 指向 loader。未启动临时 unit；检查后删除临时文件并 daemon-reload，确认原 manager active、无 drop-in，原 srcversion 和 boot ID 不变。

候选包经 UART ASCII-base64 临时传输（本机无 `sz`，未安装包），包 SHA `ce9dc5f7f24b61c3fdb6fbfa0566b0d893b72a1e8f92a76dce82c4bdc30f6c95`，6/6成员 SHA/size通过。备用卡原 26 项文件哈希再次全部通过。新恢复点保存于板端 `/home/root/kv260-runtime-persistent-backup-20261003/`：原 manager/client/libdfx、原 module、vendor unit、配置、12MB 原 baseline 归档副本及哈希/状态/dmesg；10/10原件摘要通过。

有一次 staging 拷贝误用相对路径，因当时 shell 位于 backup cwd 而失败；set -e 退出 shell，自动登录重启。检查确认只留下两个空目录，原文件、服务、模块、app、boot ID未变。改用绝对路径后安装成功。修复二进制安装于 `/usr/local/lib/kv260-runtime-repair/`；新增 loader unit 与 dfx-mgr drop-in。安装前原服务进程没有被重启。服务管理器读取的 ExecStart 已指向候选 manager，drop-in 已生效。

执行 systemctl reboot。新 boot ID `0251d729-0d3c-44e8-abb9-27121306c081`。systemd journal单调时间：loader 12.990108s启动、13.042471s成功；dfx manager 13.669094s启动、13.934433s成功；默认 firmware 为 kv260-benchmark-b4096；kernel ZOCL probe在15.146000s。driver srcversion `9BDC942A6014BCCBD1DCB78`、参数1、refcnt0；dfx manager PID1012实际路径为候选版；官方benchmark slot0 active。

冷启动后 `xdputil query` rc0：1 CU、B4096、300MHz、0xa0010000、fingerprint 0x101000056010407。原 ResNet18 XMODEL、原图片、原分类程序运行 rc0，Top-5完整一致：Samoyed .949879、white wolf .00931229、Pomeranian .00821807、Great Pyrenees .00498451、Arctic fox .00388194。模型、图片、程序hash与原清单一致。postboot目录13项摘要通过，原26项哈希仍全部一致。

启动仍显示 `proc-fs-nfsd.mount` failed（内核不支持 nfsd filesystem）；FAT `/boot` 有“not properly unmounted”警告。板端无 `fsck.vfat`/`dosfsck`，未修复；fstab两条 /boot项保留。DPU、manager和推理正常。本轮没有写QSPI或替换固件；只对备用卡根文件系统新增候选程序与systemd配置。没有做冷启动后的30分钟重复长测、断电测试、PWM或执行器测试。最终报告：`/home/ghmd/kv260-runtime-persistent-plan-20261003/PERSISTENT_ENABLEMENT_REPORT.md`。
