# AURA 视觉简化发布及 Ubuntu SSH 接入准备

## 板端实测与已提交改动

已先读 ZIP README、当前方案相关视觉章节、共享目录及语音项目 AGENTS、2026-10-30 视觉简化交接。共享目录为 `/home/ghmd/Win共享文件` 的微力同步本地目录。

Ubuntu 无有线网卡，到 192.168.50.2 的 SSH 经校园 Wi-Fi 超时；随后按任务许可使用已识别 Micro USB 串口只读核验。板端 eth0 有载波、192.168.50.2/24，原相机和服务保持正常。因此本机 SSH 不通不能解释此前 Windows 两次发布失败。

实际发现两次候选的根目录 `stage.log` 仍为指向 r11 `managed-runs` 的绝对符号链接。只排除 managed-runs/pycache 无法排除该链接。新复制工具排除根目录 stage.log、launch.json、managed-runs 等运行状态文件，保留现役启动器的原字节与路径检查。隔离测试证明旧错误可复现，新根首次/再次生成日志通过，跨根、坏链接及普通非托管日志仍被拒绝。

板端已 COMMITTED 至：

`/home/root/aura-board-vision-20261030/06391079cfddb734-r3-ubuntu/runtime`

实际和下次配置均为同级 `startup/config.json`。286 项绑定通过，仅 `board/runtime/device_observer.py` 改为兼容停用实现，无法被旧 tick 启用，无线程/采集/上传，发送数 0。原启动优化、全部旧 drop-in、相机 PID/启动时间/epoch、相邻配置、机械配置与 boot/FDT/firmware/VART 保持。一个身份库文件仅在板端进程内比较一致，未导出其哈希、身份或模板。机械 FAULT/null，监听/麦克风/跟随关闭。

本机 14 项检查通过，其中 9 项同时在 ARM 上通过；两端重叠，不累加为 23。独立 300 秒回退 timer 在提交后已停止，最终无发布事务。此前预发布脚本误把二进制音频端口当 HTTP 检查，已在切换前主动退出并修正；该失败记录保留，不是新的板端启动失败。

最终板端核验通过，Windows r12 READY、8810 不通、两条旧图片接口 410。新公开 WAV ARM 语音复核两次遇 `GpuBusy: ... insufficient_headroom`，第二次完整保留板端通过/语音受阻的分项状态，未称语音通过。没有卸载其他模型、放宽准入或恢复私有库。Windows 原 160 回归与此前公开录音证据仍属原交接时点，不能替代此次受阻的复核。

证据：`Win共享文件/语音共享文件/deliverables/2026-10-30_visual_simplification/ubuntu/evidence/`，其中 20261030T103804279843Z-deploy_visual 为提交，20261030T110222516088Z-verify_live 为最终核验。视觉流程和新事件契约已在同级 `视觉流程与事件契约.md` 整理；事件合并/落库/查询仍是设计，ASR 与对话权威库未迁板端。D 盘视觉权重仍由 Windows 清理，Ubuntu 没有访问或删除。

## 用户转向后的 SSH 接入准备

用户随后明确先做 Windows Codex 原生 SSH 接入，本轮不再覆写或重启板卡，共享目录仅交换接入资料。上述正在进行的只读复核完成后，没有再发板端命令。原视觉目录顶层 Windows 交接快照未伪填为最终通过；后续业务交接应引用上述 Ubuntu 新证据。

Ubuntu 用户 ghmd，Codex `/home/ghmd/.local/bin/codex`、0.166.0、ChatGPT 登录有效。Windows 公钥指纹 `SHA256:2e0xLhkeWwz48xIv0QqIfeTNeXoEX6sgjt2yo5ftvlc` 已去重加入用户 authorized_keys，0700/0600。没有输出或复制 auth.json、登录令牌及私钥。

原未安装 SSH Server。sudo 需密码，经 Ubuntu 系统授权安装 openssh-server/openssh-sftp-server 1:8.2p1-4ubuntu0.13，0 升级/0 卸载；服务 active/running/enabled，22 监听。root 密码登录禁止。UFW 不活动、INPUT ACCEPT，未改防火墙或路由。主机 ED25519 指纹 `SHA256:tNZ7GjGBvS/wQDcvA2omrWvQAKLYIaR4/a2WaBf/Mrs`，只读取主机公钥指纹。

修改 `/home/ghmd/.bashrc` 增加用户本地 bin PATH，保留原代理包装函数。本机真实 SSH 认证后的普通命令 shell、登录 shell、Codex 版本/登录状态及项目目录均通过。临时回环测试密钥只存本机且已经移除，Windows 公钥保留。没有启动 app-server 或开放其局域网端口。

Windows 用户提供 WLAN 10.148.20.87/17、网关 10.148.0.1，到 Ubuntu 172.23.242.132 路由走 singbox_tun。Ubuntu 返回走 172.23.0.1/wlp0s20f3；两次 ping 无回应，不能判 TCP 不通。45 秒 SSH TCP 头部观察 0 包，但尚未确认覆盖 Windows 复测，不推定拦截点。

已原子写入 `Win共享文件/协作任务/2026-10-30_Codex跨机协作/ubuntu-registration.json`，host 为 Ubuntu 172.23.242.132，port22/userghmd，实际项目为语音共享目录；ready=false，列明跨机 TCP 和 TUN 路由待复测。Ubuntu准备回执、网络审计、本机真实 SSH 验证均已写入同目录；未代填 Windows 成功记录。

下一步 Windows 在服务启动后复测 TCP/22 和主机指纹，查证实际源地址/接口/下一跳，再完成原生应用连接；现有聊天是否可接续待实测。后续 Ubuntu 负责板端编译部署，Windows 负责 27B、OmniVoice、接口联调；业务处理和记忆存储最终在板端是后续目标，当前未迁移。
